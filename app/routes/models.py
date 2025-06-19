from flask import Blueprint, jsonify

# Create the blueprint
models_bp = Blueprint('models', __name__)

class ModelController:
    def __init__(self, model_service):
        self.model_service = model_service

    def list_models(self):
        try:
            return self.model_service.list_models()
        except Exception as e:
            print(f"Error listing models: {e}")
            return jsonify({'error': str(e)}), 500

    def get_scoring_status(self, scoring_id):
        """Get the status of a scoring operation"""
        try:
            # You'll need to modify ModelService to track scoring status
            status = self.model_service.get_scoring_status(scoring_id)
            return jsonify(status)
        except Exception as e:
            print(f"Error getting scoring status: {e}")
            return jsonify({'error': str(e)}), 500
        
controller = None

def init_controller(model_service):
    global controller
    controller = ModelController(model_service)

@models_bp.route('/api/models')
def list_models():
    return controller.list_models()

@models_bp.route('/api/scoring_status/<scoring_id>')
def get_scoring_status(scoring_id):
    return controller.get_scoring_status(scoring_id)