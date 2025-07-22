from flask import Blueprint, request, jsonify
from app.exceptions import DatabaseError
import logging
import traceback

models_bp = Blueprint('models', __name__)

class ModelController:
    def __init__(self, model_service, session_service):
        self.model_service = model_service
        self.session_service = session_service
        self.session_service = session_service

    def list_models(self):
        """Get all available models"""
        try:
            logging.info("fetching all models")
            models = self.model_service.get_all_models()
            logging.info(f"found {len(models)} models")
            return jsonify(models), 200
        except DatabaseError as e:
            logging.error(f"database error in list_models: {e}")
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            logging.error(f"unexpected error in list_models: {e}")
            traceback.print_exc()
            return jsonify({'error': 'an unexpected error occurred'}), 500

    def create_model(self):
        """Create a new model"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'no data provided'}), 400
            
            # validate required fields
            required_fields = ['name', 'py_filename', 'pt_filename', 'class_name']
            missing_fields = [field for field in required_fields if not data.get(field, '').strip()]
            
            if missing_fields:
                return jsonify({'error': f'missing required fields: {", ".join(missing_fields)}'}), 400
            
            # extract and validate data
            model_data = {
                'name': data.get('name', '').strip(),
                'description': data.get('description', '').strip(),
                'py_filename': data.get('py_filename', '').strip(),
                'pt_filename': data.get('pt_filename', '').strip(),
                'class_name': data.get('class_name', '').strip(),
                'is_active': True
            }
            
            logging.info(f"creating new model: {model_data['name']}")
            created_model = self.model_service.create_model(model_data)
            logging.info(f"model created successfully with id: {created_model.get('id')}")
            
            return jsonify({
                'message': 'model created successfully',
                'model': created_model
            }), 201
            
        except DatabaseError as e:
            logging.error(f"database error in create_model: {e}")
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            logging.error(f"unexpected error in create_model: {e}")
            traceback.print_exc()
            return jsonify({'error': f'failed to create model: {str(e)}'}), 500

    def update_model(self, model_id):
        """Update an existing model"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'no data provided'}), 400
            
            logging.info(f"updating model {model_id}")
            updated_model = self.model_service.update_model(model_id, data)
            
            if not updated_model:
                return jsonify({'error': 'model not found'}), 404
            
            logging.info(f"model {model_id} updated successfully")
            return jsonify({
                'message': 'model updated successfully',
                'model': updated_model
            }), 200
            
        except DatabaseError as e:
            logging.error(f"database error in update_model: {e}")
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            logging.error(f"unexpected error in update_model: {e}")
            traceback.print_exc()
            return jsonify({'error': f'failed to update model: {str(e)}'}), 500

    def delete_model(self, model_id):
        """Delete a model"""
        try:
            logging.info(f"deleting model {model_id}")
            success = self.model_service.delete_model(model_id)
            
            if not success:
                return jsonify({'error': 'model not found'}), 404
            
            logging.info(f"model {model_id} deleted successfully")
            return jsonify({'message': 'model deleted successfully'}), 200
            
        except DatabaseError as e:
            logging.error(f"database error in delete_model: {e}")
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            logging.error(f"unexpected error in delete_model: {e}")
            traceback.print_exc()
            return jsonify({'error': f'failed to delete model: {str(e)}'}), 500

    def score_session_with_model(self):
        """Score a session using a specific model"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'no data provided'}), 400
            
            session_id = data.get('session_id')
            model_id = data.get('model_id')
            project_name = data.get('project_name')
            session_name = data.get('session_name')
            
            if not all([session_id, model_id, project_name, session_name]):
                return jsonify({'error': 'missing required fields: session_id, model_id, project_name, session_name'}), 400
            
            logging.info(f"scoring session {session_id} with model {model_id}")
            
            # Get full session info including project_path - THIS IS THE FIX
            try:
                session_info = self.session_service.get_session_details(session_id)
                if not session_info:
                    return jsonify({'error': 'session not found'}), 404
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500
            
            project_path = session_info['project_path']  # Get the full path
            session_name = session_info['session_name']
            
            # delegate to model service for scoring
            scoring_result = self.model_service.score_session_with_model(
                session_id, model_id, project_path, session_name  # Use the full project_path
            )

            logging.info(f"scoring started with id: {scoring_result.get('scoring_id')}")
        
            return jsonify({
                'success': True,
                'message': f'scoring session {session_name} with model',
                'scoring_id': scoring_result['scoring_id']
            }), 200
            
        except DatabaseError as e:
            logging.error(f"database error in score_session_with_model: {e}")
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            logging.error(f"unexpected error in score_session_with_model: {e}")
            traceback.print_exc()
            return jsonify({'error': f'failed to start scoring: {str(e)}'}), 500

    def score_range_with_model(self):
        """Score a session using a specific model"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'no data provided'}), 400
            
            session_id = data.get('session_id')
            model_id = data.get('model_id')
            project_name = data.get('project_name')
            session_name = data.get('session_name')
            start_ns = data.get('start_ns')
            end_ns = data.get('end_ns')
            
            if not all([session_id, model_id, project_name, session_name]):
                return jsonify({'error': 'missing required fields: session_id, model_id, project_name, session_name'}), 400
            
            logging.info(f"scoring session {session_id} with model {model_id}")
            
            # # Get full session info including project_path - THIS IS THE FIX
            try:
                session_info = self.session_service.get_session_details(session_id)
                if not session_info:
                    return jsonify({'error': 'session not found'}), 404
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500
            
            project_path = session_info['project_path']  # Get the full path
            session_name = session_info['session_name']
            
            # delegate to model service for scoring
            scoring_result = self.model_service.score_range_with_model(
                session_id, model_id, project_path, session_name, start_ns, end_ns  # Use the full project_path
            )

            logging.info(f"scoring started with id: {scoring_result.get('scoring_id')}")
        
            return jsonify({
                'success': True,
                'message': f'scoring session {session_name} with model',
                'scoring_id': scoring_result['scoring_id']
            }), 200
            
        except DatabaseError as e:
            logging.error(f"database error in score_session_with_model: {e}")
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            logging.error(f"unexpected error in score_session_with_model: {e}")
            traceback.print_exc()
            return jsonify({'error': f'failed to start scoring: {str(e)}'}), 500

    def get_scoring_status(self, scoring_id):
        """Get the status of a scoring operation"""
        try:
            logging.info(f"getting scoring status for {scoring_id}")
            status = self.model_service.get_scoring_status(scoring_id)
            return jsonify(status), 200
        except Exception as e:
            logging.error(f"error getting scoring status: {e}")
            return jsonify({'error': str(e)}), 500
        
    def get_gpu_status(self):
        """Check if GPU is available for PyTorch"""
        try:
            gpu_available = self.model_service.is_gpu_available()
            gpu_count = self.model_service.get_gpu_count()
            gpu_name = self.model_service.get_gpu_name()
            
            return jsonify({
                'gpu_available': gpu_available,
                'gpu_count': gpu_count,
                'gpu_name': gpu_name,
                'cuda_version': self.model_service.get_cuda_version()
            }), 200
            
        except Exception as e:
            logging.error(f"error checking GPU status: {e}")
            return jsonify({
                'gpu_available': False,
                'error': str(e)
            }), 200

    def score_session_with_model_gpu(self):
        """Score a session using a specific model on GPU"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'no data provided'}), 400
            
            session_id = data.get('session_id')
            model_id = data.get('model_id')
            project_name = data.get('project_name')
            session_name = data.get('session_name')
            
            if not all([session_id, model_id, project_name, session_name]):
                return jsonify({'error': 'missing required fields: session_id, model_id, project_name, session_name'}), 400
            
            # check if GPU is available
            if not self.model_service.is_gpu_available():
                return jsonify({'error': 'GPU is not available on this system'}), 400
            
            logging.info(f"scoring session {session_id} with model {model_id} on GPU")
            
            # get full session info including project_path
            try:
                session_info = self.session_service.get_session_details(session_id)
                if not session_info:
                    return jsonify({'error': 'session not found'}), 404
            except DatabaseError as e:
                return jsonify({'error': str(e)}), 500
            
            project_path = session_info['project_path']
            session_name = session_info['session_name']
            
            # delegate to model service for GPU scoring
            scoring_result = self.model_service.score_session_with_model(
                session_id, model_id, project_path, session_name, device='cuda'  # Use GPU for scoring
            )
            
            logging.info(f"GPU scoring started with id: {scoring_result.get('scoring_id')}")
            
            return jsonify({
                'success': True,
                'message': f'GPU scoring session {session_name} with model',
                'scoring_id': scoring_result['scoring_id']
            }), 200
            
        except DatabaseError as e:
            logging.error(f"database error in score_session_with_model_gpu: {e}")
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            logging.error(f"unexpected error in score_session_with_model_gpu: {e}")
            traceback.print_exc()
            return jsonify({'error': f'failed to start GPU scoring: {str(e)}'}), 500

controller = None

def init_controller(model_service, session_service):
    global controller
    controller = ModelController(model_service, session_service)

@models_bp.route('/api/models', methods=['GET'])
def list_models():
    return controller.list_models()

@models_bp.route('/api/models', methods=['POST'])
def create_model():
    return controller.create_model()

@models_bp.route('/api/models/<int:model_id>', methods=['PUT'])
def update_model(model_id):
    return controller.update_model(model_id)

@models_bp.route('/api/models/<int:model_id>', methods=['DELETE'])
def delete_model(model_id):
    return controller.delete_model(model_id)

@models_bp.route('/api/models/score', methods=['POST'])
def score_session_with_model():
    return controller.score_session_with_model()


@models_bp.route('/api/models/score_range', methods=['POST'])
def score_range_with_model():
    return controller.score_range_with_model()

@models_bp.route('/api/scoring_status/<scoring_id>')
def get_scoring_status(scoring_id):
    return controller.get_scoring_status(scoring_id)

@models_bp.route('/api/gpu_status', methods=['GET'])
def get_gpu_status():
    return controller.get_gpu_status()

@models_bp.route('/api/models/score_gpu', methods=['POST'])
def score_session_with_model_gpu():
    return controller.score_session_with_model_gpu()