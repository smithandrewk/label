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
            
            csv_path = os.path.join(project_path, session_name, 'accelerometer_data.csv')

            if not os.path.exists(csv_path):
                return jsonify({'error': f'CSV file not found at {csv_path}'}), 404
            
            df = pd.read_csv(csv_path)
            df = df.iloc[::50]
            
            bouts = session_info['bouts']
            
            expected_columns = ['ns_since_reboot', 'x', 'y', 'z']
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
            
            # Read original CSV from the project directory
            csv_path = os.path.join(project_path, session_name, 'accelerometer_data.csv')
            if not os.path.exists(csv_path):
                return jsonify({'error': f'CSV file not found at {csv_path}'}), 404
            
            df = pd.read_csv(csv_path)
            expected_columns = ['ns_since_reboot', 'x', 'y', 'z']
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
                
                os.makedirs(new_dir)
                segment.to_csv(os.path.join(new_dir, 'accelerometer_data.csv'), index=False)
                new_sessions.append({
                    'name': new_name,
                    'bouts': segment_bouts[i]
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