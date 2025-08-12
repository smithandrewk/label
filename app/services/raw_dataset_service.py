import os
import json
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Any
from app.repositories.raw_dataset_repository import RawDatasetRepository
from app.exceptions import DatabaseError
from app.logging_config import get_logger

logger = get_logger(__name__)

class RawDatasetService:
    def __init__(self, raw_dataset_repository=None):
        if raw_dataset_repository:
            self.raw_dataset_repo = raw_dataset_repository
        else:
            # Fallback for backward compatibility
            from app.services.database_service import get_db_connection
            self.raw_dataset_repo = RawDatasetRepository(get_db_connection=get_db_connection)
    
    def upload_raw_dataset(self, source_path: str, dataset_name: str, description: str = None, 
                          raw_data_dir: str = None) -> Dict[str, Any]:
        """
        Upload a raw dataset, handling deduplication and storage
        
        Args:
            source_path: Path to the source dataset directory
            dataset_name: Name for the dataset
            description: Optional description
            raw_data_dir: Base directory for storing raw data (defaults to DATA_DIR/raw_datasets)
            
        Returns:
            dict: Dataset creation result with metadata
        """
        if not os.path.exists(source_path):
            raise DatabaseError(f"Source path does not exist: {source_path}")
        
        if not os.path.isdir(source_path):
            raise DatabaseError(f"Source path is not a directory: {source_path}")
        
        # Set up raw data storage directory
        if raw_data_dir is None:
            raw_data_dir = os.path.expanduser(os.getenv('DATA_DIR', '~/.delta/data'))
        
        # raw_datasets_dir = os.path.join(raw_data_dir, 'raw_datasets')
        os.makedirs(raw_data_dir, exist_ok=True)
        
        # Calculate hash for deduplication
        logger.info(f"Calculating hash for dataset at {source_path}")
        dataset_hash = self.raw_dataset_repo.calculate_directory_hash(source_path)
        
        # Check if dataset already exists
        existing_dataset = self.raw_dataset_repo.find_by_hash(dataset_hash)
        if existing_dataset:
            logger.info(f"Dataset with hash {dataset_hash} already exists: {existing_dataset['dataset_name']}")
            return {
                'dataset_id': existing_dataset['dataset_id'],
                'dataset_name': existing_dataset['dataset_name'],
                'file_path': existing_dataset['file_path'],
                'duplicate': True,
                'existing_dataset': existing_dataset
            }
        
        # Calculate metadata
        file_size_bytes = self.raw_dataset_repo.calculate_directory_size(source_path)
        session_count = self.raw_dataset_repo.count_sessions_in_directory(source_path)
        
        # Create unique storage path
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        storage_name = f"{dataset_name}_{timestamp}_{dataset_hash[:8]}"
        storage_path = os.path.join(raw_data_dir, storage_name)
        
        try:
            # Copy dataset to storage location
            logger.info(f"Copying dataset from {source_path} to {storage_path}")
            shutil.copytree(source_path, storage_path)
            
            # Create database record
            dataset_result = self.raw_dataset_repo.create_dataset(
                dataset_name=dataset_name,
                dataset_hash=dataset_hash,
                file_path=storage_path,
                file_size_bytes=file_size_bytes,
                session_count=session_count,
                description=description,
                metadata={
                    'upload_timestamp': timestamp,
                    'original_source': source_path,
                    'storage_name': storage_name
                }
            )
            
            # Create raw session records
            self._create_raw_session_records(dataset_result['dataset_id'], storage_path)
            
            logger.info(f"Successfully uploaded raw dataset: {dataset_name} (ID: {dataset_result['dataset_id']})")
            
            return {
                'dataset_id': dataset_result['dataset_id'],
                'dataset_name': dataset_result['dataset_name'],
                'file_path': storage_path,
                'duplicate': False,
                'file_size_bytes': file_size_bytes,
                'session_count': session_count,
                'dataset_hash': dataset_hash
            }
            
        except Exception as e:
            # Clean up on failure
            if os.path.exists(storage_path):
                shutil.rmtree(storage_path)
            logger.error(f"Failed to upload raw dataset: {e}")
            raise DatabaseError(f'Failed to upload raw dataset: {str(e)}')
    
    def _create_raw_session_records(self, dataset_id: int, dataset_path: str) -> None:
        """Create records for all original sessions in the raw dataset"""
        if not os.path.exists(dataset_path):
            return
        
        for item in os.listdir(dataset_path):
            item_path = os.path.join(dataset_path, item)
            if os.path.isdir(item_path):
                # This is a session directory
                session_name = item
                relative_session_path = os.path.join(dataset_path, session_name)
                
                # Look for labels.json file
                labels_json_path = os.path.join(item_path, 'labels.json')
                original_labels_json = None
                if os.path.exists(labels_json_path):
                    try:
                        with open(labels_json_path, 'r') as f:
                            original_labels_json = f.read()
                    except Exception as e:
                        logger.warning(f"Could not read labels.json for session {session_name}: {e}")
                
                # Count files in session directory
                file_count = 0
                for root, dirs, files in os.walk(item_path):
                    file_count += len(files)
                
                # Create raw session record
                self.raw_dataset_repo.create_raw_session(
                    dataset_id=dataset_id,
                    session_name=session_name,
                    session_path=relative_session_path,
                    original_labels_json=original_labels_json,
                    file_count=file_count
                )
                
                logger.debug(f"Created raw session record: {session_name} ({file_count} files)")
    
    def list_raw_datasets(self) -> List[Dict[str, Any]]:
        """List all available raw datasets with summary information"""
        return self.raw_dataset_repo.list_all()
    
    def get_raw_dataset(self, dataset_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific raw dataset"""
        dataset = self.raw_dataset_repo.find_by_id(dataset_id)
        if not dataset:
            return None
        
        # Add session information
        sessions = self.raw_dataset_repo.get_dataset_sessions(dataset_id)
        dataset['sessions'] = sessions
        
        return dataset
    
    def delete_raw_dataset(self, dataset_id: int) -> Dict[str, Any]:
        """Delete a raw dataset and its files (if not referenced by projects)"""
        # Get dataset info before deletion
        dataset = self.raw_dataset_repo.find_by_id(dataset_id)
        if not dataset:
            raise DatabaseError('Raw dataset not found')
        
        dataset_path = dataset['file_path']
        
        # Delete database record (this will fail if referenced by projects)
        success = self.raw_dataset_repo.delete(dataset_id)
        
        if success:
            # Delete files from filesystem
            directory_deleted = False
            if dataset_path and os.path.exists(dataset_path):
                try:
                    shutil.rmtree(dataset_path)
                    directory_deleted = True
                    logger.info(f"Deleted raw dataset directory: {dataset_path}")
                except Exception as e:
                    logger.warning(f"Could not delete dataset directory {dataset_path}: {e}")
        
        return {
            'dataset_id': dataset_id,
            'dataset_name': dataset['dataset_name'],
            'directory_deleted': directory_deleted,
            'directory_path': dataset_path
        }
    
    def discover_sessions_in_dataset(self, dataset_path: str) -> List[Dict[str, Any]]:
        """
        Discover all sessions in a raw dataset directory
        Compatible with existing project upload session discovery logic
        """
        sessions = []
        
        if not os.path.exists(dataset_path):
            logger.warning(f"Dataset path does not exist: {dataset_path}")
            return sessions
        
        for item in os.listdir(dataset_path):
            item_path = os.path.join(dataset_path, item)
            if os.path.isdir(item_path):
                session_info = {
                    'name': item,
                    'path': item_path
                }
                
                # Look for labels.json to get original bout information
                labels_json_path = os.path.join(item_path, 'labels.json')
                if os.path.exists(labels_json_path):
                    try:
                        with open(labels_json_path, 'r') as f:
                            labels_data = json.load(f)
                            session_info['original_labels'] = labels_data
                    except Exception as e:
                        logger.warning(f"Could not parse labels.json for session {item}: {e}")
                        session_info['original_labels'] = []
                else:
                    session_info['original_labels'] = []
                
                sessions.append(session_info)
        
        logger.info(f"Discovered {len(sessions)} sessions in dataset {dataset_path}")
        return sessions
    
    def link_project_to_dataset(self, project_id: int, dataset_id: int) -> Dict[str, Any]:
        """Create a link between a project and a raw dataset"""
        return self.raw_dataset_repo.link_project_to_dataset(project_id, dataset_id)
    
    def get_project_datasets(self, project_id: int) -> List[Dict[str, Any]]:
        """Get all raw datasets linked to a project"""
        return self.raw_dataset_repo.get_project_datasets(project_id)
    
    def validate_dataset_path(self, dataset_path: str) -> Dict[str, Any]:
        """Validate that a path contains a valid dataset structure"""
        if not os.path.exists(dataset_path):
            return {
                'valid': False,
                'error': f'Path does not exist: {dataset_path}'
            }
        
        if not os.path.isdir(dataset_path):
            return {
                'valid': False,
                'error': f'Path is not a directory: {dataset_path}'
            }
        
        # Check if directory contains session subdirectories
        session_dirs = []
        for item in os.listdir(dataset_path):
            item_path = os.path.join(dataset_path, item)
            if os.path.isdir(item_path):
                session_dirs.append(item)
        
        if len(session_dirs) == 0:
            return {
                'valid': False,
                'error': 'Directory contains no session subdirectories'
            }
        
        return {
            'valid': True,
            'session_count': len(session_dirs),
            'sessions': session_dirs
        }
    
    def scan_and_register_existing_datasets(self, raw_data_dir: str = None) -> Dict[str, Any]:
        """
        Scan the raw_datasets directory for unregistered datasets and register them
        
        Args:
            raw_data_dir: Base directory for raw data (defaults to DATA_DIR/raw_datasets)
            
        Returns:
            dict: Results of the scan and registration process
        """
        if raw_data_dir is None:
            raw_data_dir = os.path.expanduser(os.getenv('DATA_DIR', '~/.delta/data'))
        
        raw_datasets_dir = os.path.join(raw_data_dir, 'raw_datasets')
        logger.info(f"Scan called with raw_data_dir={raw_data_dir}, computed raw_datasets_dir={raw_datasets_dir}")
        
        if not os.path.exists(raw_datasets_dir):
            return {
                'datasets_found': 0,
                'datasets_registered': 0,
                'datasets_skipped': 0,
                'registered_datasets': [],
                'errors': [],
                'message': f'Raw datasets directory does not exist: {raw_datasets_dir}'
            }
        
        datasets_found = 0
        datasets_registered = 0
        datasets_skipped = 0
        errors = []
        registered_datasets = []
        
        logger.info(f"Scanning for unregistered datasets in: {raw_datasets_dir}")
        
        # Get all existing dataset hashes to avoid duplicates
        existing_datasets = self.raw_dataset_repo.list_all()
        existing_hashes = {d['dataset_hash'] for d in existing_datasets}
        logger.info(f"Found {len(existing_datasets)} existing datasets with hashes: {list(existing_hashes)}")
        
        # List directory contents for debugging
        dir_contents = os.listdir(raw_datasets_dir)
        logger.info(f"Directory contents: {dir_contents}")
        
        # Scan directory for potential dataset directories
        for item in os.listdir(raw_datasets_dir):
            item_path = os.path.join(raw_datasets_dir, item)
            
            # Skip files, only process directories
            if not os.path.isdir(item_path):
                logger.debug(f"Skipping non-directory: {item}")
                continue
                
            datasets_found += 1
            logger.info(f"Processing directory {datasets_found}: {item}")
            
            try:
                # Validate that this looks like a dataset
                validation = self.validate_dataset_path(item_path)
                if not validation['valid']:
                    errors.append(f"Skipping {item}: {validation['error']}")
                    continue
                
                # Calculate hash to check if already registered
                dataset_hash = self.raw_dataset_repo.calculate_directory_hash(item_path)
                
                if dataset_hash in existing_hashes:
                    logger.debug(f"Dataset {item} already registered (hash: {dataset_hash[:8]})")
                    datasets_skipped += 1
                    continue
                
                # Extract dataset name from directory name (remove timestamp and hash suffix)
                # Expected format: datasetname_YYYYMMDD_HHMMSS_hashprefix
                parts = item.split('_')
                if len(parts) >= 4:
                    # Remove last 3 parts (date, time, hash)
                    dataset_name = '_'.join(parts[:-3])
                else:
                    # Fallback: use directory name as dataset name
                    dataset_name = item
                
                # Calculate metadata
                file_size_bytes = self.raw_dataset_repo.calculate_directory_size(item_path)
                session_count = self.raw_dataset_repo.count_sessions_in_directory(item_path)
                
                # Register the dataset
                dataset_result = self.raw_dataset_repo.create_dataset(
                    dataset_name=dataset_name,
                    dataset_hash=dataset_hash,
                    file_path=item_path,
                    file_size_bytes=file_size_bytes,
                    session_count=session_count,
                    description=f"Auto-registered from existing directory: {item}",
                    metadata={
                        'auto_registered': True,
                        'scan_timestamp': datetime.now().isoformat(),
                        'original_directory': item
                    }
                )
                
                # Create raw session records
                self._create_raw_session_records(dataset_result['dataset_id'], item_path)
                
                datasets_registered += 1
                registered_datasets.append({
                    'dataset_id': dataset_result['dataset_id'],
                    'dataset_name': dataset_name,
                    'path': item_path,
                    'hash': dataset_hash,
                    'sessions': session_count,
                    'size_bytes': file_size_bytes
                })
                
                logger.info(f"Registered dataset: {dataset_name} (ID: {dataset_result['dataset_id']}, sessions: {session_count})")
                
            except Exception as e:
                error_msg = f"Failed to register {item}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        result = {
            'datasets_found': datasets_found,
            'datasets_registered': datasets_registered, 
            'datasets_skipped': datasets_skipped,
            'registered_datasets': registered_datasets,
            'errors': errors,
            'message': f'Scan complete: {datasets_registered} registered, {datasets_skipped} skipped, {len(errors)} errors'
        }
        
        logger.info(f"Dataset scan complete: {result['message']}")
        return result