from flask import Blueprint, request, jsonify, Response
import os
from datetime import datetime
import threading
import uuid
import shutil
from app.exceptions import DatabaseError
from app.logging_config import get_logger
import traceback
import json
from app.services.project_service import ProjectService
from app.services.session_service import SessionService

logger = get_logger(__name__)

DATA_DIR = os.getenv('DATA_DIR', '~/.delta/data')

projects_bp = Blueprint('projects', __name__)

class ProjectController:
    def __init__(self, project_service, session_service):
        self.project_service: ProjectService = project_service
        self.session_service: SessionService = session_service

    def list_projects(self):
        try:
            return self.project_service.list_projects()
        except Exception as e:
            logger.error(f"Error in list_projects: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500
    
    def upload_new_project(self):
        try:
            project_name = request.form.get('name')
            participant_code = request.form.get('participant')
            project_path = request.form.get('projectPath')
            
            if not all([project_name, participant_code, project_path]):
                return jsonify({'error': 'Missing required fields: name, participant, or folderName'}), 400 
            
            project_result = self.project_service.create_project_with_files(
                project_name, participant_code, project_path, DATA_DIR
            )

            logger.info(f"Project upload result: {project_result}")
            project_id = project_result['project_id']
            participant_id = project_result['participant_id']
            new_project_path = project_result['project_path']

            sessions = self.project_service.discover_project_sessions(new_project_path)
            logger.info(f"Discovered {len(sessions) if sessions else 0} sessions in project {project_name} at {new_project_path}")
            
            # Ensure sessions is always a list
            if not isinstance(sessions, list):
                logger.warning(f"Sessions discovery returned non-list: {type(sessions)}, using empty list")
                sessions = []
            
            print(sessions)
            upload_id = str(uuid.uuid4())
            logger.info(f"Generated upload ID: {upload_id}")
            
            skipped_sessions = self.session_service.validate_sessions(sessions, new_project_path)
            sessions = [s for s in sessions if s['name'] not in skipped_sessions]
            for session in sessions:
                logger.info(f"Processing session: {session['name']}")
                bouts = self.session_service.load_bouts_from_labels_json(new_project_path, session)
                
                # Ensure bouts is always a list to prevent iteration errors
                if not isinstance(bouts, list):
                    logger.warning(f"Bouts for session {session['name']} is not a list: {type(bouts)}, using empty list")
                    bouts = []
                
                for bout in bouts:
                    if 'label' not in bout:
                        bout['label'] = 'smoking'
                created_sessions = self.session_service.preprocess_and_split_session_on_upload(
                    session_name=session['name'],
                    project_path=new_project_path,
                    project_id=project_id,
                    parent_bouts=bouts
                )

            return jsonify({
                'message': 'Project upload started',
                'project_id': project_id,
                'participant_id': participant_id,
                'central_path': new_project_path,
                'upload_id': upload_id,
                'sessions_found': len(sessions)
            })
            
        except Exception as e:
            logger.error(f"Error in upload_new_project: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': f'Upload failed: {str(e)}'}), 500
        
    def delete_project(self, project_id):
        try:
            # Get project info before deletion for response
            project_info = self.project_service.get_project_with_participant(project_id)
            if not project_info:
                return jsonify({'error': 'Project not found'}), 404
            
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
                    logger.info(f"Deleted project directory: {project_path}")
                except Exception as e:
                    logger.warning(f"Could not delete project directory {project_path}: {e}")
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
            logger.error(f"Error deleting project: {e}")
            return jsonify({'error': f'Failed to delete project: {str(e)}'}), 500

    def rename_project(self, project_id):
        try:
            data = request.get_json()
            if not data or 'name' not in data:
                return jsonify({'error': 'Missing required field: name'}), 400
            
            new_name = data['name']
            
            # Rename the project
            self.project_service.rename_project(project_id, new_name)
            
            # Get updated project info for response
            project_info = self.project_service.get_project_with_participant(project_id)
            
            return jsonify({
                'message': 'Project renamed successfully',
                'project_id': project_id,
                'project_name': project_info['project_name'],
                'participant_code': project_info['participant_code']
            })
            
        except DatabaseError as e:
            if 'Project not found' in str(e):
                return jsonify({'error': str(e)}), 404
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            logger.error(f"Error renaming project: {e}")
            return jsonify({'error': f'Failed to rename project: {str(e)}'}), 500

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
            logger.error(f"Error listing participants: {e}")
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
            logger.error(f"Error creating participant: {e}")
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
            logger.error(f"Error updating participant: {e}")
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
                        logger.info(f"Deleted project directory: {project_path}")
                    except Exception as e:
                        logger.warning(f"Could not delete project directory {project_path}: {e}")
                        # Don't fail the entire operation if directory deletion fails
            
            return jsonify({
                'message': 'Participant deleted successfully',
                'participant_id': participant_id,
                'participant_code': participant_info['participant_code'],
                'projects_deleted': deletion_stats['projects_deleted'],
                'sessions_deleted': deletion_stats['sessions_deleted']
            })
            
        except Exception as e:
            logger.error(f"Error deleting participant: {e}")
            return jsonify({'error': f'Failed to delete participant: {str(e)}'}), 500

    def update_project_participant(self, project_id):
        """Update which participant a project is assigned to"""
        try:
            data = request.get_json()
            new_participant_id = data.get('participant_id')
            
            if not new_participant_id:
                return jsonify({'error': 'Participant ID is required'}), 400
            
            try:
                result = self.project_service.update_project_participant(project_id, new_participant_id)
                
                # Get updated project info for response
                updated_project = self.project_service.get_project_with_participant(project_id)
                
                return jsonify({
                    'message': 'Project participant updated successfully',
                    'project_id': project_id,
                    'project_name': updated_project['project_name'],
                    'old_participant_id': result['old_participant_id'],
                    'new_participant_id': result['new_participant_id'],
                    'new_participant_code': updated_project['participant_code'],
                    'participant_cleaned_up': result['participant_cleaned_up']
                })
                
            except DatabaseError as e:
                if 'not found' in str(e):
                    return jsonify({'error': str(e)}), 404
                return jsonify({'error': str(e)}), 500
                
        except Exception as e:
            logger.error(f"Error updating project participant: {e}")
            return jsonify({'error': str(e)}), 500

    def bulk_upload_projects(self):
        """Upload multiple projects from a parent directory structure"""
        try:
            # Handle multipart form data for file uploads
            if 'files' not in request.files:
                return jsonify({'error': 'No files uploaded'}), 400
            
            # Get uploaded files
            uploaded_files = request.files.getlist('files')
            if not uploaded_files:
                return jsonify({'error': 'No files uploaded'}), 400

            # Debug: Log some file information
            logger.info(f"Received {len(uploaded_files)} files for bulk upload")
            for i, file in enumerate(uploaded_files[:5]):  # Log first 5 files
                logger.info(f"File {i}: filename='{file.filename}', name='{file.name}'")

            # First, ensure a "Bulk Upload" participant exists
            bulk_participant_code = "BULK_UPLOAD"

            try:
                bulk_participant = self.project_service.get_participant_by_code(bulk_participant_code)
                if not bulk_participant:
                    # Create the bulk upload participant
                    bulk_participant = self.project_service.create_participant_with_details(
                        bulk_participant_code, 
                        "Bulk", 
                        "Upload", 
                        "", 
                        "Automatically created participant for bulk uploads"
                    )
                participant_id = bulk_participant['participant_id']
                participant_code = bulk_participant['participant_code']
            except DatabaseError as e:
                logger.error(f"Error handling bulk upload participant: {e}")
                return jsonify({'error': f'Failed to create bulk upload participant: {str(e)}'}), 500

            # Group files by project directories using service layer
            project_groups = self.project_service.group_files_by_project_directories(uploaded_files)

            if not project_groups:
                return jsonify({'error': 'No valid project directories found'}), 400

            # Debug: Log project groups found
            logger.info(f"Found {len(project_groups)} project groups:")
            for project_name, files in project_groups.items():
                logger.info(f"  Project '{project_name}': {len(files)} files")
                for file in files[:3]:  # Log first 3 files per project
                    logger.info(f"    - {file.filename}")

            # Start uploading each project
            upload_results = []
            upload_ids = []
            
            for project_name, project_files in project_groups.items():
                logger.info(f"Uploading project: {project_name} with {len(project_files)} files")
                try:
                    # Create project with uploaded files using the bulk-specific service method
                    project_result = self.project_service.create_project_with_bulk_files(
                        project_name, participant_code, project_files, DATA_DIR
                    )
                    project_id = project_result['project_id']
                    new_project_path = project_result['project_path']

                    # Discover sessions in the uploaded project using service layer
                    sessions = self.project_service.discover_project_sessions(new_project_path)

                    # Generate unique upload ID for progress tracking
                    upload_id = str(uuid.uuid4())
                    upload_ids.append(upload_id)
                    
                    import json
                    for session in sessions:
                        logger.info(f"Processing session: {session['name']}")
                        bouts = self.session_service.load_bouts_from_labels_json(new_project_path, session)
                        for bout in bouts:
                            if 'label' not in bout:
                                bout['label'] = 'smoking'
                        created_sessions = self.session_service.preprocess_and_split_session_on_upload(
                            session_name=session['name'],
                            project_path=new_project_path,
                            project_id=project_id,
                            parent_bouts=bouts
                        )
                    
                    upload_results.append({
                        'project_name': project_name,
                        'project_id': project_id,
                        'upload_id': upload_id,
                        'sessions_found': len(sessions),
                        'files_uploaded': project_result['files_processed'],
                        'status': 'success'
                    })
                    
                except Exception as e:
                    logger.error(f"Error uploading project {project_name}: {e}")
                    upload_results.append({
                        'project_name': project_name,
                        'project_id': None,
                        'upload_id': None,
                        'sessions_found': 0,
                        'files_uploaded': 0,
                        'status': 'error',
                        'error': str(e)
                    })
                        
            return jsonify({
                'message': 'Bulk upload started',
                'participant_id': participant_id,
                'participant_code': participant_code,
                'projects_processed': len(project_groups),
                'upload_results': upload_results,
                'upload_ids': upload_ids
            })
            
        except Exception as e:
            logger.error(f"Error in bulk_upload_projects: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': f'Bulk upload failed: {str(e)}'}), 500

@projects_bp.route('/api/projects')
def list_projects():
    return controller.list_projects()

@projects_bp.route('/api/project/upload', methods=['POST'])
def upload_new_project():
    return controller.upload_new_project()

@projects_bp.route('/api/project/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    return controller.delete_project(project_id)

@projects_bp.route('/api/project/<int:project_id>/rename', methods=['PUT'])
def rename_project(project_id):
    return controller.rename_project(project_id)

@projects_bp.route('/api/participants')
def list_participants():
    return controller.list_participants()

@projects_bp.route('/api/participants', methods=['POST'])
def create_participant():
    return controller.create_participant()

@projects_bp.route('/api/participants/<int:participant_id>', methods=['PUT'])
def update_participant(participant_id):
    return controller.update_participant(participant_id)

@projects_bp.route('/api/participants/<int:participant_id>', methods=['DELETE'])
def delete_participant(participant_id):
    return controller.delete_participant(participant_id)

@projects_bp.route('/api/project/<int:project_id>/participant', methods=['PUT'])
def update_project_participant(project_id):
    return controller.update_project_participant(project_id)

@projects_bp.route('/api/projects/bulk-upload', methods=['POST'])
def bulk_upload_projects():
    return controller.bulk_upload_projects()

controller = None

def init_controller(session_service, project_service):
    global controller
    controller = ProjectController(session_service=session_service, project_service=project_service)