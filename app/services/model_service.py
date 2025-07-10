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

class ModelService:
    def __init__(self, session_repository=None):
        self.session_repo: SessionRepository = session_repository
        self.model = SmokingCNN(window_size=3000, num_features=3)
        self.model.load_state_dict(torch.load('model.pth', map_location='cpu'))
        self.model.eval()
        self.scoring_status = {}  # Track scoring operations
        self.models = []

    def list_models(self):
        """List all available models"""
        # TODO: Implement logic to list models from the database or filesystem
        return self.models
    
    def score_session_async(self, project_path, session_name, session_id):
        """Start async scoring of a session"""
        # Generate unique scoring ID
        scoring_id = str(uuid.uuid4())

        # Initialize status tracking
        self.scoring_status[scoring_id] = {
            'status': 'running',
            'session_id': session_id,
            'session_name': session_name,
            'start_time': time.time(),
            'error': None
        }
        # Start async processing in a separate thread
        scoring_thread = threading.Thread(
            target=self._score_session_worker,  
            args=(scoring_id, project_path, session_name, session_id)
        )
        scoring_thread.daemon = True
        scoring_thread.start()
        
        return scoring_id

    def _score_session_worker(self, scoring_id, project_path, session_name, session_id):
        try:
            print(f"Starting scoring for session {scoring_id}")

            df = pd.read_csv(f"{project_path}/{session_name}/accelerometer_data.csv")
            sample_interval = df['ns_since_reboot'].diff().median() * 1e-9
            sample_rate = 1 / sample_interval
            print(f"Sample rate: {sample_rate} Hz")

            fs = 50
            window_size_seconds = 60
            window_stride_seconds = 60

            X = []
            data = torch.tensor(df[['accel_x', 'accel_y', 'accel_z']].values, dtype=torch.float32)
            window_size = fs * window_size_seconds
            window_stride = fs * window_stride_seconds
            windowed_data = data.unfold(dimension=0,size=window_size,step=window_stride)
            X.append(windowed_data)

            X = torch.cat(X)

            with torch.no_grad():
                y_pred = self.model(X).sigmoid().cpu()
                y_pred = y_pred > .6
                y_pred = y_pred.numpy().flatten()
                y_pred = y_pred.repeat(3000)

            if len(y_pred) < len(df):
                y_pred = torch.cat([torch.tensor(y_pred), torch.zeros(len(df) - len(y_pred))])
            df['y_pred'] = y_pred*20

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

            # Remove bouts shorter than 20 seconds and format as dictionaries
            model_name = "SmokingCNN"  # You can make this configurable
            label = f"{model_name}"
            
            smoking_bouts = [
                {
                    'start': bout[0],
                    'end': bout[1], 
                    'label': label
                }
                for bout in smoking_bouts 
                if (bout[1] - bout[0]) >= 30 * 1e9
            ]
            print(f"Generated {len(smoking_bouts)} bouts with label: {label}")

            bouts = self.session_repo.get_bouts_by_session(session_id)
            json_bouts = json.loads(bouts) if bouts else []
            print(json_bouts + smoking_bouts)

            self.session_repo.set_bouts_by_session(session_id, json.dumps(json_bouts + smoking_bouts))

            # Update status on completion
            self.scoring_status[scoring_id].update({
                'status': 'completed',
                'end_time': time.time(),
                'bouts_count': len(smoking_bouts)
            })
        except Exception as e:
            print(f"Error during scoring: {e}")
            # Handle error (e.g., log it, update status, etc.)
            print(f"Error scoring session {scoring_id}: {e}")
            self.scoring_status[scoring_id].update({
                'status': 'error',
                'error': str(e),
                'end_time': time.time()
            })

        return smoking_bouts
    def get_scoring_status(self, scoring_id):
        """Get the status of a scoring operation"""
        return self.scoring_status.get(scoring_id, {'status': 'not_found'})
    
