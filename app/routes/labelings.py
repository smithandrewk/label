from flask import Blueprint, request, jsonify
from app.exceptions import DatabaseError
import os
import pandas as pd
import json
import shutil
import logging
import traceback

labelings_bp = Blueprint('labels', __name__)

class LabelController:
    def __init__(self, project_service, session_service, model_service):
        self.project_service = project_service
        self.session_service = session_service
        self.model_service = model_service
        
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

controller = None

def init_controller(project_service, session_service, model_service):
    global controller
    controller = LabelController(project_service, session_service, model_service)

@labelings_bp.route('/api/labelings/<int:project_id>')
def get_labelings(project_id):
    return controller.get_labelings(project_id)

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
            color = data.get('color', '#FF6B6B')  # Default color if none provided
            
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