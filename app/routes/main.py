from flask import Blueprint, render_template, jsonify
import json
from datetime import datetime
from app.exceptions import DatabaseError
import logging
import traceback

main_bp = Blueprint('main', __name__)

class MainController:
    def __init__(self, project_service, session_service):
        self.project_service = project_service
        self.session_service = session_service

    def export_labels(self):
        """Export all labels for all projects and sessions"""
        try:
            try:
                sessions = self.session_service.get_all_sessions_with_details()
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500
            
            # Process the data for export - hierarchical structure
            projects_dict = {}
            total_labels_count = 0
            
            for session in sessions:
                # Parse bouts data
                bouts = []
                if session['bouts']:
                    try:
                        bouts_data = session['bouts']
                        if isinstance(bouts_data, str):
                            bouts = json.loads(bouts_data)
                        elif isinstance(bouts_data, (list, dict)):
                            bouts = bouts_data
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"Error parsing bouts for session {session['session_id']}: {e}")
                        bouts = []
                
                # Process bouts into structured format
                processed_bouts = []
                if isinstance(bouts, list) and len(bouts) > 0:
                    for i, bout in enumerate(bouts):
                        if isinstance(bout, list) and len(bout) >= 2:
                            processed_bout = {
                                'bout_index': i,
                                'start_time': bout[0] if len(bout) > 0 else None,
                                'end_time': bout[1] if len(bout) > 1 else None,
                                'duration_ns': bout[1] - bout[0] if len(bout) >= 2 else None,
                                'duration_seconds': (bout[1] - bout[0]) / 1e9 if len(bout) >= 2 else None,
                                'label': bout[2] if len(bout) > 2 else 'smoking',  # Default label
                                'confidence': bout[3] if len(bout) > 3 else None
                            }
                            processed_bouts.append(processed_bout)
                            total_labels_count += 1
                        elif isinstance(bout, dict):
                            processed_bout = {
                                'bout_index': i,
                                'start_time': bout.get('start'),
                                'end_time': bout.get('end'),
                                'duration_ns': bout.get('end') - bout.get('start') if bout.get('start') and bout.get('end') else None,
                                'duration_seconds': (bout.get('end') - bout.get('start')) / 1e9 if bout.get('start') and bout.get('end') else None, 
                                'label': bout.get('label','smoking'),
                                'confidence': bout.get('confidence')
                            }
                            processed_bouts.append(processed_bout)
                            total_labels_count += 1

                
                # Create session object
                session_obj = {
                    'session_id': session['session_id'],
                    'session_name': session['session_name'],
                    'status': session['status'],
                    'verified': bool(session['verified']),
                    'bout_count': len(processed_bouts),
                    'bouts': processed_bouts
                }
                
                # Group by project
                project_key = session['project_id']
                if project_key not in projects_dict:
                    projects_dict[project_key] = {
                        'project_id': session['project_id'],
                        'project_name': session['project_name'],
                        'project_path': session['project_path'],
                        'participant': {
                            'participant_id': session['participant_id'],
                            'participant_code': session['participant_code']
                        },
                        'session_count': 0,
                        'total_bouts': 0,
                        'sessions': []
                    }
                
                # Add session to project
                projects_dict[project_key]['sessions'].append(session_obj)
                projects_dict[project_key]['session_count'] += 1
                projects_dict[project_key]['total_bouts'] += len(processed_bouts)
            
            # Convert to list format
            projects_list = list(projects_dict.values())
            
            return jsonify({
                'success': True,
                'total_projects': len(projects_list),
                'total_sessions': len(sessions),
                'total_labels': total_labels_count,
                'export_timestamp': datetime.now().isoformat(),
                'projects': projects_list
            })
            
        except Exception as e:
            logging.error(f"Error in export_labels: {str(e)}")
            logging.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500

controller = None

def init_controller(project_service, session_service):
    global controller
    controller = MainController(project_service, session_service)

@main_bp.route('/')
def serve_participants():
    return render_template('participants.html', active_view='participants')

@main_bp.route('/sessions')
def serve_index():
    print("Serving index page for sessions")
    return render_template('sessions.html', active_view='sessions')

@main_bp.route('/settings')
def serve_settings():
    return render_template('settings.html', active_view='settings')

@main_bp.route('/raw-datasets')
def serve_raw_datasets():
    return render_template('raw_datasets.html', active_view='raw_datasets')

# Export labels for all projects and sessions
@main_bp.route('/api/export/labels')
def export_labels():
    return controller.export_labels()