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
            model_dir = self._get_model_dir()
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
                
                model_dir = self._get_model_dir()
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
            model_dir = self._get_model_dir()
            py_file_path = os.path.join(model_dir, model_config['py_filename'])
            pt_file_path = os.path.join(model_dir, model_config['pt_filename'])
            
            if not os.path.exists(py_file_path):
                raise DatabaseError(f'model python file not found: {py_file_path}')
                
            if not os.path.exists(pt_file_path):
                raise DatabaseError(f'model weights file not found: {pt_file_path}')
            
            scoring_id = self.score_session_async_with_model(project_path, session_name, session_id, model_config)
            
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

                # dynamic model loading implementation
                model_dir = self._get_model_dir()
                py_file_path = os.path.join(model_dir, model_config['py_filename'])
                pt_file_path = os.path.join(model_dir, model_config['pt_filename'])
                
                logger.info(f"loading model from:")
                logger.info(f"  python file: {py_file_path}")
                logger.info(f"  weights file: {pt_file_path}")
                logger.info(f"  class name: {model_config['class_name']}")
                
                # step 1: dynamically import the python module
                import importlib.util
                import sys
                
                spec = importlib.util.spec_from_file_location("dynamic_model", py_file_path)
                if spec is None:
                    raise Exception(f"could not load module spec from {py_file_path}")
                
                dynamic_module = importlib.util.module_from_spec(spec)
                
                # add to sys.modules to handle potential circular imports
                sys.modules["dynamic_model"] = dynamic_module
                
                try:
                    spec.loader.exec_module(dynamic_module)
                except Exception as e:
                    raise Exception(f"error executing module {py_file_path}: {str(e)}")
                
                # step 2: get the model class by name
                if not hasattr(dynamic_module, model_config['class_name']):
                    available_classes = [name for name in dir(dynamic_module) if not name.startswith('_')]
                    raise Exception(f"class '{model_config['class_name']}' not found in {py_file_path}. available classes: {available_classes}")
                
                ModelClass = getattr(dynamic_module, model_config['class_name'])
                logger.info(f"successfully loaded class: {ModelClass}")
                
                # step 3: instantiate the model
                # try common constructor patterns
                try:
                    # try without arguments first
                    model = ModelClass()
                    logger.info("model instantiated without arguments")
                except TypeError as e:
                    # if that fails, try with common smoking detection parameters
                    try:
                        model = ModelClass(window_size=3000, num_features=3)
                        logger.info("model instantiated with window_size=3000, num_features=3")
                    except TypeError as e2:
                        raise Exception(f"could not instantiate {model_config['class_name']}. tried: no args, window_size+num_features. error: {str(e2)}")
                
                # step 4: load the weights
                try:
                    state_dict = torch.load(pt_file_path, map_location='cpu')
                    model.load_state_dict(state_dict)
                    model.eval()
                    logger.info("model weights loaded successfully")
                except Exception as e:
                    raise Exception(f"error loading weights from {pt_file_path}: {str(e)}")
                
                # step 5: run the scoring logic with the loaded model
                df = pd.read_csv(f"{project_path}/{session_name}/accelerometer_data.csv")
                sample_interval = df['ns_since_reboot'].diff().median() * 1e-9
                sample_rate = 1 / sample_interval
                logger.info(f"sample rate: {sample_rate} hz")

                fs = 50
                window_size_seconds = 60
                window_stride_seconds = 60

                X = []
                data = torch.tensor(df[['accel_x', 'accel_y', 'accel_z']].values, dtype=torch.float32)
                window_size = fs * window_size_seconds
                window_stride = fs * window_stride_seconds
                windowed_data = data.unfold(dimension=0, size=window_size, step=window_stride)
                X.append(windowed_data)

                X = torch.cat(X)
                logger.info(f"prepared input tensor with shape: {X.shape}")

                # use the dynamically loaded model instead of hardcoded one
                with torch.no_grad():
                    y_pred = model(X).sigmoid().cpu()
                    y_pred = y_pred > 0.6
                    y_pred = y_pred.numpy().flatten()
                    y_pred = y_pred.repeat(3000)

                if len(y_pred) < len(df):
                    y_pred = torch.cat([torch.tensor(y_pred), torch.zeros(len(df) - len(y_pred))])
                df['y_pred'] = y_pred * 20

                smoking_bouts = []
                current_bout = None
                for i in range(len(df)):
                    if df['y_pred'].iloc[i] > 0:
                        if current_bout is None:
                            current_bout = [int(df['ns_since_reboot'].iloc[i]), None]
                        else:
                            current_bout[1] = int(df['ns_since_reboot'].iloc[i])
                    else:
                        if current_bout is not None:
                            smoking_bouts.append(current_bout)
                            current_bout = None

                # remove bouts shorter than 30 seconds and format as dictionaries
                label = f"{model_config['name']}"
                
                smoking_bouts = [
                    {
                        'start': bout[0],
                        'end': bout[1], 
                        'label': label
                    }
                    for bout in smoking_bouts 
                    if (bout[1] - bout[0]) >= 30 * 1e9
                ]
                logger.info(f"generated {len(smoking_bouts)} bouts with label: {label}")

                # add to existing bouts
                bouts = self.session_repo.get_bouts_by_session(session_id)
                json_bouts = json.loads(bouts) if bouts else []
                logger.info(f"adding {len(smoking_bouts)} new bouts to existing {len(json_bouts)} bouts")

                self.session_repo.set_bouts_by_session(session_id, json.dumps(json_bouts + smoking_bouts))

                # update status on completion
                self.scoring_status[scoring_id].update({
                    'status': 'completed',
                    'end_time': time.time(),
                    'bouts_count': len(smoking_bouts)
                })
                
                logger.info(f"scoring completed successfully for {scoring_id}")
                
                # cleanup: remove from sys.modules to prevent conflicts
                if "dynamic_model" in sys.modules:
                    del sys.modules["dynamic_model"]
                
            except Exception as e:
                logger.error(f"error during scoring {scoring_id}: {e}")
                self.scoring_status[scoring_id].update({
                    'status': 'error',
                    'error': str(e),
                    'end_time': time.time()
                })
                
                # cleanup on error too
                if "dynamic_model" in sys.modules:
                    del sys.modules["dynamic_model"]

    def _score_session_worker_with_model_gpu(self, scoring_id, project_path, session_name, session_id, model_config):
        """worker function for GPU scoring with specific model"""
        try:
            logger.info(f"GPU scoring session {scoring_id} with model {model_config['name']}")

            # check GPU availability one more time
            if not torch.cuda.is_available():
                raise Exception("GPU became unavailable during scoring")
            
            device = torch.device('cuda:0')
            logger.info(f"using GPU device: {device} ({torch.cuda.get_device_name(0)})")

            # dynamic model loading implementation (same as CPU but with GPU device)
            model_dir = self._get_model_dir()
            py_file_path = os.path.join(model_dir, model_config['py_filename'])
            pt_file_path = os.path.join(model_dir, model_config['pt_filename'])
            
            logger.info(f"loading model on GPU from:")
            logger.info(f"  python file: {py_file_path}")
            logger.info(f"  weights file: {pt_file_path}")
            logger.info(f"  class name: {model_config['class_name']}")
            
            # step 1: dynamically import the python module (same as CPU)
            import importlib.util
            import sys
            
            spec = importlib.util.spec_from_file_location("dynamic_model_gpu", py_file_path)
            if spec is None:
                raise Exception(f"could not load module spec from {py_file_path}")
            
            dynamic_module = importlib.util.module_from_spec(spec)
            sys.modules["dynamic_model_gpu"] = dynamic_module
            
            try:
                spec.loader.exec_module(dynamic_module)
            except Exception as e:
                raise Exception(f"error executing module {py_file_path}: {str(e)}")
            
            # step 2: get the model class by name (same as CPU)
            if not hasattr(dynamic_module, model_config['class_name']):
                available_classes = [name for name in dir(dynamic_module) if not name.startswith('_')]
                raise Exception(f"class '{model_config['class_name']}' not found in {py_file_path}. available classes: {available_classes}")
            
            ModelClass = getattr(dynamic_module, model_config['class_name'])
            logger.info(f"successfully loaded class: {ModelClass}")
            
            # step 3: instantiate the model (same as CPU)
            try:
                model = ModelClass()
                logger.info("model instantiated without arguments")
            except TypeError as e:
                try:
                    model = ModelClass(window_size=3000, num_features=3)
                    logger.info("model instantiated with window_size=3000, num_features=3")
                except TypeError as e2:
                    raise Exception(f"could not instantiate {model_config['class_name']}. tried: no args, window_size+num_features. error: {str(e2)}")
            
            # step 4: load weights and move to GPU
            try:
                state_dict = torch.load(pt_file_path, map_location='cpu')  # Load to CPU first
                model.load_state_dict(state_dict)
                model = model.to(device)  # Move model to GPU
                model.eval()
                logger.info(f"model weights loaded and moved to GPU: {device}")
            except Exception as e:
                raise Exception(f"error loading weights to GPU from {pt_file_path}: {str(e)}")
            
            # step 5: run the scoring logic with GPU acceleration
            df = pd.read_csv(f"{project_path}/{session_name}/accelerometer_data.csv")
            sample_interval = df['ns_since_reboot'].diff().median() * 1e-9
            sample_rate = 1 / sample_interval
            logger.info(f"sample rate: {sample_rate} hz")

            fs = 50
            window_size_seconds = 60
            window_stride_seconds = 60

            X = []
            data = torch.tensor(df[['accel_x', 'accel_y', 'accel_z']].values, dtype=torch.float32)
            window_size = fs * window_size_seconds
            window_stride = fs * window_stride_seconds
            windowed_data = data.unfold(dimension=0, size=window_size, step=window_stride)
            X.append(windowed_data)

            X = torch.cat(X).to(device)  # Move input data to GPU
            logger.info(f"prepared input tensor with shape: {X.shape} on device: {X.device}")

            # use the GPU model for inference
            with torch.no_grad():
                y_pred = model(X).sigmoid().cpu()  # Move result back to CPU
                y_pred = y_pred > 0.6
                y_pred = y_pred.numpy().flatten()
                y_pred = y_pred.repeat(3000)

            logger.info("GPU inference completed, processing results...")

            if len(y_pred) < len(df):
                y_pred = torch.cat([torch.tensor(y_pred), torch.zeros(len(df) - len(y_pred))])
            df['y_pred'] = y_pred * 20

            smoking_bouts = []
            current_bout = None
            for i in range(len(df)):
                if df['y_pred'].iloc[i] > 0:
                    if current_bout is None:
                        current_bout = [int(df['ns_since_reboot'].iloc[i]), None]
                    else:
                        current_bout[1] = int(df['ns_since_reboot'].iloc[i])
                else:
                    if current_bout is not None:
                        smoking_bouts.append(current_bout)
                        current_bout = None

         
            label = f"{model_config['name']}"
            
            smoking_bouts = [
                {
                    'start': bout[0],
                    'end': bout[1], 
                    'label': label
                }
                for bout in smoking_bouts 
                if (bout[1] - bout[0]) >= 30 * 1e9
            ]
            logger.info(f"GPU generated {len(smoking_bouts)} bouts with label: {label}")

            # add to existing bouts
            bouts = self.session_repo.get_bouts_by_session(session_id)
            json_bouts = json.loads(bouts) if bouts else []
            logger.info(f"adding {len(smoking_bouts)} new GPU bouts to existing {len(json_bouts)} bouts")

            self.session_repo.set_bouts_by_session(session_id, json.dumps(json_bouts + smoking_bouts))

            # update status on completion
            self.scoring_status[scoring_id].update({
                'status': 'completed',
                'end_time': time.time(),
                'bouts_count': len(smoking_bouts),
                'device_used': f"GPU ({torch.cuda.get_device_name(0)})"
            })
            
            logger.info(f"GPU scoring completed successfully for {scoring_id}")
            
            # cleanup
            if "dynamic_model_gpu" in sys.modules:
                del sys.modules["dynamic_model_gpu"]
            
            # clear GPU cache
            torch.cuda.empty_cache()
            
        except Exception as e:
            logger.error(f"error during GPU scoring {scoring_id}: {e}")
            self.scoring_status[scoring_id].update({
                'status': 'error',
                'error': str(e),
                'end_time': time.time()
            })
            
            # cleanup on error
            if "dynamic_model_gpu" in sys.modules:
                del sys.modules["dynamic_model_gpu"]
            torch.cuda.empty_cache()

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
    
    def _get_model_dir(self):
        """get the model dir  expand the path"""
        model_dir = os.getenv('MODEL_DIR', './models')
        return os.path.expanduser(model_dir)

    def is_gpu_available(self):
        """check if GPU is available for PyTorch"""
        try:
            return torch.cuda.is_available()
        except Exception as e:
            logger.error(f"error checking GPU availability: {e}")
            return False

    def get_gpu_count(self):
        """get number of available GPUs"""
        try:
            if torch.cuda.is_available():
                return torch.cuda.device_count()
            return 0
        except Exception as e:
            logger.error(f"error getting GPU count: {e}")
            return 0

    def get_gpu_name(self):
        """get name of the primary GPU"""
        try:
            if torch.cuda.is_available() and torch.cuda.device_count() > 0:
                return torch.cuda.get_device_name(0)
            return None
        except Exception as e:
            logger.error(f"error getting GPU name: {e}")
            return None

    def get_cuda_version(self):
        """get CUDA version"""
        try:
            if torch.cuda.is_available():
                return torch.version.cuda
            return None
        except Exception as e:
            logger.error(f"error getting CUDA version: {e}")
            return None

    def score_session_with_model_gpu(self, session_id, model_id, project_path, session_name):
        """score a session using a specific model on GPU"""
        try:
            # check GPU availability
            if not self.is_gpu_available():
                raise DatabaseError('GPU is not available on this system')
            
            # get model configuration
            model_config = self.get_model_by_id(model_id)
            if not model_config:
                raise DatabaseError(f'model {model_id} not found')
            
            logger.info(f"starting GPU scoring with model {model_config['name']} for session {session_id}")
            
            # validate model files exist before starting scoring
            model_dir = self._get_model_dir()
            py_file_path = os.path.join(model_dir, model_config['py_filename'])
            pt_file_path = os.path.join(model_dir, model_config['pt_filename'])
            
            if not os.path.exists(py_file_path):
                raise DatabaseError(f'model python file not found: {py_file_path}')
                
            if not os.path.exists(pt_file_path):
                raise DatabaseError(f'model weights file not found: {pt_file_path}')
            
            scoring_id = self.score_session_async_with_model_gpu(
                project_path, session_name, session_id, model_config
            )
            
            return {'scoring_id': scoring_id}
            
        except Exception as e:
            logger.error(f"error starting GPU scoring with model {model_id}: {e}")
            raise DatabaseError(f'failed to start GPU scoring: {str(e)}')

    def score_session_async_with_model_gpu(self, project_path, session_name, session_id, model_config):
        """start async GPU scoring with specific model configuration"""
        # generate unique scoring id
        scoring_id = str(uuid.uuid4())

        # initialize status tracking with GPU indicator
        self.scoring_status[scoring_id] = {
            'status': 'running',
            'session_id': session_id,
            'session_name': session_name,
            'model_id': model_config['id'],
            'model_name': model_config['name'],
            'device': 'gpu',
            'start_time': time.time(),
            'error': None
        }
        
        # start async processing in a separate thread
        scoring_thread = threading.Thread(
            target=self._score_session_worker_with_model_gpu,  
            args=(scoring_id, project_path, session_name, session_id, model_config)
        )
        scoring_thread.daemon = True
        scoring_thread.start()
        
        return scoring_id