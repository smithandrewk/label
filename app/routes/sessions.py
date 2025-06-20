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
            show_split = request.args.get('show_split', '0') == '1'  # Optional parameter to show split sessions
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
            
            # Get the root session that contains the data
            root_session_name = self._find_root_session_name(session_info)
            start_idx = session_info['start_idx']
            stop_idx = session_info['stop_idx']
            
            # Pass all the necessary information for properly loading data
            scoring_id = self.model_service.score_session_async(
                project_path=project_path, 
                session_name=session_name, 
                session_id=session_id,
                root_session_name=root_session_name,
                start_idx=start_idx,
                stop_idx=stop_idx
            )
            
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
            parent_name = session_info['parent_name']
            start_idx = session_info['start_idx']
            stop_idx = session_info['stop_idx']
            
            # Follow parent chain to find the root session (original data file)
            root_session_name = self._find_root_session_name(session_info)
            print(f"Root session name: {root_session_name}")
            
            csv_path = os.path.join(project_path, root_session_name, 'accelerometer_data.csv')
            print(f"Looking for CSV at: {csv_path}")
            print(f"Start index: {start_idx}, Stop index: {stop_idx}")
            if not os.path.exists(csv_path):
                print(f"CSV file not found at {csv_path}")
                return jsonify({'error': f'CSV file not found at {csv_path}'}), 404
                
            # First read just the header to get column names
            headers = pd.read_csv(csv_path, nrows=0).columns.tolist()
            expected_columns = ['ns_since_reboot', 'x', 'y', 'z']
                
            if start_idx is not None and stop_idx is not None:
                print(f"Reading CSV from {start_idx} to {stop_idx}")
                # Use header=None to indicate no header in the data portion, then set column names manually
                df = pd.read_csv(csv_path, skiprows=start_idx+1, nrows=stop_idx - start_idx, header=None)
                df.columns = headers
            elif start_idx is not None:
                print(f"Reading CSV from {start_idx} to end")
                df = pd.read_csv(csv_path, skiprows=start_idx+1, header=None)
                df.columns = headers
            else:
                df = pd.read_csv(csv_path)

            df = df.iloc[::50]
            
            bouts = session_info['bouts']
            
            # Verify columns after loading
            if not all(col in df.columns for col in expected_columns):
                logging.error(f"Invalid CSV format. Expected columns: {expected_columns}, Found: {list(df.columns)}")
                
                # Check if we have data but with wrong column names (could be numeric indices)
                if len(df.columns) >= len(expected_columns) and all(col.isdigit() for col in df.columns.astype(str)):
                    logging.warning("Column names are numeric indices, attempting to fix by applying expected column names")
                    # Rename columns to expected names
                    rename_map = {i: col for i, col in enumerate(headers) if i < len(df.columns)}
                    df = df.rename(columns=rename_map)
                else:
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
                rows_affected = self.session_service.update_session(session_id, status, keep, bouts, verified)
                if rows_affected == 0:
                    return jsonify({'error': 'Session not found'}), 404
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500
            
            if rows_affected == 0:
                return jsonify({'warning': 'No session found with that ID'}), 200
                
            return jsonify({'message': 'Metadata updated', 'rows_affected': rows_affected})
        except Exception as e:
            print(f"Error updating session metadata: {e}")
            return jsonify({'error': str(e)}), 500
        
    def split_session(self, session_id):
        try:
            data = request.get_json()
            split_points = data.get('split_points')  # list of ns_since_reboot timestamps
            print(split_points)

            if not split_points or not isinstance(split_points, list) or len(split_points) == 0:
                return jsonify({'error': 'At least one split point required'}), 400

            session_info = self.session_service.get_session_details(session_id)
            if not session_info:
                return jsonify({'error': 'Session not found'}), 404
            
            session_name = session_info['session_name']
            project_path = session_info['project_path']
            
            try:
                parent_bouts = json.loads(session_info['bouts'] or '[]')
                # Convert to list if it's not already
                if isinstance(parent_bouts, str):
                    parent_bouts = json.loads(parent_bouts)
            except json.JSONDecodeError:
                parent_bouts = []
            
            print(f"Parent bouts: {parent_bouts}")
            
            # Find the root session that contains the original data file
            root_session_name = self._find_root_session_name(session_info)
            print(f"Root session name for data: {root_session_name}")

            csv_path = os.path.join(project_path, root_session_name, 'accelerometer_data.csv')
            if not os.path.exists(csv_path):
                return jsonify({'error': f'CSV file not found at {csv_path}'}), 404
            
            # Read the CSV file with proper header handling
            df = pd.read_csv(csv_path)
            expected_columns = ['ns_since_reboot', 'x', 'y', 'z']
            
            if not all(col in df.columns for col in expected_columns):
                logging.error(f"Invalid CSV format. Expected columns: {expected_columns}, Found: {list(df.columns)}")
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

            print(f"Split indices: {split_indices}")
            print(f"Split timestamps: {split_timestamps}")

            # Split data into segments
            segments = []
            segment_ranges_indices = []  # Store [start_idx, stop_idx] for each segment
            start_idx = 0
            
            # Create segments from the split points
            for idx in split_indices:
                # Each segment goes from start_idx up to and including idx
                segment = df.iloc[start_idx:idx + 1][expected_columns]
                if not segment.empty:
                    segments.append(segment)
                    segment_ranges_indices.append([start_idx, idx])
                    print(f"Created segment from index {start_idx} to {idx}")
                start_idx = idx + 1
                
            # Add final segment from last split point to end
            final_segment = df.iloc[start_idx:][expected_columns]
            if not final_segment.empty:
                segments.append(final_segment)
                segment_ranges_indices.append([start_idx, len(df) - 1])
                print(f"Created final segment from index {start_idx} to {len(df) - 1}")
                
            print(f"Created {len(segments)} segments with index ranges: {segment_ranges_indices}")

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
                # Each bout is [start_time, stop_time]
                if len(bout) != 2:
                    continue  # Skip malformed bouts
                    
                bout_start = bout[0]
                bout_end = bout[1]
                
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
                print(new_name)
                
                # Get the root session name for proper lineage tracking
                root_session_name = self._find_root_session_name(session_info)
                
                # Use the precomputed segment indices
                segment_start_idx = segment_ranges_indices[i][0]
                segment_stop_idx = segment_ranges_indices[i][1]
                
                print(f"Segment {i+1} indices: start={segment_start_idx}, stop={segment_stop_idx}")
                
                new_sessions.append({
                    'name': new_name,
                    'bouts': segment_bouts[i],
                    'start_idx': segment_start_idx,
                    'stop_idx': segment_stop_idx,
                    'root_session_name': root_session_name
                })

            # Copy original log file to new directories
            # log_path = os.path.join(project_path, session_name, 'log.csv')
            # if os.path.exists(log_path):
            #     for session_data in new_sessions:
            #         shutil.copy(log_path, os.path.join(project_path, session_data['name'], 'log.csv'))
            # else:
            #     print(f"Log file not found at {log_path}. Skipping copy.")
            
            try:
                created_sessions = self.session_service.split_session(session_id, session_info, new_sessions)
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500

            # Delete original session directory
            # shutil.rmtree(os.path.join(project_path, session_name))

            return jsonify({
                'message': 'Session split successfully', 
                'new_sessions': [s['name'] for s in new_sessions]
            })
        except Exception as e:
            print(f"Error splitting session: {e}")
            return jsonify({'error': str(e)}), 500
        except DatabaseError as e:
            return jsonify({'error': str(e)}), 500

    def _find_root_session_name(self, session_info):
        """
        Traverse the parent chain to find the root session name (original data source).
        
        Args:
            session_info: Dictionary containing session metadata including 'parent_name'
            
        Returns:
            str: The session name of the root session that contains the original data file
        """
        current_session = session_info
        visited = set()  # To prevent infinite loops in case of circular references
        
        while current_session and current_session['parent_name'] and current_session['session_name'] != current_session['parent_name']:
            # Add current session to visited set
            visited.add(current_session['session_name'])
            
            # Get parent session info
            try:
                # Find parent session by name in the same project
                parent_sessions = self.session_service.get_sessions(
                    project_id=current_session['project_id'], 
                    show_split=True  # Need to include split sessions since they might be parents
                )
                
                parent_session = next(
                    (s for s in parent_sessions if s['session_name'] == current_session['parent_name']),
                    None
                )
                
                if not parent_session:
                    # Parent not found, return the current session name
                    return current_session['parent_name']
                
                # Check for circular reference
                if parent_session['session_name'] in visited:
                    print(f"Warning: Circular reference detected in session lineage: {parent_session['session_name']}")
                    return current_session['parent_name']
                
                # Get full parent session details
                parent_session_details = self.session_service.get_session_details(parent_session['session_id'])
                if not parent_session_details:
                    return current_session['parent_name']
                
                current_session = parent_session_details
            except Exception as e:
                print(f"Error traversing session lineage: {e}")
                return current_session['parent_name']
        
        # Return the name of the root session
        return current_session['session_name']
        
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