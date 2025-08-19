from flask import Blueprint, request, jsonify, session
from app.exceptions import DatabaseError
import os
import pandas as pd
import json
import shutil
import logging
import traceback
import random
from datetime import datetime
from app.services.project_service import ProjectService
from app.services.session_service import SessionService
from app.services.model_service import ModelService

labelings_bp = Blueprint('labels', __name__)

class LabelController:
    def __init__(self, project_service, session_service, model_service):
        self.project_service: ProjectService = project_service
        self.session_service: SessionService = session_service
        self.model_service: ModelService = model_service

    def get_labelings(self, project_id):
        try:
            labelings = self.project_service.get_labelings(project_id)
            return jsonify(labelings), 200
        except DatabaseError as e:
            logging.error(f"Database error: {e}")
            return jsonify({"error": "Database error occurred"}), 500
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            traceback.print_exc()
            return jsonify({"error": "An unexpected error occurred"}), 500
            
    def get_all_labelings(self, project_id):
        try:
            labelings = self.project_service.get_all_labelings(project_id, include_deleted=True)
            return jsonify(labelings), 200
        except DatabaseError as e:
            logging.error(f"Database error: {e}")
            return jsonify({"error": "Database error occurred"}), 500
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            traceback.print_exc()
            return jsonify({"error": "An unexpected error occurred"}), 500
        
    def rename_labeling(self, project_id):
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid input: No data provided"}), 400
            
            old_name = data.get('old_name', '').strip()
            new_name = data.get('new_name', '').strip()
            
            if not old_name:
                return jsonify({"error": "Old labeling name cannot be empty"}), 400
                
            if not new_name:
                return jsonify({"error": "New labeling name cannot be empty"}), 400
                
            if old_name == new_name:
                return jsonify({"error": "New name must be different from the old name"}), 400
            
            # Rename the labeling in the database
            result = self.project_service.rename_labeling(project_id, old_name, new_name)
            
            # Also update all session bouts that use this labeling name
            self.session_service.update_session_bouts_labeling_name(project_id, old_name, new_name)
            
            return jsonify({
                "status": "success",
                "message": f"Labeling renamed from '{old_name}' to '{new_name}' successfully",
                "old_name": old_name,
                "new_name": new_name
            }), 200
            
        except DatabaseError as e:
            logging.error(f"Database error: {str(e)}")
            return jsonify({"error": f"Database error: {str(e)}"}), 500
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            traceback.print_exc()
            return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    def duplicate_labeling(self, project_id):
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid input: No data provided"}), 400
            
            original_name = data.get('original_name', '').strip()
            new_name = data.get('new_name', '').strip()
            
            if not original_name:
                return jsonify({"error": "Original labeling name cannot be empty"}), 400
                
            if not new_name:
                return jsonify({"error": "New labeling name cannot be empty"}), 400
                
            if original_name == new_name:
                return jsonify({"error": "New name must be different from the original name"}), 400
            
            # Check if the new name already exists
            existing_labelings = json.loads(self.project_service.get_labelings(project_id)[0]['labelings'])

            if any(labeling.get('name') == new_name for labeling in existing_labelings):
                return jsonify({"error": f"A labeling with the name '{new_name}' already exists"}), 400

            # Get the original labeling to copy its color
            original_labeling = next((l for l in existing_labelings if l.get('name') == original_name), None)
            if not original_labeling:
                return jsonify({"error": f"Original labeling '{original_name}' not found"}), 404
            
            # Generate a new random color for the duplicate
            pretty_colors = [
                '#FF6B6B',  # Coral Red
                '#4ECDC4',  # Turquoise
                '#45B7D1',  # Sky Blue
                '#96CEB4',  # Mint Green
                '#FFEAA7',  # Warm Yellow
                '#DDA0DD',  # Plum
                '#98D8C8',  # Seafoam
                '#F7DC6F',  # Light Gold
                '#BB8FCE',  # Lavender
                '#85C1E9',  # Light Blue
                '#F8C471',  # Peach
                '#82E0AA',  # Light Green
                '#F1948A',  # Salmon
                '#85C1E9',  # Powder Blue
                '#D7BDE2'   # Light Purple
            ]
            new_color = random.choice(pretty_colors)
            
            # Create the duplicate labeling
            duplicate_labeling = {
                "name": new_name,
                "color": new_color,
                "is_deleted": False,
            }
            
            # Add the new labeling to the project
            self.project_service.update_labelings(project_id, duplicate_labeling)
            
            # Duplicate all bouts from the original labeling to the new one
            self.session_service.duplicate_session_bouts_for_labeling(project_id, original_name, new_name)
            
            return jsonify({
                "status": "success",
                "message": f"Labeling '{original_name}' duplicated as '{new_name}' successfully",
                "original_name": original_name,
                "new_name": new_name,
                "new_color": new_color
            }), 200
            
        except DatabaseError as e:
            logging.error(f"Database error: {str(e)}")
            return jsonify({"error": f"Database error: {str(e)}"}), 500
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            traceback.print_exc()
            return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    def delete_labeling(self, project_id):
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid input: No data provided"}), 400
            
            labeling_name = data.get('name', '').strip()
            
            if not labeling_name:
                return jsonify({"error": "Labeling name cannot be empty"}), 400
            
            # Check if the labeling exists and is not already deleted
            existing_labelings = json.loads(self.project_service.get_labelings(project_id)[0]['labelings'])
            
            labeling_to_delete = next((l for l in existing_labelings if l.get('name') == labeling_name), None)
            if not labeling_to_delete:
                return jsonify({"error": f"Labeling '{labeling_name}' not found"}), 404
                
            if labeling_to_delete.get('is_deleted', False):
                return jsonify({"error": f"Labeling '{labeling_name}' is already deleted"}), 400
            
            # Mark the labeling as deleted
            result = self.project_service.delete_labeling(project_id, labeling_name)
            
            return jsonify({
                "status": "success",
                "message": f"Labeling '{labeling_name}' deleted successfully",
                "labeling_name": labeling_name
            }), 200
            
        except DatabaseError as e:
            logging.error(f"Database error: {str(e)}")
            return jsonify({"error": f"Database error: {str(e)}"}), 500
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            traceback.print_exc()
            return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    def permanently_delete_labeling(self, project_id):
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid input: No data provided"}), 400
            
            labeling_name = data.get('name', '').strip()
            
            if not labeling_name:
                return jsonify({"error": "Labeling name cannot be empty"}), 400
            
            # Permanently delete the labeling and associated bouts
            result = self.project_service.permanently_delete_labeling(project_id, labeling_name)
            
            # Create detailed message including bout removal info
            message = f"Labeling '{labeling_name}' permanently deleted successfully"
            if 'bouts_removed' in result and result['bouts_removed'] > 0:
                message += f" (removed {result['bouts_removed']} bouts from {result['sessions_updated']} sessions)"
            
            response_data = {
                "status": "success",
                "message": message,
                "labeling_name": labeling_name
            }
            
            # Include bout removal statistics in response
            if 'bouts_removed' in result:
                response_data['bouts_removed'] = result['bouts_removed']
                response_data['sessions_updated'] = result['sessions_updated']
            
            if 'bout_removal_error' in result:
                response_data['bout_removal_error'] = result['bout_removal_error']
            
            return jsonify(response_data), 200
            
        except DatabaseError as e:
            logging.error(f"Database error: {str(e)}")
            return jsonify({"error": f"Database error: {str(e)}"}), 500
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            traceback.print_exc()
            return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    def export_labeling(self, project_id, labeling_name):
        """Export all labels for a specific labeling in a project"""
        try:
            # Get project details
            try:
                project = self.project_service.get_project_with_participant(project_id)
                if not project:
                    return jsonify({'error': 'Project not found'}), 404
                    
                all_sessions = self.session_service.get_all_sessions_with_details()
                # Filter sessions for the specific project
                sessions = [s for s in all_sessions if s['project_id'] == project_id]
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500
            
            # Process the data for export - filter by labeling name
            session_list = []
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
                
                # Filter bouts by labeling name and process them
                filtered_bouts = []
                if isinstance(bouts, list) and len(bouts) > 0:
                    for i, bout in enumerate(bouts):
                        bout_label = None
                        if isinstance(bout, list) and len(bout) > 2:
                            bout_label = bout[2]
                        elif isinstance(bout, dict):
                            bout_label = bout.get('label', 'smoking')
                        
                        # Only include bouts that match the specified labeling
                        if bout_label == labeling_name:
                            if isinstance(bout, list) and len(bout) >= 2:
                                processed_bout = {
                                    'bout_index': len(filtered_bouts),
                                    'start_time': bout[0] if len(bout) > 0 else None,
                                    'end_time': bout[1] if len(bout) > 1 else None,
                                    'duration_ns': bout[1] - bout[0] if len(bout) >= 2 else None,
                                    'duration_seconds': (bout[1] - bout[0]) / 1e9 if len(bout) >= 2 else None,
                                    'label': bout[2] if len(bout) > 2 else 'smoking',
                                    'confidence': bout[3] if len(bout) > 3 else None
                                }
                                filtered_bouts.append(processed_bout)
                                total_labels_count += 1
                            elif isinstance(bout, dict):
                                processed_bout = {
                                    'bout_index': len(filtered_bouts),
                                    'start_time': bout.get('start'),
                                    'end_time': bout.get('end'),
                                    'duration_ns': bout.get('end') - bout.get('start') if bout.get('start') and bout.get('end') else None,
                                    'duration_seconds': (bout.get('end') - bout.get('start')) / 1e9 if bout.get('start') and bout.get('end') else None, 
                                    'label': bout.get('label','smoking'),
                                    'confidence': bout.get('confidence')
                                }
                                filtered_bouts.append(processed_bout)
                                total_labels_count += 1

                # Only include sessions that have bouts for this labeling
                if len(filtered_bouts) > 0:
                    # Get root session info for proper export naming
                    root_info = self.session_service.get_root_session_info(session['session_id'])
                    root_session_name = root_info['root_session_name'] if root_info else session['session_name']
                    
                    session_obj = {
                        'session_id': session['session_id'],
                        'session_name': root_session_name,  # Use root session name for export
                        'original_session_name': session['session_name'],  # Keep original for reference
                        'status': session['status'],
                        'verified': bool(session['verified']),
                        'bout_count': len(filtered_bouts),
                        'bouts': filtered_bouts,
                        'is_virtual_split': root_info['is_virtual_split'] if root_info else False
                    }
                    session_list.append(session_obj)
            
            return jsonify({
                'success': True,
                'project_id': project['project_id'],
                'project_name': project['project_name'],
                'labeling_name': labeling_name,
                'participant': {
                    'participant_id': project['participant_id'],
                    'participant_code': project['participant_code']
                },
                'total_sessions': len(session_list),
                'total_bouts': total_labels_count,
                'export_timestamp': datetime.now().isoformat(),
                'sessions': session_list
            })
            
        except Exception as e:
            logging.error(f"Error in export_labeling: {str(e)}")
            logging.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500

    def import_labeling(self, project_id):
        """Import labeling data from JSON export format"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Validate required fields
            if not data.get('labeling_name') or not data.get('sessions'):
                return jsonify({'error': 'Invalid import format: missing labeling_name or sessions'}), 400
                
            labeling_name = data['labeling_name'].strip()
            imported_sessions = data['sessions']
            
            if not labeling_name:
                return jsonify({'error': 'Labeling name cannot be empty'}), 400
                
            if not isinstance(imported_sessions, list):
                return jsonify({'error': 'Sessions must be an array'}), 400
            
            # Get current project sessions to match against
            try:
                all_sessions = self.session_service.get_all_sessions_with_details()
                project_sessions = [s for s in all_sessions if s['project_id'] == project_id]
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500
            
            # Check if labeling already exists, if not create it
            existing_labelings = self.project_service.get_labelings(project_id)
            labeling_exists = False
            if existing_labelings and len(existing_labelings) > 0:
                labelings_data = json.loads(existing_labelings[0]['labelings'])
                labeling_exists = any(l.get('name') == labeling_name for l in labelings_data)
            
            if not labeling_exists:
                # Create new labeling
                # Generate a color for the new labeling
                pretty_colors = [
                    '#FF6B6B',  # Coral Red
                    '#4ECDC4',  # Turquoise
                    '#45B7D1',  # Sky Blue
                    '#96CEB4',  # Mint Green
                    '#FFEAA7',  # Warm Yellow
                    '#DDA0DD',  # Plum
                    '#98D8C8',  # Seafoam
                    '#F7DC6F',  # Light Gold
                    '#BB8FCE',  # Lavender
                    '#85C1E9',  # Light Blue
                    '#F8C471',  # Peach
                    '#82E0AA',  # Light Green
                ]
                
                color = data.get('color', random.choice(pretty_colors))
                labeling = {
                    "name": labeling_name,
                    "color": color,
                    "is_deleted": False
                }
                
                self.project_service.update_labelings(project_id, labeling)
            
            # Process session matching and bout importing with virtual split support
            sessions_processed = 0
            bouts_imported = 0
            
            # Group existing sessions by root session name and direct session name (for legacy compatibility)
            sessions_by_root = {}
            sessions_by_direct_name = {}
            for existing_session in project_sessions:
                # Modern virtual split handling
                root_info = self.session_service.get_root_session_info(existing_session['session_id'])
                root_session_name = root_info['root_session_name'] if root_info else existing_session['session_name']
                
                if root_session_name not in sessions_by_root:
                    sessions_by_root[root_session_name] = []
                sessions_by_root[root_session_name].append(existing_session)
                
                # Legacy direct name mapping (for backward compatibility with legacy exports)
                direct_session_name = existing_session['session_name']
                if direct_session_name not in sessions_by_direct_name:
                    sessions_by_direct_name[direct_session_name] = []
                sessions_by_direct_name[direct_session_name].append(existing_session)
            
            # Process each imported session
            for imported_session in imported_sessions:
                imported_session_name = imported_session['session_name']
                imported_bouts = imported_session.get('bouts', [])
                
                # Find matching existing sessions - try root name first (modern), then direct name (legacy)
                matching_sessions = sessions_by_root.get(imported_session_name, [])
                if not matching_sessions:
                    # Fallback to direct session name matching for legacy exports
                    matching_sessions = sessions_by_direct_name.get(imported_session_name, [])
                
                for existing_session in matching_sessions:
                    current_bouts = []
                    try:
                        if isinstance(existing_session['bouts'], str):
                            current_bouts = json.loads(existing_session['bouts'])
                        elif isinstance(existing_session['bouts'], list):
                            current_bouts = existing_session['bouts']
                    except (json.JSONDecodeError, TypeError):
                        current_bouts = []

                    session_updated = False
                    for bout in imported_bouts:
                        bout_start_ns = bout.get('start_time')
                        bout_end_ns = bout.get('end_time')

                        # Check if bout start and end times are within the session bounds
                        # Allow bout end time to equal session stop_ns (inclusive right boundary)
                        if (bout_start_ns is not None and bout_end_ns is not None and
                            existing_session['start_ns'] <= bout_start_ns <= existing_session['stop_ns'] and
                            existing_session['start_ns'] <= bout_end_ns <= existing_session['stop_ns']):
                            
                            new_bout = {
                                "start": bout.get('start_time'),
                                "end": bout.get('end_time'),
                                "label": labeling_name,
                                "confidence": bout.get('confidence')
                            }

                            current_bouts.append(new_bout)
                            bouts_imported += 1
                            session_updated = True
                    
                    # Only update session if bouts were added
                    if session_updated:
                        merged_bouts_json = json.dumps(current_bouts)
                        self.session_service.update_session(
                            existing_session['session_id'],
                            existing_session['status'],
                            existing_session['keep'],
                            merged_bouts_json,
                            existing_session['verified']
                        )
                        sessions_processed += 1

            return jsonify({
                'success': True,
                'message': f'Successfully imported labeling "{labeling_name}"',
                'labeling_name': labeling_name,
                'sessions_processed': sessions_processed,
                'bouts_imported': bouts_imported,
                'labeling_created': not labeling_exists
            })
            
        except Exception as e:
            logging.error(f"Error in import_labeling: {str(e)}")
            logging.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500

controller = None

def init_controller(project_service, session_service, model_service):
    global controller
    controller = LabelController(project_service, session_service, model_service)

@labelings_bp.route('/api/labelings/<int:project_id>')
def get_labelings(project_id):
    return controller.get_labelings(project_id)

@labelings_bp.route('/api/labelings/<int:project_id>/all')
def get_all_labelings(project_id):
    return controller.get_all_labelings(project_id)

# Update labelings to include the new labeling
@labelings_bp.route('/api/labelings/<int:project_id>/update', methods=['POST'])
def update_labelings(project_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid input: No data provided"}), 400
        
        # Handle both old format (single label string) and new format (structured labeling)
        if 'name' in data:
            # New format: creating a structured labeling with name and labels
            labeling_name = data.get('name', '').strip()
            if not labeling_name:
                return jsonify({"error": "Labeling name cannot be empty"}), 400
            
            # Initialize with empty labels structure if not provided
            labels = data.get('labels', {})
            
            # Pretty color palette for automatic labeling colors
            pretty_colors = [
                '#FF6B6B',  # Coral Red
                '#4ECDC4',  # Turquoise
                '#45B7D1',  # Sky Blue
                '#96CEB4',  # Mint Green
                '#FFEAA7',  # Warm Yellow
                '#DDA0DD',  # Plum
                '#98D8C8',  # Seafoam
                '#F7DC6F',  # Light Gold
                '#BB8FCE',  # Lavender
                '#85C1E9',  # Light Blue
                '#F8C471',  # Peach
                '#82E0AA',  # Light Green
                '#F1948A',  # Salmon
                '#85C1E9',  # Powder Blue
                '#D7BDE2'   # Light Purple
            ]
            
            color = data.get('color', random.choice(pretty_colors))  # Random pretty color if none provided
            
            # Create a labeling object with name and color
            labeling = {
                "name": labeling_name,
                "color": color
            }
            
            # Create new labeling by adding the structured object to the labelings list
            updated_labelings = controller.project_service.update_labelings(project_id, labeling)
            
            return jsonify({
                "status": "success",
                "message": f"Labeling '{labeling_name}' created successfully",
                "labeling_name": labeling_name,
                "color": color,
                "labels": labels
            }), 200
        else:
            return jsonify({"error": "Invalid input: Missing 'name' or 'label' field"}), 400
        
    except DatabaseError as e:
        logging.error(f"Database error: {str(e)}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# Update labeling color
@labelings_bp.route('/api/labelings/<int:project_id>/color', methods=['PUT'])
def update_labeling_color(project_id):
    try:
        data = request.get_json()
        # Logging the request data for debugging
        logging.debug(f"Received data for updating labeling color: {data}")
        print(f"Received data for updating labeling color: {data}")
        if not data:
            return jsonify({"error": "Invalid input: No data provided"}), 400
        
        labeling_name = data.get('name', '').strip()
        color = data.get('color', '')
        
        if not labeling_name:
            return jsonify({"error": "Labeling name cannot be empty"}), 400
        
        if not color:
            return jsonify({"error": "Color cannot be empty"}), 400
        
        # Update the labeling color in the database
        result = controller.project_service.update_labeling_color(project_id, labeling_name, color)
        
        return jsonify({
            "status": "success",
            "message": f"Color for labeling '{labeling_name}' updated successfully",
            "labeling_name": labeling_name,
            "color": color
        }), 200
        
    except DatabaseError as e:
        logging.error(f"Database error: {str(e)}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# Rename labeling
@labelings_bp.route('/api/labelings/<int:project_id>/rename', methods=['PUT'])
def rename_labeling(project_id):
    return controller.rename_labeling(project_id)

# Duplicate labeling
@labelings_bp.route('/api/labelings/<int:project_id>/duplicate', methods=['POST'])
def duplicate_labeling(project_id):
    return controller.duplicate_labeling(project_id)

# Delete labeling
@labelings_bp.route('/api/labelings/<int:project_id>/delete', methods=['DELETE'])
def delete_labeling(project_id):
    return controller.delete_labeling(project_id)

# Permanently delete labeling
@labelings_bp.route('/api/labelings/<int:project_id>/permanent-delete', methods=['DELETE'])
def permanently_delete_labeling(project_id):
    return controller.permanently_delete_labeling(project_id)

# Export labeling
@labelings_bp.route('/api/export/labeling/<int:project_id>/<labeling_name>')
def export_labeling(project_id, labeling_name):
    return controller.export_labeling(project_id, labeling_name)

# Import labeling
@labelings_bp.route('/api/import/labeling/<int:project_id>', methods=['POST'])
def import_labeling(project_id):
    return controller.import_labeling(project_id)