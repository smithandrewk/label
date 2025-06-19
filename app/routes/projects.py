from flask import Blueprint, request, jsonify
import os
from datetime import datetime
import threading
import uuid
import shutil
from app.exceptions import DatabaseError
import logging
import traceback

DATA_DIR = os.getenv('DATA_DIR', '~/.delta/data')

projects_bp = Blueprint('projects', __name__)

class ProjectController:
    def __init__(self, project_service, session_service):
        self.project_service = project_service
        self.session_service = session_service

    def list_projects(self):
        try:
            return self.project_service.list_projects()
        except Exception as e:
            logging.error(f"Error in list_projects: {str(e)}")
            logging.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500
    
    def upload_new_project(self):
        try:
            # Handle multipart form data for file uploads
            if 'files' not in request.files:
                return jsonify({'error': 'No files uploaded'}), 400
            
            # Get form data
            project_name = request.form.get('name')
            participant_code = request.form.get('participant')
            folder_name = request.form.get('folderName')
            
            if not all([project_name, participant_code, folder_name]):
                return jsonify({'error': 'Missing required fields: name, participant, or folderName'}), 400
            
            # Get uploaded files
            uploaded_files = request.files.getlist('files')
            if not uploaded_files:
                return jsonify({'error': 'No files uploaded'}), 400

            participant = self.project_service.get_participant_by_code(participant_code)
            if participant:
                # Use existing participant
                participant_id = participant['participant_id']
            else:
                # Create new participant
                created_participant = self.project_service.create_participant(participant_code)
                participant_id = created_participant['participant_id']

            # Create new directory in central data store
            central_data_dir = os.path.expanduser(DATA_DIR)
            os.makedirs(central_data_dir, exist_ok=True)
            
            # Create a unique project directory name
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            project_dir_name = f"{project_name}_{participant_code}_{timestamp}"
            new_project_path = os.path.join(central_data_dir, project_dir_name)
            
            # Create the project directory structure from uploaded files
            try:
                os.makedirs(new_project_path, exist_ok=True)
                
                # Process uploaded files and recreate directory structure
                for file in uploaded_files:
                    if file.filename and file.filename != '':
                        # Get relative path within the selected folder
                        relative_path = file.filename
                        if '/' in relative_path:
                            # Remove the root folder name from the path since we're creating our own structure
                            path_parts = relative_path.split('/')
                            if len(path_parts) > 1:
                                relative_path = '/'.join(path_parts[1:])  # Remove the first part (root folder name)
                        
                        # Create full file path
                        file_path = os.path.join(new_project_path, relative_path)
                        
                        # Create directories if they don't exist
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        
                        # Save the file
                        file.save(file_path)
                        
            except Exception as e:
                # Clean up on error
                if os.path.exists(new_project_path):
                    shutil.rmtree(new_project_path)
                return jsonify({'error': f'Failed to save uploaded files: {str(e)}'}), 500


            created_project = self.project_service.insert_project(project_name, participant_id, new_project_path) # dictionary

            project_id = created_project['project_id']

            # Find all session directories in the uploaded project
            sessions = []
            if os.path.exists(new_project_path):
                for item in os.listdir(new_project_path):
                    item_path = os.path.join(new_project_path, item)
                    if os.path.isdir(item_path):
                        accel_file = os.path.join(item_path, 'accelerometer_data.csv')
                        if os.path.exists(accel_file):
                            sessions.append({'name': item, 'file': 'accelerometer_data.csv'})
                
                # Sort sessions by date/time in the name
                try:
                    sessions.sort(key=lambda s: datetime.strptime('_'.join(s['name'].split('_')[:4]), '%Y-%m-%d_%H_%M_%S'))
                except:
                    # If sorting fails, keep original order
                    pass

            # Generate unique upload ID for progress tracking
            upload_id = str(uuid.uuid4())
            
            # Start async processing in a separate thread
            if sessions:
                processing_thread = threading.Thread(
                    target=self.session_service.process_sessions_async,
                    args=(upload_id, sessions, new_project_path, project_id)
                )
                processing_thread.daemon = True
                processing_thread.start()
            else:
                # No sessions to process
                self.session_service.upload_progress[upload_id] = {
                    'status': 'complete',
                    'message': 'No sessions found in uploaded project',
                    'total_sessions_created': 0
                }
                        
            return jsonify({
                'message': 'Project upload started',
                'project_id': project_id,
                'participant_id': participant_id,
                'central_path': new_project_path,
                'upload_id': upload_id,
                'sessions_found': len(sessions),
                'files_uploaded': len(uploaded_files),
                'progress_url': f'/api/upload-progress/{upload_id}'
            })
            
        except Exception as e:
            logging.error(f"Error in upload_new_project: {str(e)}")
            logging.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': f'Upload failed: {str(e)}'}), 500
        
    def delete_project(self, project_id):
        try:
            try:
                project_info = self.project_service.get_project_with_participant(project_id)
                if not project_info:
                    return jsonify({'error': 'Project not found'}), 404
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500
            
            project_path = project_info['path']
            participant_id = project_info['participant_id']
            
            try:
                # Delete session lineage records first (due to foreign key constraints)
                self.session_service.delete_session_lineage_by_project(project_id)
                
                # Delete sessions (this will cascade due to foreign key)
                sessions_deleted = self.session_service.delete_sessions_by_project(project_id)
                
                # Delete the project
                self.project_service.delete_project(project_id)
                
            except DatabaseError as e:
                if 'Project not found' in str(e):
                    return jsonify({'error': str(e)}), 404
                return jsonify({'error': str(e)}), 500
            
            try:
                participant_deleted = self.project_service.cleanup_participant_if_needed(participant_id)
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500
            
            directory_deleted = False
            if project_path and os.path.exists(project_path):
                try:
                    shutil.rmtree(project_path)
                    directory_deleted = True
                    print(f"Deleted project directory: {project_path}")
                except Exception as e:
                    print(f"Warning: Could not delete project directory {project_path}: {e}")
                    # Don't fail the entire operation if directory deletion fails
            
            return jsonify({
                'message': 'Project deleted successfully',
                'project_id': project_id,
                'project_name': project_info['project_name'],
                'participant_code': project_info['participant_code'],
                'sessions_deleted': sessions_deleted,
                'directory_deleted': directory_deleted,
                'participant_deleted': participant_deleted,
                'directory_path': project_path
            })
            
        except Exception as e:
            print(f"Error deleting project: {e}")
            return jsonify({'error': f'Failed to delete project: {str(e)}'}), 500

    def list_participants(self):
        try:
            try:
                participants = self.project_service.get_all_participants_with_stats()
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500
            # Process the results to convert project_ids from string to array
            for participant in participants:
                if participant['project_ids']:
                    participant['project_ids'] = [int(id.strip()) for id in participant['project_ids'].split(',')]
                else:
                    participant['project_ids'] = []
                    
                if not participant['project_names']:
                    participant['project_names'] = ''
            

            return jsonify(participants)
        except Exception as e:
            print(f"Error listing participants: {e}")
            return jsonify({'error': str(e)}), 500

    def create_participant(self):
        try:
            data = request.get_json()
            participant_code = data.get('participant_code')
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            email = data.get('email', '')
            notes = data.get('notes', '')
            
            if not participant_code:
                return jsonify({'error': 'Participant code is required'}), 400
            
            try:
                created_participant = self.project_service.create_participant_with_details(
                    participant_code, first_name, last_name, email, notes
                )
                return jsonify({
                    'message': 'Participant created successfully',
                    'participant_id': created_participant['participant_id'],
                    'participant_code': created_participant['participant_code']
                })
            except DatabaseError as e:
                if 'already exists' in str(e):
                    return jsonify({'error': str(e)}), 400
                return jsonify({'error': str(e)}), 500
                    
        except Exception as e:
            print(f"Error creating participant: {e}")
            return jsonify({'error': str(e)}), 500

    def update_participant(self, participant_id):
        try:
            data = request.get_json()
            participant_code = data.get('participant_code')
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            email = data.get('email', '')
            notes = data.get('notes', '')
            
            if not participant_code:
                return jsonify({'error': 'Participant code is required'}), 400
            
            try:
                updated_participant = self.project_service.update_participant(
                    participant_id, participant_code, first_name, last_name, email, notes
                )
                return jsonify({
                    'message': 'Participant updated successfully',
                    'participant_id': updated_participant['participant_id'],
                    'participant_code': updated_participant['participant_code']
                })
            except DatabaseError as e:
                if 'not found' in str(e):
                    return jsonify({'error': str(e)}), 404
                elif 'already exists' in str(e):
                    return jsonify({'error': str(e)}), 400
                return jsonify({'error': str(e)}), 500
                    
        except Exception as e:
            print(f"Error updating participant: {e}")
            return jsonify({'error': str(e)}), 500

    def delete_participant(self, participant_id):
        try:
            try:
                # First, get participant information
                participant_info = self.project_service.get_participant_info(participant_id)
                if not participant_info:
                    return jsonify({'error': 'Participant not found'}), 404
                
                # Get all projects for this participant to delete associated data
                projects_to_delete = self.project_service.get_participant_projects(participant_id)
                
                # Count sessions to be deleted
                session_count = self.project_service.count_participant_sessions(participant_id)
                
                # Delete participant and all associated data
                deletion_stats = self.project_service.delete_participant_cascade(participant_id)
                
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500
            
            # Delete project directories from filesystem
            for project in projects_to_delete:
                project_path = project['path']
                if project_path and os.path.exists(project_path):
                    try:
                        shutil.rmtree(project_path)
                        print(f"Deleted project directory: {project_path}")
                    except Exception as e:
                        print(f"Warning: Could not delete project directory {project_path}: {e}")
                        # Don't fail the entire operation if directory deletion fails
            
            return jsonify({
                'message': 'Participant deleted successfully',
                'participant_id': participant_id,
                'participant_code': participant_info['participant_code'],
                'projects_deleted': deletion_stats['projects_deleted'],
                'sessions_deleted': deletion_stats['sessions_deleted']
            })
            
        except Exception as e:
            print(f"Error deleting participant: {e}")
            return jsonify({'error': f'Failed to delete participant: {str(e)}'}), 500

    def upload_progress_stream(self, upload_id):
        """Server-Sent Events endpoint for upload progress tracking"""
        import json
        import time
        from flask import Response
        
        print(f"SSE connection established for upload {upload_id}")
        print(f"Current upload_progress keys: {list(self.session_service.upload_progress.keys())}")
        
        def generate_progress():
            # Check if upload_id exists before starting
            if upload_id not in self.session_service.upload_progress:
                print(f"Upload ID {upload_id} not found in progress tracking")
                yield f"data: {json.dumps({'status': 'error', 'message': 'Upload not found'})}\n\n"
                return
                
            while upload_id in self.session_service.upload_progress:
                progress_data = self.session_service.upload_progress[upload_id]
                print(f"Sending progress update for {upload_id}: {progress_data}")
                yield f"data: {json.dumps(progress_data)}\n\n"
                
                # If upload is complete, send final message and stop
                if progress_data.get('status') == 'complete':
                    print(f"Upload {upload_id} complete, closing SSE connection")
                    # Clean up progress data after a short delay
                    import threading
                    threading.Timer(5.0, lambda: self.session_service.upload_progress.pop(upload_id, None)).start()
                    break
                elif progress_data.get('status') == 'error':
                    print(f"Upload {upload_id} error, closing SSE connection")
                    threading.Timer(5.0, lambda: self.session_service.upload_progress.pop(upload_id, None)).start()
                    break
                    
                time.sleep(0.5)  # Update every 500ms
        
        response = Response(generate_progress(), mimetype='text/event-stream')
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

controller = None

def init_controller(session_service, project_service):
    global controller
    controller = ProjectController(session_service=session_service, project_service=project_service)

@projects_bp.route('/api/project/upload', methods=['POST'])
def upload_new_project():
    return controller.upload_new_project()

@projects_bp.route('/api/projects')
def list_projects():
    return controller.list_projects()

@projects_bp.route('/api/project/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    return controller.delete_project(project_id)

@projects_bp.route('/api/participants')
def list_participants():
    return controller.list_participants()

@projects_bp.route('/api/participants', methods=['POST'])
def create_participant():
    return controller.create_participant()

@projects_bp.route('/api/participants/<int:participant_id>', methods=['DELETE'])
def delete_participant(participant_id):
    return controller.delete_participant(participant_id)

# Update participant
@projects_bp.route('/api/participants/<int:participant_id>', methods=['PUT'])
def update_participant(self, participant_id):
    return controller.update_participant(participant_id)

@projects_bp.route('/api/upload-progress/<upload_id>', methods=['GET'])
def upload_progress_stream(upload_id):
    return controller.upload_progress_stream(upload_id)
    return controller.upload_progress_stream(upload_id)