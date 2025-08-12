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

controller = None

def init_controller(raw_dataset_service):
    global controller
    controller = RawDatasetController(raw_dataset_service=raw_dataset_service)