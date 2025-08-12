from flask import Blueprint, request, jsonify
from app.services.session_service import SessionService
from app.exceptions import DatabaseError
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
        
    def get_session_data(self, session_id):
        try:
            session_info = self.session_service.get_session_details(session_id)

            if not session_info:
                return jsonify({'error': 'Session not found'}), 404

            project_path = session_info['project_path']
            session_name = session_info['session_name']
            
            print(f"DEBUG: Session {session_id} - project_path: {project_path}, session_name: {session_name}")
            
            # Check if this is a virtual split session
            split_info = self.session_service.session_repo.get_session_split_info(session_id)
            print(f"DEBUG: Split info: {split_info}")
            
            # Also check if session has a dataset_id for dataset-based sessions
            print(f"DEBUG: Checking session dataset info...")
            dataset_id = session_info.get('dataset_id')
            raw_session_name = session_info.get('raw_session_name')
            print(f"DEBUG: Session dataset_id: {dataset_id}, raw_session_name: {raw_session_name}")
            
            if split_info and split_info['parent_data_path']:
                # Check if we need to correct the path for dataset-based sessions
                if dataset_id and split_info['parent_data_path'] and ('raw_datasets/raw_datasets' in split_info['parent_data_path'] or not os.path.exists(split_info['parent_data_path'])):
                    print(f"DEBUG: Path needs correction, attempting to fix...")
                    # Get correct dataset path using current server's DATA_DIR
                    try:
                        from app.services.raw_dataset_service import RawDatasetService
                        raw_dataset_service = RawDatasetService()
                        dataset = raw_dataset_service.raw_dataset_repo.find_by_id(dataset_id)
                        if dataset:
                            # Use current DATA_DIR instead of stored path
                            current_data_dir = os.path.expanduser(os.getenv('DATA_DIR', '~/.delta/data'))
                            dataset_dir_name = os.path.basename(dataset['file_path'])
                            corrected_dataset_path = os.path.join(current_data_dir, 'raw_datasets', dataset_dir_name)
                            
                            # If we don't have raw_session_name, try to infer it from session name
                            if not raw_session_name:
                                session_name = session_info['session_name']
                                # Remove split suffix (.1, .2, etc) to get original session name
                                inferred_session_name = session_name.split('.')[0] if '.' in session_name else session_name
                                print(f"DEBUG: No raw_session_name, inferring from session_name: {inferred_session_name}")
                                corrected_path = os.path.join(corrected_dataset_path, inferred_session_name)
                            else:
                                corrected_path = os.path.join(corrected_dataset_path, raw_session_name)
                            
                            print(f"DEBUG: Corrected path: {corrected_path}")
                            split_info['parent_data_path'] = corrected_path
                    except Exception as e:
                        print(f"DEBUG: Could not correct path: {e}")
                
                # Virtual split session (including dataset-based sessions) - load from parent with offsets
                csv_path = os.path.join(split_info['parent_data_path'], 'accelerometer_data.csv')
                if not os.path.exists(csv_path):
                    return jsonify({'error': f'Parent CSV file not found at {csv_path}'}), 404
                
                from app.services.utils import load_dataframe_from_csv
                
                # Check if we have valid offsets (new virtual splits)
                if split_info['data_start_offset'] is not None and split_info['data_end_offset'] is not None:
                    # Use efficient loading with offsets
                    df = load_dataframe_from_csv(
                        csv_path,
                        column_prefix='accel',
                        start_offset=split_info['data_start_offset'],
                        end_offset=split_info['data_end_offset']
                    )
                else:
                    # Fallback for old virtual splits without offsets - filter by time range
                    df = pd.read_csv(csv_path)
                    if 'x' in df.columns:
                        df = df.rename(columns={'x': 'accel_x', 'y': 'accel_y', 'z': 'accel_z'})
                    
                    # Filter by session time range
                    print(f"DEBUG: session_info keys: {session_info.keys()}")
                    print(f"DEBUG: session_info: {session_info}")
                    start_ns = session_info['start_ns']
                    stop_ns = session_info['stop_ns']
                    df = df[(df['ns_since_reboot'] >= start_ns) & (df['ns_since_reboot'] <= stop_ns)]
                
                # Apply downsampling for visualization
                df = df.iloc[::50]
            elif project_path:
                # Regular session with project path - load from session directory
                csv_path = os.path.join(project_path, session_name, 'accelerometer_data.csv')
                if not os.path.exists(csv_path):
                    return jsonify({'error': f'CSV file not found at {csv_path}'}), 404
                
                df = pd.read_csv(csv_path)
                df = df.iloc[::50]
                
                # If the CSV has 'x', 'y', 'z' columns, rename them to 'accel_x', 'accel_y', 'accel_z'
                if 'x' in df.columns:
                    df = df.rename(columns={'x': 'accel_x', 'y': 'accel_y', 'z': 'accel_z'})
            else:
                # Dataset-based session without virtual split info - this shouldn't happen
                return jsonify({'error': 'Dataset-based session missing virtual split information'}), 500

            bouts = session_info['bouts']
            expected_columns = ['ns_since_reboot', 'accel_x', 'accel_y', 'accel_z']

            if not all(col in df.columns for col in expected_columns):
                return jsonify({'error': f'Invalid CSV format. Expected columns: {expected_columns}, Found: {list(df.columns)}'}), 400

            data = df[expected_columns].to_dict(orient='records')
            data = {
                'bouts': bouts,
                'data': data,
                'session_info': session_info
            }
            
            return jsonify(data)
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
                print(f"Updating session {session_id} with status={status}, keep={keep}, bouts={bouts}, verified={verified}")
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
            
            # Check if this is a virtual split session that needs parent data
            split_info = self.session_service.session_repo.get_session_split_info(session_id)
            if split_info and split_info['parent_data_path']:
                # Virtual split session - load from parent data file
                csv_path = os.path.join(split_info['parent_data_path'], 'accelerometer_data.csv')
                if not os.path.exists(csv_path):
                    return jsonify({'error': f'Parent CSV file not found at {csv_path}'}), 404
                
                # Load the session data using virtual split logic
                from app.services.utils import load_dataframe_from_csv
                if split_info['data_start_offset'] is not None and split_info['data_end_offset'] is not None:
                    # Use efficient loading with offsets
                    df = load_dataframe_from_csv(
                        csv_path,
                        column_prefix='accel',
                        start_offset=split_info['data_start_offset'],
                        end_offset=split_info['data_end_offset']
                    )
                else:
                    # Fallback for old virtual splits - filter by time range
                    df = pd.read_csv(csv_path)
                    if 'x' in df.columns:
                        df = df.rename(columns={'x': 'accel_x', 'y': 'accel_y', 'z': 'accel_z'})
                    
                    # Filter by session time range to get only this virtual split's data
                    start_ns = session_info['start_ns']
                    stop_ns = session_info['stop_ns']
                    df = df[(df['ns_since_reboot'] >= start_ns) & (df['ns_since_reboot'] <= stop_ns)]
                    
                # IMPORTANT: Reset index so split point calculations work correctly
                # The split points are relative to the filtered dataframe, not the original
                df = df.reset_index(drop=True)
            else:
                # Regular session - load from session directory
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

            # Calculate virtual split segments with offsets
            segment_offsets = []
            start_idx = 0
            for idx in split_indices:
                if start_idx < idx:  # Only add if segment has data
                    segment_offsets.append((start_idx, idx))
                start_idx = idx
            # Add final segment
            if start_idx < len(df):
                segment_offsets.append((start_idx, len(df)))

            if len(segment_offsets) < 2:
                return jsonify({'error': 'Split would not create multiple valid recordings'}), 400

            # Define time ranges for each segment
            segment_ranges = []
            for start_offset, end_offset in segment_offsets:
                segment_df = df.iloc[start_offset:end_offset]
                start_time = segment_df['ns_since_reboot'].min()
                end_time = segment_df['ns_since_reboot'].max()
                segment_ranges.append((start_time, end_time))
            
            # Assign bouts to segments based on time ranges
            segment_bouts = [[] for _ in segment_ranges]
            
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
                        adjusted_bout = {'start': float(segment_start), 'end': float(bout_end), 'label': bout_label}
                        segment_bouts[i].append(adjusted_bout)
                        break
                    # If bout overlaps with segment end
                    elif segment_start <= bout_start <= segment_end and bout_end > segment_end:
                        # Adjust bout to end at segment boundary
                        adjusted_bout = {'start': float(bout_start), 'end': float(segment_end), 'label': bout_label}
                        segment_bouts[i].append(adjusted_bout)
                        break
                    # If bout spans entire segment
                    elif bout_start < segment_start and bout_end > segment_end:
                        # Create a bout for the entire segment
                        adjusted_bout = {'start': float(segment_start), 'end': float(segment_end), 'label': bout_label}
                        segment_bouts[i].append(adjusted_bout)
                        break

            # Pre-generate all unique names to avoid transaction conflicts
            generated_names = []
            for i in range(len(segment_offsets)):
                # Generate name that doesn't conflict with database OR previously generated names in this batch
                base_counter = 1
                while True:
                    candidate_name = f"{session_name}.{base_counter}"
                    
                    # Check if this name conflicts with previously generated names in this batch
                    if candidate_name in generated_names:
                        base_counter += 1
                        continue
                        
                    # Check database for collision
                    count = self.session_service.session_repo.count_sessions_by_name_and_project(candidate_name, session_info['project_id'])
                    if count == 0:
                        generated_names.append(candidate_name)
                        break
                    
                    base_counter += 1
            
            # Create virtual split sessions (no physical file creation)
            new_sessions = []
            for i, (start_offset, end_offset) in enumerate(segment_offsets):
                new_name = generated_names[i]
                
                # Calculate start_ns and stop_ns for this segment
                segment_start_ns, segment_stop_ns = segment_ranges[i]
                
                # Calculate absolute offsets relative to the original parent file
                absolute_start_offset = start_offset
                absolute_end_offset = end_offset
                
                # If we're splitting a virtual split, adjust offsets relative to parent
                session_split_info = self.session_service.session_repo.get_session_split_info(session_id)
                if session_split_info and session_split_info['parent_data_path']:
                    if session_split_info['data_start_offset'] is not None:
                        # Add the parent's start offset to make it absolute
                        absolute_start_offset = session_split_info['data_start_offset'] + start_offset
                        absolute_end_offset = session_split_info['data_start_offset'] + end_offset
                    # If parent doesn't have offsets, we can't calculate absolute offsets
                    # so we'll use None and fall back to time-based filtering
                    else:
                        absolute_start_offset = None
                        absolute_end_offset = None
                
                new_sessions.append({
                    'name': new_name,
                    'bouts': segment_bouts[i],
                    'start_ns': int(segment_start_ns),
                    'stop_ns': int(segment_stop_ns),
                    'data_start_offset': absolute_start_offset,
                    'data_end_offset': absolute_end_offset
                })
                
            try:
                created_sessions = self.session_service.split_session(session_id, session_info, new_sessions)
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500

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