from flask import Blueprint, request, jsonify
import os
import traceback
from app.exceptions import DatabaseError
from app.logging_config import get_logger
from app.services.raw_dataset_service import RawDatasetService

logger = get_logger(__name__)

RAW_DATA_DIR = os.getenv('RAW_DATA_DIR', os.path.expanduser('~/.delta/data/raw_datasets'))

raw_datasets_bp = Blueprint('raw_datasets', __name__)

class RawDatasetController:
    def __init__(self, raw_dataset_service):
        self.raw_dataset_service: RawDatasetService = raw_dataset_service
    
    def upload_raw_dataset(self):
        """Upload a new raw dataset"""
        try:
            dataset_name = request.form.get('name')
            source_path = request.form.get('sourcePath')
            description = request.form.get('description', '')
            
            if not all([dataset_name, source_path]):
                return jsonify({'error': 'Missing required fields: name or sourcePath'}), 400
            
            # Validate source path
            validation = self.raw_dataset_service.validate_dataset_path(source_path)
            if not validation['valid']:
                return jsonify({'error': validation['error']}), 400
            
            result = self.raw_dataset_service.upload_raw_dataset(
                source_path=source_path,
                dataset_name=dataset_name,
                description=description,
                raw_data_dir=RAW_DATA_DIR
            )
            
            logger.info(f"Raw dataset upload result: {result}")
            
            if result.get('duplicate', False):
                return jsonify({
                    'message': 'Raw dataset already exists (duplicate detected)',
                    'dataset_id': result['dataset_id'],
                    'dataset_name': result['dataset_name'],
                    'duplicate': True,
                    'existing_dataset': result['existing_dataset']
                })
            else:
                return jsonify({
                    'message': 'Raw dataset uploaded successfully',
                    'dataset_id': result['dataset_id'],
                    'dataset_name': result['dataset_name'],
                    'file_path': result['file_path'],
                    'file_size_bytes': result['file_size_bytes'],
                    'session_count': result['session_count'],
                    'dataset_hash': result['dataset_hash'],
                    'duplicate': False
                })
            
        except Exception as e:
            logger.error(f"Error in upload_raw_dataset: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': f'Upload failed: {str(e)}'}), 500
    
    def list_raw_datasets(self):
        """List all available raw datasets"""
        try:
            datasets = self.raw_dataset_service.list_raw_datasets()
            return jsonify(datasets)
            
        except Exception as e:
            logger.error(f"Error in list_raw_datasets: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500
    
    def get_raw_dataset(self, dataset_id):
        """Get detailed information about a specific raw dataset"""
        try:
            dataset = self.raw_dataset_service.get_raw_dataset(dataset_id)
            if not dataset:
                return jsonify({'error': 'Raw dataset not found'}), 404
            
            return jsonify(dataset)
            
        except Exception as e:
            logger.error(f"Error in get_raw_dataset: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500
    
    def delete_raw_dataset(self, dataset_id):
        """Delete a raw dataset"""
        try:
            result = self.raw_dataset_service.delete_raw_dataset(dataset_id)
            
            return jsonify({
                'message': 'Raw dataset deleted successfully',
                'dataset_id': result['dataset_id'],
                'dataset_name': result['dataset_name'],
                'directory_deleted': result['directory_deleted'],
                'directory_path': result['directory_path']
            })
            
        except DatabaseError as e:
            if 'not found' in str(e):
                return jsonify({'error': str(e)}), 404
            elif 'referenced by' in str(e):
                return jsonify({'error': str(e)}), 409  # Conflict - cannot delete
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            logger.error(f"Error deleting raw dataset: {e}")
            return jsonify({'error': f'Failed to delete raw dataset: {str(e)}'}), 500
    
    def validate_dataset_path(self):
        """Validate a dataset path before upload"""
        try:
            source_path = request.json.get('sourcePath')
            if not source_path:
                return jsonify({'error': 'Missing sourcePath'}), 400
            
            validation = self.raw_dataset_service.validate_dataset_path(source_path)
            return jsonify(validation)
            
        except Exception as e:
            logger.error(f"Error validating dataset path: {e}")
            return jsonify({'error': str(e)}), 500
    
    def preview_dataset(self):
        """Preview a dataset structure before upload"""
        try:
            source_path = request.json.get('sourcePath')
            if not source_path:
                return jsonify({'error': 'Missing sourcePath'}), 400
            
            # Validate path first
            validation = self.raw_dataset_service.validate_dataset_path(source_path)
            if not validation['valid']:
                return jsonify(validation), 400
            
            # Get session information
            sessions = self.raw_dataset_service.discover_sessions_in_dataset(source_path)
            
            # Calculate basic metadata
            from app.repositories.raw_dataset_repository import RawDatasetRepository
            file_size_bytes = RawDatasetRepository.calculate_directory_size(source_path)
            
            return jsonify({
                'valid': True,
                'sessions': sessions,
                'session_count': len(sessions),
                'file_size_bytes': file_size_bytes,
                'estimated_hash': 'calculating...'  # Could add hash calculation if needed
            })
            
        except Exception as e:
            logger.error(f"Error previewing dataset: {e}")
            return jsonify({'error': str(e)}), 500
    
    def scan_and_register_datasets(self):
        """Scan the raw datasets directory for unregistered datasets and register them"""
        try:
            # Optionally allow specifying a custom directory
            custom_dir = request.json.get('raw_data_dir') if request.is_json else None
            
            logger.info(f"Starting dataset scan and register process")
            result = self.raw_dataset_service.scan_and_register_existing_datasets(custom_dir)
            
            return jsonify({
                'message': result['message'],
                'datasets_found': result['datasets_found'],
                'datasets_registered': result['datasets_registered'],
                'datasets_skipped': result['datasets_skipped'],
                'registered_datasets': result['registered_datasets'],
                'errors': result['errors']
            })
            
        except Exception as e:
            logger.error(f"Error in scan_and_register_datasets: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': f'Scan and register failed: {str(e)}'}), 500
    
    def bulk_scan_datasets(self):
        """Scan a parent directory for multiple potential datasets"""
        try:
            parent_path = request.json.get('parent_path')
            if not parent_path:
                return jsonify({'error': 'Missing parent_path'}), 400
            
            # Validate parent path exists
            if not os.path.exists(parent_path):
                return jsonify({'error': 'Parent path does not exist'}), 400
                
            if not os.path.isdir(parent_path):
                return jsonify({'error': 'Parent path is not a directory'}), 400
            
            logger.info(f"Bulk scanning parent directory: {parent_path}")
            
            # Get all subdirectories that could be datasets
            potential_datasets = []
            for item in os.listdir(parent_path):
                item_path = os.path.join(parent_path, item)
                if os.path.isdir(item_path):
                    # Check if this directory looks like a dataset
                    validation = self.raw_dataset_service.validate_dataset_path(item_path)
                    
                    dataset_info = {
                        'name': item,  # Use directory name as dataset name
                        'path': item_path,
                        'valid': validation['valid'],
                        'error': validation.get('error', None)
                    }
                    
                    if validation['valid']:
                        # Get additional info for valid datasets
                        try:
                            sessions = self.raw_dataset_service.discover_sessions_in_dataset(item_path)
                            from app.repositories.raw_dataset_repository import RawDatasetRepository
                            file_size_bytes = RawDatasetRepository.calculate_directory_size(item_path)
                            
                            dataset_info.update({
                                'sessions': sessions,
                                'session_count': len(sessions),
                                'file_size_bytes': file_size_bytes,
                            })
                        except Exception as e:
                            logger.warning(f"Error getting dataset info for {item_path}: {e}")
                            dataset_info['error'] = str(e)
                            dataset_info['valid'] = False
                    
                    potential_datasets.append(dataset_info)
            
            # Sort by name
            potential_datasets.sort(key=lambda x: x['name'])
            
            return jsonify({
                'parent_path': parent_path,
                'datasets': potential_datasets,
                'total_found': len(potential_datasets),
                'valid_datasets': sum(1 for d in potential_datasets if d['valid'])
            })
            
        except Exception as e:
            logger.error(f"Error in bulk_scan_datasets: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': f'Bulk scan failed: {str(e)}'}), 500
    
    def bulk_upload_datasets(self):
        """Upload multiple datasets from a bulk scan"""
        try:
            datasets_data = request.json.get('datasets', [])
            if not datasets_data:
                return jsonify({'error': 'No datasets provided'}), 400
            
            results = {
                'successful': [],
                'failed': [],
                'duplicates': [],
                'total_processed': len(datasets_data)
            }
            
            for dataset_data in datasets_data:
                try:
                    result = self.raw_dataset_service.upload_raw_dataset(
                        source_path=dataset_data['path'],
                        dataset_name=dataset_data['name'],
                        description=dataset_data.get('description', ''),
                        raw_data_dir=RAW_DATA_DIR
                    )
                    
                    if result.get('duplicate', False):
                        results['duplicates'].append({
                            'name': dataset_data['name'],
                            'path': dataset_data['path'],
                            'existing_id': result['dataset_id']
                        })
                    else:
                        results['successful'].append({
                            'name': result['dataset_name'],
                            'id': result['dataset_id'],
                            'path': result['file_path'],
                            'sessions': result['session_count']
                        })
                        
                except Exception as e:
                    logger.error(f"Error uploading dataset {dataset_data['name']}: {e}")
                    results['failed'].append({
                        'name': dataset_data['name'],
                        'path': dataset_data['path'],
                        'error': str(e)
                    })
            
            message_parts = []
            if results['successful']:
                message_parts.append(f"{len(results['successful'])} datasets uploaded successfully")
            if results['duplicates']:
                message_parts.append(f"{len(results['duplicates'])} duplicates skipped")
            if results['failed']:
                message_parts.append(f"{len(results['failed'])} failed")
                
            results['message'] = ', '.join(message_parts)
            
            return jsonify(results)
            
        except Exception as e:
            logger.error(f"Error in bulk_upload_datasets: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({'error': f'Bulk upload failed: {str(e)}'}), 500

# Route definitions
@raw_datasets_bp.route('/api/datasets/upload', methods=['POST'])
def upload_raw_dataset():
    return controller.upload_raw_dataset()

@raw_datasets_bp.route('/api/datasets')
def list_raw_datasets():
    return controller.list_raw_datasets()

@raw_datasets_bp.route('/api/datasets/<int:dataset_id>')
def get_raw_dataset(dataset_id):
    return controller.get_raw_dataset(dataset_id)

@raw_datasets_bp.route('/api/datasets/<int:dataset_id>', methods=['DELETE'])
def delete_raw_dataset(dataset_id):
    return controller.delete_raw_dataset(dataset_id)

@raw_datasets_bp.route('/api/datasets/validate', methods=['POST'])
def validate_dataset_path():
    return controller.validate_dataset_path()

@raw_datasets_bp.route('/api/datasets/preview', methods=['POST'])
def preview_dataset():
    return controller.preview_dataset()

@raw_datasets_bp.route('/api/datasets/scan', methods=['POST'])
def scan_and_register_datasets():
    return controller.scan_and_register_datasets()

@raw_datasets_bp.route('/api/datasets/bulk-scan', methods=['POST'])
def bulk_scan_datasets():
    return controller.bulk_scan_datasets()

@raw_datasets_bp.route('/api/datasets/bulk-upload', methods=['POST'])
def bulk_upload_datasets():
    return controller.bulk_upload_datasets()

controller = None

def init_controller(raw_dataset_service):
    global controller
    controller = RawDatasetController(raw_dataset_service=raw_dataset_service)