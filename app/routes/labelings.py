"""
Labelings API routes for the application.

This module defines the API endpoints for managing labeling sets.
"""

from flask import Blueprint, jsonify, request, current_app
from app.services.labeling_service import Labeling, LabelingValidationError, LabelingService
from app.exceptions import DatabaseError
import json

# Create a Blueprint for the labelings API
labelings_bp = Blueprint('labelings', __name__)


class LabelingController:
    """Controller class for labeling operations."""
    
    def __init__(self, labeling_service: LabelingService):
        self.labeling_service = labeling_service
    
    def get_all_labelings(self):
        """Get all labelings available to the user."""
        try:
            visible_only = request.args.get('visible_only', 'true').lower() == 'true'
            
            try:
                labelings = self.labeling_service.get_all_labelings(visible_only=visible_only)
                return success_response(
                    data=labelings,
                    message=f"Retrieved {len(labelings)} labelings"
                )
            except DatabaseError as e:
                return error_response(str(e), 500, "DATABASE_ERROR")
                
        except Exception as e:
            return error_response(f"Failed to get labelings: {str(e)}", 500)
    
    def get_labeling(self, labeling_id):
        """Get a specific labeling by ID."""
        try:
            try:
                labeling = self.labeling_service.get_labeling_by_id(labeling_id)
                if not labeling:
                    return error_response("Labeling not found", 404, "NOT_FOUND")
                
                return success_response(
                    data=labeling,
                    message=f"Retrieved labeling: {labeling['name']}"
                )
            except DatabaseError as e:
                return error_response(str(e), 500, "DATABASE_ERROR")
                
        except Exception as e:
            return error_response(f"Failed to get labeling: {str(e)}", 500)
    
    def get_project_labelings(self, project_id):
        """Get all labelings for a specific project."""
        try:
            visible_only = request.args.get('visible_only', 'true').lower() == 'true'
            
            try:
                labelings = self.labeling_service.get_labelings_for_project(
                    project_id=project_id, 
                    visible_only=visible_only
                )
                return success_response(
                    data=labelings,
                    message=f"Retrieved {len(labelings)} labelings for project {project_id}"
                )
            except DatabaseError as e:
                return error_response(str(e), 500, "DATABASE_ERROR")
                
        except Exception as e:
            return error_response(f"Failed to get project labelings: {str(e)}", 500)
    
    def get_session_labelings(self, session_id):
        """Get all labelings for a specific session."""
        try:
            visible_only = request.args.get('visible_only', 'true').lower() == 'true'
            
            try:
                labelings = self.labeling_service.get_labelings_for_session(
                    session_id=session_id, 
                    visible_only=visible_only
                )
                return success_response(
                    data=labelings,
                    message=f"Retrieved {len(labelings)} labelings for session {session_id}"
                )
            except DatabaseError as e:
                return error_response(str(e), 500, "DATABASE_ERROR")
                
        except Exception as e:
            return error_response(f"Failed to get session labelings: {str(e)}", 500)


# Global controller instance
controller = None


def init_controller(labeling_service):
    """Initialize the controller with dependencies."""
    global controller
    controller = LabelingController(labeling_service)

# Standard API response format utilities
def success_response(data=None, message="Success", status_code=200):
    """Create a standardized success response"""
    response = {
        "success": True,
        "message": message
    }
    if data is not None:
        response["data"] = data
    return jsonify(response), status_code

def error_response(message="An error occurred", status_code=400, error_code=None):
    """Create a standardized error response"""
    response = {
        "success": False,
        "error": message
    }
    if error_code:
        response["error_code"] = error_code
    return jsonify(response), status_code

def validation_error_response(message, field=None):
    """Create a standardized validation error response"""
    response = {
        "success": False,
        "error": message,
        "error_code": "VALIDATION_ERROR"
    }
    if field:
        response["field"] = field
    return jsonify(response), 400

# ----- Endpoints for global labelings -----

# ----- Endpoints for global labelings -----

@labelings_bp.route('/api/labelings', methods=['GET'])
def get_all_labelings():
    """Get all labelings available to the user."""
    return controller.get_all_labelings()

@labelings_bp.route('/api/labelings', methods=['POST'])
def create_labeling():
    """Create a new labeling."""
    # TODO: Implement in a future commit
    return success_response(
        data={"id": "temp_id", "name": "Temporary Labeling"},
        message="Create labeling endpoint (to be implemented)",
        status_code=201
    )

@labelings_bp.route('/api/labelings/<labeling_id>', methods=['GET'])
def get_labeling(labeling_id):
    """Get a specific labeling by ID."""
    return controller.get_labeling(labeling_id)

@labelings_bp.route('/api/labelings/<labeling_id>', methods=['PUT'])
def update_labeling(labeling_id):
    """Update a specific labeling by ID."""
    # TODO: Implement in a future commit
    return success_response(
        data={"id": labeling_id, "updated": True},
        message=f"Update labeling endpoint for ID: {labeling_id} (to be implemented)"
    )

@labelings_bp.route('/api/labelings/<labeling_id>', methods=['DELETE'])
def delete_labeling(labeling_id):
    """Delete a specific labeling by ID."""
    # TODO: Implement in a future commit
    return success_response(
        data={"id": labeling_id, "deleted": True},
        message=f"Delete labeling endpoint for ID: {labeling_id} (to be implemented)"
    )

# ----- Endpoints for project-specific labelings -----

@labelings_bp.route('/api/projects/<int:project_id>/labelings', methods=['GET'])
def get_project_labelings(project_id):
    """Get all labelings for a specific project."""
    return controller.get_project_labelings(project_id)

@labelings_bp.route('/api/projects/<int:project_id>/labelings', methods=['POST'])
def create_project_labeling(project_id):
    """Create a new labeling for a specific project."""
    # TODO: Implement in a future commit
    return success_response(
        data={"id": "temp_id", "project_id": project_id, "name": "Temporary Project Labeling"},
        message=f"Create labeling for project ID: {project_id} (to be implemented)",
        status_code=201
    )

# ----- Endpoints for session-specific labelings -----

@labelings_bp.route('/api/sessions/<int:session_id>/labelings', methods=['GET'])
def get_session_labelings(session_id):
    """Get all labelings for a specific session."""
    return controller.get_session_labelings(session_id)

@labelings_bp.route('/api/sessions/<int:session_id>/labelings', methods=['POST'])
def create_session_labeling(session_id):
    """Create a new labeling for a specific session."""
    # TODO: Implement in a future commit
    return success_response(
        data={"id": "temp_id", "session_id": session_id, "name": "Temporary Session Labeling"},
        message=f"Create labeling for session ID: {session_id} (to be implemented)",
        status_code=201
    )

# ----- Utility endpoints -----

@labelings_bp.route('/api/labelings/<labeling_id>/toggle', methods=['POST'])
def toggle_labeling_visibility(labeling_id):
    """Toggle the visibility of a labeling."""
    # TODO: Implement in a future commit
    return success_response(
        data={"id": labeling_id, "visible": True},
        message=f"Toggle visibility for labeling ID: {labeling_id} (to be implemented)"
    )

@labelings_bp.route('/api/labelings/<labeling_id>/duplicate', methods=['POST'])
def duplicate_labeling(labeling_id):
    """Create a duplicate of an existing labeling."""
    # TODO: Implement in a future commit
    return success_response(
        data={"original_id": labeling_id, "new_id": "new_temp_id", "name": "Copy of Temporary Labeling"},
        message=f"Duplicate labeling ID: {labeling_id} (to be implemented)",
        status_code=201
    )
