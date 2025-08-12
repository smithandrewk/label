from flask import Blueprint, request, jsonify
import os
import uuid
import shutil
import json
from datetime import datetime
from app.exceptions import DatabaseError
from app.logging_config import get_logger
import traceback
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

            all_labels = []

            for session in sessions:
                logger.info(f"Processing session: {session['name']}")
                bouts = self.session_service.load_bouts_from_labels_json(new_project_path, session)
                
                # Ensure bouts is always a list to prevent iteration errors
                if not isinstance(bouts, list):
                    logger.warning(f"Bouts for session {session['name']} is not a list: {type(bouts)}, using empty list")
                    bouts = []
                
                for bout in bouts:
                    if 'label' not in bout:
                        bout['label'] = 'SELF REPORTED SMOKING'

                    if bout['label'] not in all_labels:
                        all_labels.append(bout['label'])

                created_sessions = self.session_service.preprocess_and_split_session_on_upload(
                    session_name=session['name'],
                    project_path=new_project_path,
                    project_id=project_id,
                    parent_bouts=bouts
                )

            # Log all labels
            logger.info(f"All labels found in project {project_name}: {all_labels}")

            # Add labels to project metadata
            self.project_service.add_list_of_labeling_names_to_project(project_id, all_labels)
            
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
            bulkUploadFolderPath = request.form.get('bulkUploadFolderPath')
            logger.info(f"Received bulk upload request for folder: {bulkUploadFolderPath}")
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

            # Start uploading each project
            upload_results = []
            upload_ids = []
            
            projects = os.listdir(bulkUploadFolderPath)
            logger.info(f"Found {len(projects)} projects to upload in {bulkUploadFolderPath}")
            for project_name in projects:
                logger.info(f"Uploading project: {project_name}")
                try:
                    project_result = self.project_service.create_project_with_bulk_files(
                        project_name=project_name,
                        participant_code=participant_code,
                        bulkUploadFolderPath=bulkUploadFolderPath,
                        data_dir=DATA_DIR
                    )
                    project_id = project_result['project_id']
                    new_project_path = project_result['project_path']

                    # Discover sessions in the uploaded project using service layer
                    sessions = self.project_service.discover_project_sessions(new_project_path)

                    # Generate unique upload ID for progress tracking
                    upload_id = str(uuid.uuid4())
                    upload_ids.append(upload_id)
                    
                    all_labels = []

                    for session in sessions:
                        logger.info(f"Processing session: {session['name']}")
                        bouts = self.session_service.load_bouts_from_labels_json(new_project_path, session)

                        for bout in bouts:
                            if 'label' not in bout:
                                bout['label'] = 'SELF REPORTED SMOKING'

                            if bout['label'] not in all_labels:
                                all_labels.append(bout['label'])

                        created_sessions = self.session_service.preprocess_and_split_session_on_upload(
                            session_name=session['name'],
                            project_path=new_project_path,
                            project_id=project_id,
                            parent_bouts=bouts
                        )
                    # Log all labels
                    logger.info(f"All labels found in project {project_name}: {all_labels}")

                    # Add labels to project metadata
                    self.project_service.add_list_of_labeling_names_to_project(project_id, all_labels)
                    
                    upload_results.append({
                        'project_name': project_name,
                        'project_id': project_id,
                        'upload_id': upload_id,
                        'sessions_found': len(sessions),
                        'status': 'success'
                    })
                    
                except Exception as e:
                    logger.error(f"Error uploading project {project_name}: {e}")
                    upload_results.append({
                        'project_name': project_name,
                        'project_id': None,
                        'upload_id': None,
                        'sessions_found': 0,
                        'status': 'error',
                        'error': str(e)
                    })
                        
            return jsonify({
                'message': 'Bulk upload started',
                'participant_id': participant_id,
                'participant_code': participant_code,
                'upload_results': upload_results,
                'upload_ids': upload_ids
            })
            
        except Exception as e:
            logger.error(f"Error in bulk_upload_projects: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': f'Bulk upload failed: {str(e)}'}), 500

    def create_dataset_based_project(self):
        """Create a new project that references raw datasets instead of copying files"""
        try:
            data = request.get_json()
            project_name = data.get('name')
            participant_code = data.get('participant')
            dataset_ids = data.get('dataset_ids', [])
            split_configs = data.get('split_configs', {})
            description = data.get('description', '')
            
            if not all([project_name, participant_code]):
                return jsonify({'error': 'Missing required fields: name or participant'}), 400
            
            if not dataset_ids:
                return jsonify({'error': 'At least one dataset must be selected'}), 400
            
            # Validate dataset IDs are integers
            try:
                dataset_ids = [int(id) for id in dataset_ids]
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid dataset IDs provided'}), 400
            
            result = self.project_service.create_dataset_based_project(
                project_name=project_name,
                participant_code=participant_code,
                dataset_ids=dataset_ids,
                split_configs=split_configs,
                description=description
            )
            
            logger.info(f"Dataset-based project creation result: {result}")
            
            return jsonify({
                'message': 'Dataset-based project created successfully',
                'project_id': result['project_id'],
                'participant_id': result['participant_id'],
                'project_name': result['project_name'],
                'dataset_count': result['dataset_count'],
                'project_type': result['project_type']
            })
            
        except Exception as e:
            logger.error(f"Error in create_dataset_based_project: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': f'Dataset-based project creation failed: {str(e)}'}), 500

    def export_project_configuration(self, project_id):
        """Export project configuration including dataset references and analysis settings"""
        try:
            # Get project details including type and analysis config
            project = self.project_service.get_project_with_participant(project_id)
            if not project:
                return jsonify({'error': 'Project not found'}), 404
            
            # Get linked datasets if this is a dataset-based project
            from app.services.raw_dataset_service import RawDatasetService
            raw_dataset_service = RawDatasetService()
            linked_datasets = raw_dataset_service.get_project_datasets(project_id)
            
            # Get project labelings
            labelings_data = []
            try:
                labelings_result = self.project_service.get_labelings(project_id)
                if labelings_result and len(labelings_result) > 0:
                    labelings_data = json.loads(labelings_result[0]['labelings']) if labelings_result[0]['labelings'] else []
            except Exception as e:
                logger.warning(f"Could not load labelings for project {project_id}: {e}")
                labelings_data = []
            
            # Get sessions with their bouts for this project
            try:
                all_sessions = self.session_service.get_all_sessions_with_details()
                project_sessions = [s for s in all_sessions if s['project_id'] == project_id]
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500
            
            # Process sessions and their bouts
            processed_sessions = []
            for session in project_sessions:
                session_data = {
                    'session_id': session['session_id'],
                    'session_name': session['session_name'],
                    'status': session['status'],
                    'verified': bool(session['verified']),
                    'start_ns': session.get('start_ns'),
                    'stop_ns': session.get('stop_ns'),
                    'dataset_id': session.get('dataset_id'),
                    'raw_session_name': session.get('raw_session_name'),
                    'virtual_split_info': {
                        'parent_data_path': session.get('parent_session_data_path'),
                        'data_start_offset': session.get('data_start_offset'),
                        'data_end_offset': session.get('data_end_offset'),
                        'is_virtual_split': bool(session.get('parent_session_data_path'))
                    }
                }
                
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
                        logger.warning(f"Error parsing bouts for session {session['session_id']}: {e}")
                        bouts = []
                
                session_data['bouts'] = bouts
                processed_sessions.append(session_data)
            
            # Create export data structure
            export_data = {
                'export_version': '2.0',  # Version 2.0 supports dataset-based projects
                'export_timestamp': datetime.now().isoformat(),
                'export_type': 'project_configuration',
                'project': {
                    'project_id': project['project_id'],
                    'project_name': project['project_name'],
                    'project_type': project.get('project_type', 'legacy'),
                    'analysis_config': json.loads(project.get('analysis_config', '{}')) if project.get('analysis_config') else {},
                    'participant': {
                        'participant_id': project['participant_id'],
                        'participant_code': project['participant_code']
                    }
                },
                'datasets': [{
                    'dataset_id': ds['dataset_id'],
                    'dataset_name': ds['dataset_name'],
                    'dataset_hash': ds['dataset_hash'],
                    'session_count': ds['session_count'],
                    'description': ds.get('description'),
                    'metadata': ds.get('metadata', {})
                } for ds in linked_datasets],
                'labelings': labelings_data,
                'sessions': processed_sessions,
                'session_count': len(processed_sessions),
                'total_bouts': sum(len(s.get('bouts', [])) for s in processed_sessions)
            }
            
            return jsonify(export_data)
            
        except Exception as e:
            logger.error(f"Error exporting project configuration: {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500

    def import_project_configuration(self):
        """Import a project configuration, creating project and linking to datasets"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Validate export format
            if data.get('export_type') != 'project_configuration':
                return jsonify({'error': 'Invalid export type. Expected project_configuration.'}), 400
            
            export_version = data.get('export_version', '1.0')
            if export_version not in ['1.0', '2.0']:
                return jsonify({'error': f'Unsupported export version: {export_version}'}), 400
            
            project_data = data.get('project', {})
            datasets_data = data.get('datasets', [])
            labelings_data = data.get('labelings', [])
            
            if not project_data.get('project_name'):
                return jsonify({'error': 'Missing project name in import data'}), 400
            
            # Check if this is a dataset-based project import
            if export_version == '2.0' and datasets_data:
                # For dataset-based projects, validate that referenced datasets exist
                from app.services.raw_dataset_service import RawDatasetService
                raw_dataset_service = RawDatasetService()
                
                missing_datasets = []
                available_dataset_ids = []
                
                for dataset_ref in datasets_data:
                    dataset_hash = dataset_ref.get('dataset_hash')
                    if dataset_hash:
                        existing_dataset = raw_dataset_service.raw_dataset_repo.find_by_hash(dataset_hash)
                        if existing_dataset:
                            available_dataset_ids.append(existing_dataset['dataset_id'])
                        else:
                            missing_datasets.append({
                                'name': dataset_ref.get('dataset_name'),
                                'hash': dataset_hash
                            })
                
                if missing_datasets:
                    return jsonify({
                        'error': 'Referenced datasets not found',
                        'missing_datasets': missing_datasets,
                        'suggestion': 'Upload the missing datasets first, then retry the import'
                    }), 400
                
                # Create dataset-based project
                new_project_name = f"{project_data['project_name']}_imported_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                result = self.project_service.create_dataset_based_project(
                    project_name=new_project_name,
                    participant_code=project_data.get('participant', {}).get('participant_code', 'IMPORTED'),
                    dataset_ids=available_dataset_ids,
                    split_configs=project_data.get('analysis_config', {}).get('split_configs', {}),
                    description=f"Imported from {project_data['project_name']} on {datetime.now().isoformat()}"
                )
                
                project_id = result['project_id']
                
                # Import labelings if present
                if labelings_data:
                    for labeling in labelings_data:
                        try:
                            self.project_service.update_labelings(project_id, labeling)
                        except Exception as e:
                            logger.warning(f"Could not import labeling {labeling.get('name')}: {e}")
                
                return jsonify({
                    'message': 'Project configuration imported successfully',
                    'project_id': project_id,
                    'project_name': new_project_name,
                    'imported_datasets': len(available_dataset_ids),
                    'imported_labelings': len(labelings_data),
                    'note': 'Virtual sessions will be recreated when you start analysis'
                })
                
            else:
                return jsonify({
                    'error': 'Legacy project import not supported in this version',
                    'suggestion': 'Use the original project upload workflow for legacy projects'
                }), 400
                
        except Exception as e:
            logger.error(f"Error importing project configuration: {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500

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

@projects_bp.route('/api/projects/create-from-datasets', methods=['POST'])
def create_dataset_based_project():
    return controller.create_dataset_based_project()

@projects_bp.route('/api/projects/<int:project_id>/export-config')
def export_project_configuration(project_id):
    return controller.export_project_configuration(project_id)

@projects_bp.route('/api/projects/import-config', methods=['POST'])
def import_project_configuration():
    return controller.import_project_configuration()

controller = None

def init_controller(session_service, project_service):
    global controller
    controller = ProjectController(session_service=session_service, project_service=project_service)