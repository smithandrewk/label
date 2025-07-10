from time import sleep
import uuid
import threading
import time
import uuid
import json
import torch
import numpy as np
import pandas as pd
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.nn.functional import relu
from torch.utils.data import DataLoader, TensorDataset
from app.repositories.session_repository import SessionRepository
from app.exceptions import DatabaseError
from app.logging_config import get_logger

logger = get_logger(__name__)
class ModelService:
    def __init__(self, session_repository=None, model_repository=None):
        self.session_repo: SessionRepository = session_repository
        self.model_repo = model_repository
        self.scoring_status = {}  # track scoring operations
        
        # remove hardcoded default model loading
        # users must add their own models through the UI
        logger.info("model service initialized - no default models loaded")

    # remove _ensure_default_model_exists method entirely

    def get_all_models(self):
        """get all available models"""
        try:
            models = self.model_repo.get_all_active()
            # convert to dict format for json serialization
            formatted_models = []
            for model in models:
                formatted_models.append({
                    'id': model['model_id'],
                    'name': model['name'],
                    'description': model['description'] or '',
                    'py_filename': model['py_filename'],
                    'pt_filename': model['pt_filename'],
                    'class_name': model['class_name'],
                    'is_active': bool(model['is_active']),
                    'created_at': model['created_at'].isoformat() if model['created_at'] else None
                })
            
            logger.info(f"returning {len(formatted_models)} available models")
            return formatted_models
        except Exception as e:
            logger.error(f"error getting all models: {e}")
            raise DatabaseError(f'failed to get models: {str(e)}')

    def create_model(self, model_data):
        """create a new model configuration"""
        try:
            # validate model files exist
            model_dir = os.getenv('MODEL_DIR', './models')
            py_file_path = os.path.join(model_dir, model_data['py_filename'])
            pt_file_path = os.path.join(model_dir, model_data['pt_filename'])
            
            # add actual file validation
            if not os.path.exists(model_dir):
                raise DatabaseError(f'model directory does not exist: {model_dir}')
            
            if not os.path.exists(py_file_path):
                raise DatabaseError(f'python file not found: {py_file_path}')
                
            if not os.path.exists(pt_file_path):
                raise DatabaseError(f'weights file not found: {pt_file_path}')
            
            logger.info(f"validated model files:")
            logger.info(f"  python file: {py_file_path}")
            logger.info(f"  weights file: {pt_file_path}")
            
            # create model record in database
            created_model = self.model_repo.create(model_data)
            
            # format for json response
            formatted_model = {
                'id': created_model['model_id'],
                'name': created_model['name'],
                'description': created_model['description'] or '',
                'py_filename': created_model['py_filename'],
                'pt_filename': created_model['pt_filename'],
                'class_name': created_model['class_name'],
                'is_active': bool(created_model['is_active']),
                'created_at': created_model['created_at'].isoformat() if created_model['created_at'] else None
            }
            
            logger.info(f"created new model: {formatted_model['name']} with id {formatted_model['id']}")
            return formatted_model
            
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"error creating model: {e}")
            raise DatabaseError(f'failed to create model: {str(e)}')

    def update_model(self, model_id, model_data):
        """update an existing model"""
        try:
            # if updating file paths, validate they exist
            if 'py_filename' in model_data or 'pt_filename' in model_data:
                model = self.model_repo.find_by_id(model_id)
                if not model:
                    raise DatabaseError('model not found')
                
                model_dir = os.getenv('MODEL_DIR', './models')
                py_filename = model_data.get('py_filename', model['py_filename'])
                pt_filename = model_data.get('pt_filename', model['pt_filename'])
                
                py_file_path = os.path.join(model_dir, py_filename)
                pt_file_path = os.path.join(model_dir, pt_filename)
                
                if not os.path.exists(py_file_path):
                    raise DatabaseError(f'python file not found: {py_file_path}')
                    
                if not os.path.exists(pt_file_path):
                    raise DatabaseError(f'weights file not found: {pt_file_path}')
            
            updated_model = self.model_repo.update(model_id, model_data)
            
            if not updated_model:
                return None
            
            # format for json response
            formatted_model = {
                'id': updated_model['model_id'],
                'name': updated_model['name'],
                'description': updated_model['description'] or '',
                'py_filename': updated_model['py_filename'],
                'pt_filename': updated_model['pt_filename'],
                'class_name': updated_model['class_name'],
                'is_active': bool(updated_model['is_active']),
                'created_at': updated_model['created_at'].isoformat() if updated_model['created_at'] else None
            }
            
            logger.info(f"updated model {model_id}: {formatted_model['name']}")
            return formatted_model
            
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"error updating model {model_id}: {e}")
            raise DatabaseError(f'failed to update model: {str(e)}')

    def delete_model(self, model_id):
        """delete a model (soft delete by setting is_active to false)"""
        try:
            model = self.model_repo.find_by_id(model_id)
            if not model:
                return False
            
            self.model_repo.delete(model_id)
            
            logger.info(f"deleted model {model_id}: {model['name']}")
            return True
            
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"error deleting model {model_id}: {e}")
            raise DatabaseError(f'failed to delete model: {str(e)}')

    def get_model_by_id(self, model_id):
        """get a specific model by id"""
        try:
            model = self.model_repo.find_by_id(model_id)
            if not model or not model['is_active']:
                return None
            
            # format for internal use
            return {
                'id': model['model_id'],
                'name': model['name'],
                'description': model['description'] or '',
                'py_filename': model['py_filename'],
                'pt_filename': model['pt_filename'],
                'class_name': model['class_name']
            }
        except Exception as e:
            logger.error(f"error getting model {model_id}: {e}")
            return None

    def score_session_with_model(self, session_id, model_id, project_path, session_name):
        """score a session using a specific model"""
        try:
            # get model configuration
            model_config = self.get_model_by_id(model_id)
            if not model_config:
                raise DatabaseError(f'model {model_id} not found')
            
            logger.info(f"starting scoring with model {model_config['name']} for session {session_id}")
            
            # validate model files exist before starting scoring
            model_dir = os.getenv('MODEL_DIR', './models')
            py_file_path = os.path.join(model_dir, model_config['py_filename'])
            pt_file_path = os.path.join(model_dir, model_config['pt_filename'])
            
            if not os.path.exists(py_file_path):
                raise DatabaseError(f'model python file not found: {py_file_path}')
                
            if not os.path.exists(pt_file_path):
                raise DatabaseError(f'model weights file not found: {pt_file_path}')
            
            scoring_id = self.score_session_async_with_model(
                project_path, session_name, session_id, model_config
            )
            
            return {'scoring_id': scoring_id}
            
        except Exception as e:
            logger.error(f"error starting scoring with model {model_id}: {e}")
            raise DatabaseError(f'failed to start scoring: {str(e)}')

    def score_session_async_with_model(self, project_path, session_name, session_id, model_config):
        """start async scoring with specific model configuration"""
        # generate unique scoring id
        scoring_id = str(uuid.uuid4())

        # initialize status tracking
        self.scoring_status[scoring_id] = {
            'status': 'running',
            'session_id': session_id,
            'session_name': session_name,
            'model_id': model_config['id'],
            'model_name': model_config['name'],
            'start_time': time.time(),
            'error': None
        }
        
        # start async processing in a separate thread
        scoring_thread = threading.Thread(
            target=self._score_session_worker_with_model,  
            args=(scoring_id, project_path, session_name, session_id, model_config)
        )
        scoring_thread.daemon = True
        scoring_thread.start()
        
        return scoring_id

    def _score_session_worker_with_model(self, scoring_id, project_path, session_name, session_id, model_config):
        """worker function for scoring with specific model"""
        try:
            logger.info(f"scoring session {scoring_id} with model {model_config['name']}")

            # TODO: implement dynamic model loading based on model_config
            # for now, this will fail gracefully since we removed the default model
            logger.error("dynamic model loading not yet implemented")
            raise Exception("dynamic model loading not yet implemented - please implement model loading based on model_config")
            
        except Exception as e:
            logger.error(f"error during scoring {scoring_id}: {e}")
            self.scoring_status[scoring_id].update({
                'status': 'error',
                'error': str(e),
                'end_time': time.time()
            })

    # update backward compatibility methods to handle no default model
    def list_models(self):
        """backward compatibility - list all models"""
        return self.get_all_models()
    
    def score_session_async(self, project_path, session_name, session_id):
        """backward compatibility - score with first available model or fail gracefully"""
        try:
            available_models = self.get_all_models()
            if not available_models:
                raise DatabaseError('no models configured - please add a model through the UI before scoring')
            
            # use the first available model
            first_model = available_models[0]
            model_config = {
                'id': first_model['id'],
                'name': first_model['name'],
                'py_filename': first_model['py_filename'],
                'pt_filename': first_model['pt_filename'],
                'class_name': first_model['class_name']
            }
            
            logger.info(f"using first available model for backward compatibility: {model_config['name']}")
            return self.score_session_async_with_model(project_path, session_name, session_id, model_config)
            
        except Exception as e:
            logger.error(f"error in backward compatibility scoring: {e}")
            raise DatabaseError(f'scoring failed: {str(e)}')

    def _score_session_worker(self, scoring_id, project_path, session_name, session_id):
        """backward compatibility worker - should not be called anymore"""
        logger.error("old scoring worker called - this should use the model-specific worker")
        self.scoring_status[scoring_id].update({
            'status': 'error',
            'error': 'old scoring method called - please use model selection',
            'end_time': time.time()
        })
    
    def get_scoring_status(self, scoring_id):
        """get the status of a scoring operation"""
        return self.scoring_status.get(scoring_id, {'status': 'not_found'})

# remove the SmokingCNN class entirely - models should be loaded dynamically