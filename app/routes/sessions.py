from flask import Blueprint, request, jsonify
from app.services.session_service import SessionService
from app.exceptions import DatabaseError
from app.services.utils import api_performance_monitor, performance_monitor, create_downsampled_cache, get_cached_csv_path
import os
import pandas as pd
import json
import shutil
import logging
import traceback

sessions_bp = Blueprint('sessions', __name__)

class SessionController:
    def __init__(self, project_service, session_service, model_service):
        self.project_service = project_service
        self.session_service = session_service
        self.model_service = model_service

    def list_sessions(self):
        try:
            project_id = request.args.get('project_id')
            show_split = request.args.get('show_split', '0') == '1'
            try:
                sessions = self.session_service.get_sessions(project_id=project_id, show_split=show_split)
                return jsonify(sessions), 200
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500
        except Exception as e:
            logging.error(f"Error in method: {str(e)}")
            logging.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500
        
    def score_session(self):
        print("Scoring session")
        try:
            data = request.get_json()
            print(f"Received data: {data}")
            session_id = data.get('session_id')

            try:
                session_info = self.session_service.get_session_details(session_id)
                if not session_info:
                    return jsonify({'error': 'Session not found'}), 404
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500

            project_path = session_info['project_path']
            session_name = session_info['session_name']

            scoring_id = self.model_service.score_session_async(project_path, session_name, session_id)
            
            return jsonify({
                'success': True,
                'message': f'Scoring session {session_name}',
                'scoring_id': scoring_id,
            }), 200
        except Exception as e:
            print(f"Error starting session scoring: {e}")
            return jsonify({'error': f'Failed to start scoring: {str(e)}'}), 500
        
    @api_performance_monitor
    def get_session_data(self, session_id):
        try:
            # Parse pagination parameters
            offset = request.args.get('offset', 0, type=int)
            limit = request.args.get('limit', 0, type=int)  # 0 means no limit (backward compatibility)
            
            session_info = self.session_service.get_session_details(session_id)

            if not session_info:
                return jsonify({'error': 'Session not found'}), 404

            project_path = session_info['project_path']
            session_name = session_info['session_name']
            
            csv_path = os.path.join(project_path, session_name, 'accelerometer_data.csv')

            if not os.path.exists(csv_path):
                return jsonify({'error': f'CSV file not found at {csv_path}'}), 404
            
            # Log original file size for performance comparison
            file_size_mb = os.path.getsize(csv_path) / 1024 / 1024
            logging.info(f"PERFORMANCE: Loading CSV file size: {file_size_mb:.2f}MB")
            
            # Use cached downsampled file for better performance
            downsample_ratio = 10
            cache_path = get_cached_csv_path(csv_path, downsample_ratio)
            
            # Create or update cache if needed
            cache_created = create_downsampled_cache(csv_path, cache_path, downsample_ratio)
            
            if cache_created and os.path.exists(cache_path):
                # Use cached downsampled file - much faster!
                working_csv_path = cache_path
                cache_size_mb = os.path.getsize(cache_path) / 1024 / 1024
                logging.info(f"PERFORMANCE: Using cached downsampled file: {cache_size_mb:.2f}MB (was {file_size_mb:.2f}MB)")
                is_using_cache = True
                effective_downsample_ratio = 1  # Already downsampled in cache
            else:
                # Fallback to original file with in-memory downsampling
                working_csv_path = csv_path
                logging.info(f"PERFORMANCE: Cache unavailable, using original file with in-memory downsampling")
                is_using_cache = False
                effective_downsample_ratio = downsample_ratio
            
            # Read CSV with chunking if pagination is requested
            if limit > 0:
                csv_offset = offset * effective_downsample_ratio
                csv_limit = limit * effective_downsample_ratio
                
                logging.info(f"PERFORMANCE: Paginated read - offset:{offset}, limit:{limit} (CSV offset:{csv_offset}, limit:{csv_limit})")
                
                if csv_offset > 0:
                    # Skip rows efficiently 
                    df = pd.read_csv(working_csv_path, skiprows=range(1, csv_offset + 1), nrows=csv_limit)
                else:
                    # Read from beginning
                    df = pd.read_csv(working_csv_path, nrows=csv_limit)
                
                original_rows = len(df)
                
                # Apply downsampling only if not using cache
                if not is_using_cache:
                    df = df.iloc[::effective_downsample_ratio]
                
                downsampled_rows = len(df)
                
                # Estimate total count more accurately
                if is_using_cache:
                    # For cached file, we can get exact count efficiently
                    with open(working_csv_path, 'r') as f:
                        total_downsampled_estimate = sum(1 for _ in f) - 1  # Subtract header
                else:
                    # Estimate from file size
                    total_rows_estimate = int(file_size_mb * 1024 * 1024 / 50)
                    total_downsampled_estimate = total_rows_estimate // downsample_ratio
                
                has_more = (offset + limit) < total_downsampled_estimate
                
                pagination_info = {
                    'offset': offset,
                    'limit': limit,
                    'returned_count': downsampled_rows,
                    'has_more': has_more,
                    'estimated_total': total_downsampled_estimate,
                    'using_cache': is_using_cache
                }
                
            else:
                # Legacy behavior - load entire file
                df = pd.read_csv(working_csv_path)
                original_rows = len(df)
                
                # Apply downsampling only if not using cache
                if not is_using_cache:
                    df = df.iloc[::effective_downsample_ratio]
                
                downsampled_rows = len(df)
                
                pagination_info = {
                    'offset': 0,
                    'limit': 0,
                    'returned_count': downsampled_rows,
                    'has_more': False,
                    'total_count': downsampled_rows,
                    'using_cache': is_using_cache
                }
            
            percentage = (downsampled_rows/original_rows*100) if original_rows > 0 else 0
            logging.info(f"PERFORMANCE: Processed {original_rows} -> {downsampled_rows} rows ({percentage:.1f}%), cache: {is_using_cache}")

            bouts = session_info['bouts']
            expected_columns = ['ns_since_reboot', 'accel_x', 'accel_y', 'accel_z']

            # If the CSV has 'x', 'y', 'z' columns, rename them to 'accel_x', 'accel_y', 'accel_z'
            if 'x' in df.columns:
                df = df.rename(columns={'x': 'accel_x', 'y': 'accel_y', 'z': 'accel_z'})

            if not all(col in df.columns for col in expected_columns):
                return jsonify({'error': f'Invalid CSV format. Expected columns: {expected_columns}, Found: {list(df.columns)}'}), 400

            data_records = df[expected_columns].to_dict(orient='records')
            response_data = {
                'bouts': bouts,
                'data': data_records,
                'session_info': session_info,
                'pagination': pagination_info
            }
            
            return jsonify(response_data)
        except Exception as e:
            print(f"Error retrieving session data: {e}")
            return jsonify({'error': f'Server error: {str(e)}'}), 500

    def get_session_metadata(self, session_name):
        try:
            try:
                metadata = self.session_service.get_session_data_by_session_name(session_name)
                if not metadata:
                    return jsonify({'error': 'Session not found'}), 404
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500
            if not metadata:
                return jsonify({'error': 'Session not found'}), 404
            return jsonify(metadata)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    def update_session_metadata(self, session_id):
        try:
            data = request.get_json()
            status = data.get('status')
            keep = data.get('keep')
            bouts = data.get('bouts')
            verified = data.get('verified')
            
            try:
                rows_affected = self.session_service.update_session(session_id, status, keep, bouts, verified)
                
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500
            
            return jsonify({'message': 'Metadata updated', 'rows_affected': rows_affected})
        except Exception as e:
            print(f"Error updating session metadata: {e}")
            return jsonify({'error': str(e)}), 500
        
    def split_session(self, session_id):
        try:
            data = request.get_json()
            split_points = data.get('split_points')  # Array of ns_since_reboot timestamps
            if not split_points or not isinstance(split_points, list) or len(split_points) == 0:
                return jsonify({'error': 'At least one split point required'}), 400

            try:
                session_info = self.session_service.get_session_details(session_id)
                if not session_info:
                    return jsonify({'error': 'Session not found'}), 404
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500
            
            session_name = session_info['session_name']
            project_path = session_info['project_path']
            
            try:
                parent_bouts = json.loads(session_info['bouts'] or '[]')
                # Convert to list if it's not already
                if isinstance(parent_bouts, str):
                    parent_bouts = json.loads(parent_bouts)
            except json.JSONDecodeError:
                parent_bouts = []
            
            # Read original CSV from the project directory
            csv_path = os.path.join(project_path, session_name, 'accelerometer_data.csv')
            if not os.path.exists(csv_path):
                return jsonify({'error': f'CSV file not found at {csv_path}'}), 404
            
            df = pd.read_csv(csv_path)
            expected_columns = ['ns_since_reboot', 'accel_x', 'accel_y', 'accel_z']
            if not all(col in df.columns for col in expected_columns):
                return jsonify({'error': f'Invalid CSV format. Expected columns: {expected_columns}, Found: {list(df.columns)}'}), 400

            # Find split indices
            split_points = sorted(set(float(p) for p in split_points))  # Ensure unique and sorted
            split_indices = []
            split_timestamps = []  # Store the actual timestamps at split points
            for point in split_points:
                df['time_diff'] = abs(df['ns_since_reboot'] - point)
                split_index = df['time_diff'].idxmin()
                if split_index == 0 or split_index == len(df) - 1:
                    continue  # Skip points at start or end
                split_indices.append(split_index)
                split_timestamps.append(df.loc[split_index, 'ns_since_reboot'])
            split_indices = sorted(set(split_indices))  # Ensure unique and sorted
            split_timestamps = sorted(set(split_timestamps))  # Ensure unique and sorted

            if not split_indices:
                return jsonify({'error': 'No valid split points provided'}), 400

            # Split data into segments
            segments = []
            start_idx = 0
            for idx in split_indices:
                segment = df.iloc[start_idx:idx + 1][expected_columns]
                if not segment.empty:
                    segments.append(segment)
                start_idx = idx + 1
            # Add final segment
            final_segment = df.iloc[start_idx:][expected_columns]
            if not final_segment.empty:
                segments.append(final_segment)

            if len(segments) < 2:
                return jsonify({'error': 'Split would not create multiple valid recordings'}), 400

            # Define time ranges for each segment
            segment_ranges = []
            for i, segment in enumerate(segments):
                start_time = segment['ns_since_reboot'].min()
                end_time = segment['ns_since_reboot'].max()
                segment_ranges.append((start_time, end_time))
            
            # Assign bouts to segments based on time ranges
            segment_bouts = [[] for _ in segments]
            
            for bout in parent_bouts:
                """
                Each bout is represented as a dictionary with 'start', 'end', and 'label' keys.

                Example:
                bout = {
                    'start': 1234567890.0,
                    'end': 1234567895.0,
                    'label': 'smoking'
                }

                bout['start'] and bout['end'] are in ns_since_reboot format.
                bout['label'] is a string representing the label of the bout.
                """
                bout_start = bout['start']
                bout_end = bout['end']
                bout_label = bout['label']

                for i, (segment_start, segment_end) in enumerate(segment_ranges):
                    # If bout is entirely within segment
                    if segment_start <= bout_start <= segment_end and segment_start <= bout_end <= segment_end:
                        segment_bouts[i].append(bout)
                        break
                    # If bout overlaps with segment start
                    elif bout_start < segment_start and segment_start <= bout_end <= segment_end:
                        # Adjust bout to start at segment boundary
                        adjusted_bout = [float(segment_start), float(bout_end)]
                        segment_bouts[i].append(adjusted_bout)
                        break
                    # If bout overlaps with segment end
                    elif segment_start <= bout_start <= segment_end and bout_end > segment_end:
                        # Adjust bout to end at segment boundary
                        adjusted_bout = [float(bout_start), float(segment_end)]
                        segment_bouts[i].append(adjusted_bout)
                        break
                    # If bout spans entire segment
                    elif bout_start < segment_start and bout_end > segment_end:
                        # Create a bout for the entire segment
                        adjusted_bout = [float(segment_start), float(segment_end)]
                        segment_bouts[i].append(adjusted_bout)
                        break

            # Create new session names and directories
            new_sessions = []
            for i, segment in enumerate(segments):
                # Generate unique name instead of using suffix
                new_name = self.session_service.generate_unique_session_name(session_name, project_path, session_info['project_id'])
                new_dir = os.path.join(project_path, new_name)
                
                # Calculate start_ns and stop_ns for this segment
                segment_start_ns = int(segment['ns_since_reboot'].min())
                segment_stop_ns = int(segment['ns_since_reboot'].max())
                
                os.makedirs(new_dir)
                segment.to_csv(os.path.join(new_dir, 'accelerometer_data.csv'), index=False)
                new_sessions.append({
                    'name': new_name,
                    'bouts': segment_bouts[i],
                    'start_ns': segment_start_ns,
                    'stop_ns': segment_stop_ns
                })

            # Copy original log file to new directories
            log_path = os.path.join(project_path, session_name, 'log.csv')
            if os.path.exists(log_path):
                for session_data in new_sessions:
                    shutil.copy(log_path, os.path.join(project_path, session_data['name'], 'log.csv'))
            else:
                print(f"Log file not found at {log_path}. Skipping copy.")
                
            try:
                created_sessions = self.session_service.split_session(session_id, session_info, new_sessions)
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500

            # Delete original session directory
            shutil.rmtree(os.path.join(project_path, session_name))

            return jsonify({
                'message': 'Session split successfully', 
                'new_sessions': [s['name'] for s in new_sessions]
            })
        except Exception as e:
            print(f"Error splitting session: {e}")
            return jsonify({'error': str(e)}), 500

controller = None

def init_controller(project_service, session_service, model_service):
    global controller
    controller = SessionController(project_service, session_service, model_service)

@sessions_bp.route('/api/sessions')
def list_sessions():
    return controller.list_sessions()

@sessions_bp.route('/score_session', methods=['POST'])
def score_session():
    return controller.score_session()

@sessions_bp.route('/api/session/<int:session_id>')
def get_session_data(session_id):
    return controller.get_session_data(session_id)

@sessions_bp.route('/api/session/<int:session_id>/metadata', methods=['PUT'])
def update_session_metadata(session_id):
    return controller.update_session_metadata(session_id)

@sessions_bp.route('/api/session/<session_name>/metadata')
def get_session_metadata(session_name):
    return controller.get_session_metadata(session_name)

@sessions_bp.route('/api/session/<int:session_id>/split', methods=['POST'])
def split_session(session_id):
    return controller.split_session(session_id)