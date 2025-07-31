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
from app.repositories.session_repository import SessionRepository
from app.exceptions import DatabaseError
from app.logging_config import get_logger
from app.services.model_processor import ModelProcessor

logger = get_logger(__name__)

class ModelService:
    def __init__(self, session_repository=None, model_repository=None):
        self.session_repo: SessionRepository = session_repository
        self.model_repo = model_repository
        self.scoring_status = {}  # track scoring operations
        
        logger.info("model service initialized - no default models loaded")

    def get_all_models(self):
        """get all available models"""
        try:
            models = self.model_repo.get_all_active()
            # convert to dict format for json serialization
            formatted_models = []
            for model in models:
                import json
                model_settings = None
                if model.get('model_settings'):
                    try:
                        model_settings = json.loads(model['model_settings'])
                    except (json.JSONDecodeError, TypeError):
                        model_settings = None
                
                formatted_models.append({
                    'id': model['model_id'],
                    'name': model['name'],
                    'description': model['description'] or '',
                    'py_filename': model['py_filename'],
                    'pt_filename': model['pt_filename'],
                    'class_name': model['class_name'],
                    'model_settings': model_settings,
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
            
            # validate model interface by actually loading and testing it
            logger.info("validating model interface...")
            test_model_config = {
                'id': 'test',
                'name': model_data['name'],
                'py_filename': model_data['py_filename'],
                'pt_filename': model_data['pt_filename'],
                'class_name': model_data['class_name']
            }
            
            try:
                # Load model instance to test interface
                test_model_instance = self._load_model_instance(test_model_config, device='cpu')
                
                # Validate interface using ModelProcessor
                ModelProcessor(test_model_instance)
                
                logger.info(f"model interface validation passed for {model_data['name']}")
                
            except Exception as e:
                logger.error(f"model .py file validation failed: {e}")
                raise DatabaseError(f'model .py files validation failed: {str(e)}')
            finally:
                # Clean up any imported modules from testing
                import sys
                module_name = f"dynamic_model_cpu_test"
                if module_name in sys.modules:
                    del sys.modules[module_name]
            
            # create model record in database
            created_model = self.model_repo.create(model_data)
            
            # format for json response with model_settings parsing
            import json
            model_settings = None
            if created_model.get('model_settings'):
                try:
                    model_settings = json.loads(created_model['model_settings'])
                except (json.JSONDecodeError, TypeError):
                    model_settings = None
            
            formatted_model = {
                'id': created_model['model_id'],
                'name': created_model['name'],
                'description': created_model['description'] or '',
                'py_filename': created_model['py_filename'],
                'pt_filename': created_model['pt_filename'],
                'class_name': created_model['class_name'],
                'model_settings': model_settings,
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
            
            # format for json response with model_settings parsing
            import json
            model_settings = None
            if updated_model.get('model_settings'):
                try:
                    model_settings = json.loads(updated_model['model_settings'])
                except (json.JSONDecodeError, TypeError):
                    model_settings = None
            
            formatted_model = {
                'id': updated_model['model_id'],
                'name': updated_model['name'],
                'description': updated_model['description'] or '',
                'py_filename': updated_model['py_filename'],
                'pt_filename': updated_model['pt_filename'],
                'class_name': updated_model['class_name'],
                'model_settings': model_settings,
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
            
            import json
            model_settings = None
            if model.get('model_settings'):
                try:
                    model_settings = json.loads(model['model_settings'])
                except (json.JSONDecodeError, TypeError):
                    model_settings = None
            
            # format for internal use
            return {
                'id': model['model_id'],
                'name': model['name'],
                'description': model['description'] or '',
                'py_filename': model['py_filename'],
                'pt_filename': model['pt_filename'],
                'class_name': model['class_name'],
                'model_settings': model_settings
            }
        except Exception as e:
            logger.error(f"error getting model {model_id}: {e}")
            return None

    # =======================
    # Data Processing Logic
    # =======================

    def load_session_data(self, project_path, session_name):
        """
        Extract CSV loading logic into a separate method
        
        Args:
            project_path: Path to the project directory
            session_name: Name of the session
            
        Returns:
            pandas.DataFrame: Session data with proper column naming
        """
        try:
            csv_path = f"{project_path}/{session_name}/accelerometer_data.csv"
            logger.info(f"Loading session data from: {csv_path}")
            
            df = pd.read_csv(csv_path)
            
            # Ensure proper column naming
            if 'x' in df.columns:
                df = df.rename(columns={'x': 'accel_x', 'y': 'accel_y', 'z': 'accel_z'})
            
            # Calculate sample rate for logging
            sample_interval = df['ns_since_reboot'].diff().median() * 1e-9
            sample_rate = 1 / sample_interval
            logger.info(f"loaded session data: {len(df)} rows at {sample_rate:.1f} Hz")
            
            return df
            
        except Exception as e:
            logger.error(f"error loading session data: {e}")
            raise DatabaseError(f'failed to load session data: {str(e)}')
        
    def load_range_data(self, project_path, session_name, start_ns, end_ns):
        """
        Extract CSV loading logic into a separate method
        
        Args:
            project_path: Path to the project directory
            session_name: Name of the session
            
        Returns:
            pandas.DataFrame: Session data with proper column naming
        """
        try:
            csv_path = f"{project_path}/{session_name}/accelerometer_data.csv"
            logger.info(f"Loading session data from: {csv_path}")
            
            df = pd.read_csv(csv_path)
            
            # Ensure proper column naming
            if 'x' in df.columns:
                df = df.rename(columns={'x': 'accel_x', 'y': 'accel_y', 'z': 'accel_z'})
            
            # Calculate sample rate for logging
            sample_interval = df['ns_since_reboot'].diff().median() * 1e-9
            sample_rate = 1 / sample_interval
            logger.info(f"loaded session data: {len(df)} rows at {sample_rate:.1f} Hz")
            
            # Filter by range
            df = df[(df['ns_since_reboot'] >= start_ns) & (df['ns_since_reboot'] <= end_ns)]

            if df.empty:
                logger.warning(f"no data found in range {start_ns} to {end_ns} for session {session_name}")
                return pd.DataFrame(columns=['ns_since_reboot', 'accel_x', 'accel_y', 'accel_z', 'y_pred'])
            
            return df
            
        except Exception as e:
            logger.error(f"error loading session data: {e}")
            raise DatabaseError(f'failed to load session data: {str(e)}')

    def _extract_bouts_from_predictions(self, df, predictions, labeling_name, min_duration_sec=0.25):
        """
        Extract bouts from prediction timeline
        
        Args:
            df: DataFrame with time data
            predictions: Model predictions (already thresholded binary values)
            labeling_name: Name for the labeling (None to use no label - append to current)
            min_duration_sec: Minimum bout duration in seconds
            
        Returns:
            list: List of bout dictionaries
        """
        try:
            # Add predictions to dataframe with configurable threshold
            if len(predictions) < len(df):
                # Extend predictions if needed
                extended_predictions = np.concatenate([
                    predictions, 
                    np.zeros(len(df) - len(predictions))
                ])
                df = df.copy()
                df['y_pred'] = extended_predictions
            else:
                df = df.copy()
                df['y_pred'] = predictions[:len(df)]

            # Extract bouts (predictions are already thresholded by processor)
            smoking_bouts = []
            current_bout = None
            
            for i in range(len(df)):
                if df['y_pred'].iloc[i] > 0:  # Already binary from processor
                    if current_bout is None:
                        current_bout = [int(df['ns_since_reboot'].iloc[i]), None]
                    current_bout[1] = int(df['ns_since_reboot'].iloc[i])
                else:
                    if current_bout is not None:
                        smoking_bouts.append(current_bout)
                        current_bout = None

            # Close any open bout
            if current_bout is not None:
                smoking_bouts.append(current_bout)

            # Filter by minimum duration and format as dictionaries
            min_duration_ns = min_duration_sec * 1e9
            label = labeling_name or "smoking"
            
            logger.info(f"Filtering bouts: min_duration_sec={min_duration_sec}, min_duration_ns={min_duration_ns}")
            logger.info(f"Found {len(smoking_bouts)} raw bouts before filtering")
            
            filtered_bouts = [
                {
                    'start': bout[0],
                    'end': bout[1], 
                    'label': label
                }
                for bout in smoking_bouts 
                if ((bout[1] - bout[0]) >= min_duration_ns)
            ]
            
            # Log some debug info about filtering
            if len(smoking_bouts) > 0:
                durations = [(bout[1] - bout[0]) / 1e9 for bout in smoking_bouts]
                logger.info(f"Bout durations (seconds): {durations[:10]}...")  # Show first 10
                logger.info(f"Min required duration: {min_duration_sec}s ({min_duration_ns}ns)")
            
            logger.info(f"extracted {len(filtered_bouts)} bouts with label: {label} "
                       f"(filtered from {len(smoking_bouts)} raw bouts)")
            
            return filtered_bouts
            
        except Exception as e:
            logger.error(f"error extracting bouts: {e}")
            raise DatabaseError(f'failed to extract bouts: {str(e)}')

    def _load_model_instance(self, model_config, device):
        """
        Extract and centralize dynamic model loading
        
        Args:
            model_config: Model configuration dictionary
            device: Target device ('cpu' or 'cuda')
            
        Returns:
            Loaded and configured model instance
        """
        try:
            model_dir = self._get_model_dir()
            py_file_path = os.path.join(model_dir, model_config['py_filename'])
            pt_file_path = os.path.join(model_dir, model_config['pt_filename'])
            
            logger.info(f"loading model from:")
            logger.info(f"  python file: {py_file_path}")
            logger.info(f"  weights file: {pt_file_path}")
            logger.info(f"  class name: {model_config['class_name']}")
            logger.info(f"  target device: {device}")
            
            # Dynamic import
            import importlib.util
            import sys
            
            module_name = f"dynamic_model_{device}_{model_config['id']}"
            spec = importlib.util.spec_from_file_location(module_name, py_file_path)
            if spec is None:
                raise Exception(f"could not load module spec from {py_file_path}")
            
            dynamic_module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = dynamic_module
            
            try:
                spec.loader.exec_module(dynamic_module)
            except Exception as e:
                raise Exception(f"error executing module {py_file_path}: {str(e)}")
            
            # Get model class
            if not hasattr(dynamic_module, model_config['class_name']):
                available_classes = [name for name in dir(dynamic_module) if not name.startswith('_')]
                raise Exception(f"class '{model_config['class_name']}' not found in {py_file_path}. "
                              f"available classes: {available_classes}")
            
            ModelClass = getattr(dynamic_module, model_config['class_name'])
            logger.info(f"successfully loaded class: {ModelClass}")
            
            # Instantiate model
            try:
                model = ModelClass()
                logger.info("model instantiated without arguments")
            except TypeError as e:
                try:
                    model = ModelClass(window_size=3000, num_features=3)
                    logger.info("model instantiated with window_size=3000, num_features=3")
                except TypeError as e2:
                    raise Exception(f"could not instantiate {model_config['class_name']}. "
                                  f"tried: no args, window_size+num_features. error: {str(e2)}")
            
            # Load weights
            try:
                device_obj = torch.device(device)
                state_dict = torch.load(pt_file_path, map_location='cpu')
                model.load_state_dict(state_dict)
                model = model.to(device_obj)
                model.eval()
                logger.info(f"model weights loaded and moved to device: {device}")
            except Exception as e:
                raise Exception(f"error loading weights to {device} from {pt_file_path}: {str(e)}")
            
            return model
            
        except Exception as e:
            logger.error(f"error loading model instance: {e}")
            # Cleanup
            if 'module_name' in locals() and module_name in sys.modules:
                del sys.modules[module_name]
            raise

    def _save_bouts_to_session(self, session_id, bouts):
        """
        Save bouts to session in database
        
        Args:
            session_id: ID of the session
            bouts: List of bout dictionaries
        """
        try:
            # Get existing bouts and merge
            existing_bouts = self.session_repo.get_bouts_by_session(session_id)
            json_bouts = json.loads(existing_bouts) if existing_bouts else []
            
            logger.info(f"adding {len(bouts)} new bouts to existing {len(json_bouts)} bouts for session {session_id}")
            
            # Save merged bouts
            merged_bouts = json_bouts + bouts
            self.session_repo.set_bouts_by_session(session_id, json.dumps(merged_bouts))
            
            logger.info(f"successfully saved {len(merged_bouts)} total bouts to session {session_id}")
            
        except Exception as e:
            logger.error(f"error saving bouts to session {session_id}: {e}")
            raise DatabaseError(f'failed to save bouts: {str(e)}')

    # =======================
    #   Worker 
    # =======================

    def _score_session_worker(self, scoring_id, project_path, session_name, session_id, model_config, device='cpu', append_to_current=True, current_labeling_name=None):
        """
        Unified worker function that handles both CPU and GPU scoring through delegation
        
        Args:
            scoring_id: Unique identifier for this scoring operation
            project_path: Path to the project directory
            session_name: Name of the session
            session_id: Database session ID
            model_config: Model configuration dictionary
            device: Target device ('cpu' or 'cuda')
        """
        try:
            device_label = device.upper()
            logger.info(f"{device_label} scoring session {scoring_id} with model {model_config['name']}")

            # Step 1: Load session data
            data = self.load_session_data(project_path, session_name)

            # Step 2: Get model settings or use defaults
            model_settings = model_config.get('model_settings', {})
            threshold = model_settings.get('threshold', 0.5)
            min_bout_duration_ns = model_settings.get('min_bout_duration_ns', 250000000)  # 0.25 seconds
            min_bout_duration_sec = min_bout_duration_ns / 1e9
            
            logger.info(f"Model config model_settings: {model_config.get('model_settings')}")
            logger.info(f"Using model settings: threshold={threshold}, min_bout_duration_ns={min_bout_duration_ns}, min_bout_duration_sec={min_bout_duration_sec}")
            
            # Step 3: Load and wrap model with processor
            model_instance = self._load_model_instance(model_config, device)
            processor = ModelProcessor(model_instance)
            
            # Step 4: Process through model pipeline with custom threshold
            time_domain_predictions = processor.process(data, device, threshold)
            
            # Step 5: Extract bouts from predictions using model settings
            if append_to_current:
                labeling_name = current_labeling_name if current_labeling_name else "smoking"
            else:
                labeling_name = model_config['name']
            
            bouts = self._extract_bouts_from_predictions(
                data, time_domain_predictions, labeling_name, min_bout_duration_sec
            )
            
            # Step 6: Save bouts to database
            self._save_bouts_to_session(session_id, bouts)
            
            # Update status on completion
            self.scoring_status[scoring_id].update({
                'status': 'completed',
                'end_time': time.time(),
                'bouts_count': len(bouts),
                'device_used': f"{device_label}" + (f" ({torch.cuda.get_device_name(0)})" if device == 'cuda' else "")
            })
            
            logger.info(f"{device_label} scoring completed successfully for {scoring_id}")
            
        except Exception as e:
            logger.error(f"error during {device.upper()} scoring {scoring_id}: {e}")
            self.scoring_status[scoring_id].update({
                'status': 'error',
                'error': str(e),
                'end_time': time.time()
            })
        finally:
            # Cleanup: clear GPU cache if using GPU
            if device == 'cuda':
                torch.cuda.empty_cache()

    def _score_range_worker(self, scoring_id, project_path, session_name, session_id, model_config, start_ns, end_ns, device='cpu', append_to_current=True, current_labeling_name=None):
        """
        Unified worker function that handles both CPU and GPU scoring through delegation
        
        Args:
            scoring_id: Unique identifier for this scoring operation
            project_path: Path to the project directory
            session_name: Name of the session
            session_id: Database session ID
            model_config: Model configuration dictionary
            device: Target device ('cpu' or 'cuda')
        """
        try:
            device_label = device.upper()
            logger.info(f"{device_label} scoring session {scoring_id} with model {model_config['name']}")

            # Step 1: Load session data
            data = self.load_range_data(project_path, session_name, start_ns, end_ns)
            
            # Step 2: Get model settings or use defaults
            model_settings = model_config.get('model_settings', {})
            threshold = model_settings.get('threshold', 0.5)
            min_bout_duration_ns = model_settings.get('min_bout_duration_ns', 250000000)  # 0.25 seconds
            min_bout_duration_sec = min_bout_duration_ns / 1e9
            
            logger.info(f"Model config model_settings: {model_config.get('model_settings')}")
            logger.info(f"Using model settings: threshold={threshold}, min_bout_duration_ns={min_bout_duration_ns}, min_bout_duration_sec={min_bout_duration_sec}")
            
            # Step 3: Load and wrap model with processor
            model_instance = self._load_model_instance(model_config, device)
            processor = ModelProcessor(model_instance)
            
            # Step 4: Process through model pipeline with custom threshold
            time_domain_predictions = processor.process(data, device, threshold)
            
            # Step 5: Extract bouts from predictions using model settings
            if append_to_current:
                labeling_name = current_labeling_name if current_labeling_name else "smoking"
            else:
                labeling_name = model_config['name']
            
            bouts = self._extract_bouts_from_predictions(
                data, time_domain_predictions, labeling_name, min_bout_duration_sec
            )
            
            # Step 6: Save bouts to database
            self._save_bouts_to_session(session_id, bouts)
            
            # Update status on completion
            self.scoring_status[scoring_id].update({
                'status': 'completed',
                'end_time': time.time(),
                'bouts_count': len(bouts),
                'device_used': f"{device_label}" + (f" ({torch.cuda.get_device_name(0)})" if device == 'cuda' else "")
            })
            
            logger.info(f"{device_label} scoring completed successfully for {scoring_id}")
            
        except Exception as e:
            logger.error(f"error during {device.upper()} scoring {scoring_id}: {e}")
            self.scoring_status[scoring_id].update({
                'status': 'error',
                'error': str(e),
                'end_time': time.time()
            })
        finally:
            # Cleanup: clear GPU cache if using GPU
            if device == 'cuda':
                torch.cuda.empty_cache()

    # =======================
    # Updated Public API Methods
    # =======================

    def score_session_with_model(self, session_id, model_id, project_path, session_name, start_ns=None, end_ns=None, device='cpu', append_to_current=True, current_labeling_name=None):
        """score a session using a specific model"""
        try:
            if device not in ['cpu', 'cuda']:
                raise ValueError('device must be either "cpu" or "cuda"')
            
            if device == 'cuda' and not self.is_gpu_available():
                raise RuntimeError('GPU is not available on this system')

            model_config = self.get_model_by_id(model_id)
            if not model_config:
                raise DatabaseError(f'model {model_id} not found')
            
            logger.info(f"starting {device} scoring with model {model_config['name']} for session {session_id}")
            
            # Validate model files exist
            self._validate_model_files(model_config)
            
            if start_ns is not None and end_ns is not None:
                # Range scoring
                logger.info(f"scoring range {start_ns} to {end_ns} for session {session_id}")
                scoring_id = self.score_range_async_with_model(
                    project_path, session_name, session_id, model_config, start_ns, end_ns, device=device, append_to_current=append_to_current, current_labeling_name=current_labeling_name
                )
            else:
                # Full session scoring
                logger.info(f"scoring full session {session_id} with model {model_config['name']}")
                scoring_id = self.score_session_async_with_model(
                    project_path, session_name, session_id, model_config, device=device, append_to_current=append_to_current, current_labeling_name=current_labeling_name
                )
            
            return {'scoring_id': scoring_id}
            
        except Exception as e:
            logger.error(f"error starting CPU scoring with model {model_id}: {e}")
            raise DatabaseError(f'failed to start scoring: {str(e)}')

    def score_session_async_with_model(self, project_path, session_name, session_id, model_config, device='cpu', append_to_current=True, current_labeling_name=None):
        """start async scoring with specific model configuration and device"""
        scoring_id = str(uuid.uuid4())
        device_label = device.upper()

        # Initialize status tracking
        self.scoring_status[scoring_id] = {
            'status': 'running',
            'session_id': session_id,
            'session_name': session_name,
            'model_id': model_config['id'],
            'model_name': model_config['name'],
            'device': device,
            'start_time': time.time(),
            'error': None
        }
        
        # Start async processing using unified worker
        scoring_thread = threading.Thread(
            target=self._score_session_worker,  
            args=(scoring_id, project_path, session_name, session_id, model_config, device, append_to_current, current_labeling_name)
        )
        scoring_thread.daemon = True
        scoring_thread.start()
        
        logger.info(f"started {device_label} scoring thread for {scoring_id}")
        return scoring_id
    
    def score_range_async_with_model(self, project_path, session_name, session_id, model_config, start_ns, end_ns, device='cpu', append_to_current=True, current_labeling_name=None):
        """start async scoring with specific model configuration and device"""
        scoring_id = str(uuid.uuid4())
        device_label = device.upper()

        # Initialize status tracking
        self.scoring_status[scoring_id] = {
            'status': 'running',
            'session_id': session_id,
            'session_name': session_name,
            'model_id': model_config['id'],
            'model_name': model_config['name'],
            'device': device,
            'start_time': time.time(),
            'error': None
        }
        
        # Start async processing using unified worker
        scoring_thread = threading.Thread(
            target=self._score_range_worker,  
            args=(scoring_id, project_path, session_name, session_id, model_config, start_ns, end_ns, device, append_to_current, current_labeling_name)
        )
        scoring_thread.daemon = True
        scoring_thread.start()
        
        logger.info(f"started {device_label} scoring thread for {scoring_id}")
        return scoring_id

    def _validate_model_files(self, model_config):
        """Validate that model files exist before starting scoring"""
        model_dir = self._get_model_dir()
        py_file_path = os.path.join(model_dir, model_config['py_filename'])
        pt_file_path = os.path.join(model_dir, model_config['pt_filename'])
        
        if not os.path.exists(py_file_path):
            raise DatabaseError(f'model python file not found: {py_file_path}')
            
        if not os.path.exists(pt_file_path):
            raise DatabaseError(f'model weights file not found: {pt_file_path}')

    # =======================
    # Utility Methods
    # =======================

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
            return self.score_session_async_with_model(project_path, session_name, session_id, model_config, device='cpu')
            
        except Exception as e:
            logger.error(f"error in backward compatibility scoring: {e}")
            raise DatabaseError(f'scoring failed: {str(e)}')
    
    def get_scoring_status(self, scoring_id):
        """get the status of a scoring operation"""
        return self.scoring_status.get(scoring_id, {'status': 'not_found'})
    
    def _get_model_dir(self):
        """get the model directory path"""
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