class SmokingCNN(nn.Module):
    def __init__(self, window_size=100, num_features=6):
        super(SmokingCNN, self).__init__()
        kernel_size = 3

        self.c1 = nn.Conv1d(in_channels=num_features, out_channels=4, kernel_size=kernel_size)
        self.c2 = nn.Conv1d(in_channels=4, out_channels=8, kernel_size=kernel_size)
        self.c3 = nn.Conv1d(in_channels=8, out_channels=16, kernel_size=kernel_size)

        self.classifier = nn.Linear(16, 1)
    
    
    def forward(self, x):
        x = self.c1(x)
        x = relu(x)
        x = self.c2(x)
        x = relu(x)
        x = self.c3(x)
        x = relu(x)
        x = x.mean(dim=2)

        x = self.classifier(x)
        return x
    
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
        
        # load default model for backward compatibility
        self.default_model = SmokingCNN(window_size=3000, num_features=3)
        model_path = 'model.pth'
        if os.path.exists(model_path):
            self.default_model.load_state_dict(torch.load(model_path, map_location='cpu'))
            self.default_model.eval()
            logger.info("loaded default model from model.pth")
        else:
            logger.warning("default model file model.pth not found")
        
        # ensure default model exists in database
        self._ensure_default_model_exists()

    def _ensure_default_model_exists(self):
        """ensure default model exists in database"""
        try:
            # check if any models exist
            if self.model_repo.count_active() == 0:
                logger.info("no models found, creating default model")
                default_model_data = {
                    'name': 'SmokingCNN (Default)',
                    'description': 'default smoking detection model',
                    'py_filename': 'model_service.py',
                    'pt_filename': 'model.pth',
                    'class_name': 'SmokingCNN',
                    'is_active': True
                }
                self.model_repo.create(default_model_data)
                logger.info("created default model in database")
        except Exception as e:
            logger.error(f"error ensuring default model exists: {e}")

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
            
            # for now just log the validation - later we can add actual file checks
            logger.info(f"model files should be located at:")
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
            # prevent deletion of default model (assume first model is default)
            model = self.model_repo.find_by_id(model_id)
            if not model:
                return False
            
            # for now allow deletion of any model, but we could add protection logic here
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

    def score_session_with_model(self, session_id, model_id, project_name, session_name):
        """score a session using a specific model"""
        try:
            # get model configuration
            model_config = self.get_model_by_id(model_id)
            if not model_config:
                raise DatabaseError(f'model {model_id} not found')
            
            logger.info(f"starting scoring with model {model_config['name']} for session {session_id}")
            
            # for now use the default scoring logic but log the selected model
            # later we can implement dynamic model loading based on config
            scoring_id = self.score_session_async_with_model(
                project_name, session_name, session_id, model_config
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

            # for now use the default model implementation
            # later we can dynamically load models based on model_config
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
            windowed_data = data.unfold(dimension=0,size=window_size,step=window_stride)
            X.append(windowed_data)

            X = torch.cat(X)

            with torch.no_grad():
                y_pred = self.default_model(X).sigmoid().cpu()
                y_pred = y_pred > .6
                y_pred = y_pred.numpy().flatten()
                y_pred = y_pred.repeat(3000)

            if len(y_pred) < len(df):
                y_pred = torch.cat([torch.tensor(y_pred), torch.zeros(len(df) - len(y_pred))])
            df['y_pred'] = y_pred*20

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

            # remove bouts shorter than 20 seconds and format as dictionaries
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
            
            logger.info(f"scoring completed for {scoring_id}")
            
        except Exception as e:
            logger.error(f"error during scoring {scoring_id}: {e}")
            self.scoring_status[scoring_id].update({
                'status': 'error',
                'error': str(e),
                'end_time': time.time()
            })

    # backward compatibility methods
    def list_models(self):
        """backward compatibility - list all models"""
        return self.get_all_models()
    
    def score_session_async(self, project_path, session_name, session_id):
        """backward compatibility - score with default model"""
        default_model = self.get_model_by_id(1)  # default model has id 1
        if not default_model:
            raise DatabaseError('default model not available')
        
        return self.score_session_async_with_model(project_path, session_name, session_id, default_model)

    def _score_session_worker(self, scoring_id, project_path, session_name, session_id):
        """backward compatibility worker"""
        default_model = self.get_model_by_id(1)
        if default_model:
            self._score_session_worker_with_model(scoring_id, project_path, session_name, session_id, default_model)
        else:
            self.scoring_status[scoring_id].update({
                'status': 'error',
                'error': 'default model not available',
                'end_time': time.time()
            })
    
    def get_scoring_status(self, scoring_id):
        """get the status of a scoring operation"""
        return self.scoring_status.get(scoring_id, {'status': 'not_found'})

class SmokingCNN(nn.Module):
    def __init__(self, window_size=100, num_features=6):
        super(SmokingCNN, self).__init__()
        kernel_size = 3

        self.c1 = nn.Conv1d(in_channels=num_features, out_channels=4, kernel_size=kernel_size)
        self.c2 = nn.Conv1d(in_channels=4, out_channels=8, kernel_size=kernel_size)
        self.c3 = nn.Conv1d(in_channels=8, out_channels=16, kernel_size=kernel_size)

        self.classifier = nn.Linear(16, 1)
    
    def forward(self, x):
        x = self.c1(x)
        x = relu(x)
        x = self.c2(x)
        x = relu(x)
        x = self.c3(x)
        x = relu(x)
        x = x.mean(dim=2)

        x = self.classifier(x)
        return x