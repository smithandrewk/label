import os
import json
import hashlib
from typing import List, Dict, Optional, Any
from app.repositories.base_repository import BaseRepository
from app.exceptions import DatabaseError
from app.logging_config import get_logger

logger = get_logger(__name__)

class RawDatasetRepository(BaseRepository):
    def __init__(self):
        super().__init__()
    
    def create_dataset(self, dataset_name: str, dataset_hash: str, file_path: str, 
                      file_size_bytes: int, session_count: int, description: str = None, 
                      metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new raw dataset record"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO raw_datasets (dataset_name, dataset_hash, file_path, file_size_bytes, 
                                            session_count, description, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (dataset_name, dataset_hash, file_path, file_size_bytes, session_count, 
                     description, json.dumps(metadata) if metadata else None))
                
                dataset_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Created raw dataset: {dataset_name} with ID {dataset_id}")
                return {
                    'dataset_id': dataset_id,
                    'dataset_name': dataset_name,
                    'dataset_hash': dataset_hash,
                    'file_path': file_path
                }
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating raw dataset: {e}")
            raise DatabaseError(f'Failed to create raw dataset: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    def find_by_hash(self, dataset_hash: str) -> Optional[Dict[str, Any]]:
        """Find a dataset by its hash (for deduplication)"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT dataset_id, dataset_name, dataset_hash, file_path, upload_timestamp,
                           file_size_bytes, session_count, description, metadata
                    FROM raw_datasets 
                    WHERE dataset_hash = %s
                """, (dataset_hash,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'dataset_id': result[0],
                        'dataset_name': result[1],
                        'dataset_hash': result[2],
                        'file_path': result[3],
                        'upload_timestamp': result[4],
                        'file_size_bytes': result[5],
                        'session_count': result[6],
                        'description': result[7],
                        'metadata': json.loads(result[8]) if result[8] else {}
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error finding dataset by hash: {e}")
            raise DatabaseError(f'Failed to find dataset: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    def find_by_id(self, dataset_id: int) -> Optional[Dict[str, Any]]:
        """Find a dataset by its ID"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT dataset_id, dataset_name, dataset_hash, file_path, upload_timestamp,
                           file_size_bytes, session_count, description, metadata
                    FROM raw_datasets 
                    WHERE dataset_id = %s
                """, (dataset_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'dataset_id': result[0],
                        'dataset_name': result[1],
                        'dataset_hash': result[2],
                        'file_path': result[3],
                        'upload_timestamp': result[4],
                        'file_size_bytes': result[5],
                        'session_count': result[6],
                        'description': result[7],
                        'metadata': json.loads(result[8]) if result[8] else {}
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error finding dataset by ID: {e}")
            raise DatabaseError(f'Failed to find dataset: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    def list_all(self) -> List[Dict[str, Any]]:
        """List all raw datasets with summary information"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT rd.dataset_id, rd.dataset_name, rd.dataset_hash, rd.file_path, 
                           rd.upload_timestamp, rd.file_size_bytes, rd.session_count, 
                           rd.description, rd.metadata,
                           COUNT(DISTINCT pdr.project_id) as project_count
                    FROM raw_datasets rd
                    LEFT JOIN project_dataset_refs pdr ON rd.dataset_id = pdr.dataset_id
                    GROUP BY rd.dataset_id
                    ORDER BY rd.upload_timestamp DESC
                """)
                
                results = cursor.fetchall()
                datasets = []
                
                for result in results:
                    datasets.append({
                        'dataset_id': result[0],
                        'dataset_name': result[1],
                        'dataset_hash': result[2],
                        'file_path': result[3],
                        'upload_timestamp': result[4],
                        'file_size_bytes': result[5],
                        'session_count': result[6],
                        'description': result[7],
                        'metadata': json.loads(result[8]) if result[8] else {},
                        'project_count': result[9]
                    })
                
                return datasets
                
        except Exception as e:
            logger.error(f"Error listing datasets: {e}")
            raise DatabaseError(f'Failed to list datasets: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    def delete(self, dataset_id: int) -> bool:
        """Delete a raw dataset (will fail if referenced by projects)"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        try:
            with conn.cursor() as cursor:
                # Check if dataset is referenced by any projects
                cursor.execute("""
                    SELECT COUNT(*) FROM project_dataset_refs WHERE dataset_id = %s
                """, (dataset_id,))
                
                ref_count = cursor.fetchone()[0]
                if ref_count > 0:
                    raise DatabaseError(f'Cannot delete dataset: referenced by {ref_count} project(s)')
                
                cursor.execute("DELETE FROM raw_datasets WHERE dataset_id = %s", (dataset_id,))
                deleted = cursor.rowcount > 0
                conn.commit()
                
                if deleted:
                    logger.info(f"Deleted raw dataset with ID {dataset_id}")
                
                return deleted
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting dataset: {e}")
            raise DatabaseError(f'Failed to delete dataset: {str(e)}')
        finally:
            cursor.close()
            conn.close()

    def create_raw_session(self, dataset_id: int, session_name: str, session_path: str,
                          original_labels_json: str = None, file_count: int = 0) -> Dict[str, Any]:
        """Create a raw dataset session record"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO raw_dataset_sessions (dataset_id, session_name, session_path, 
                                                    original_labels_json, file_count)
                    VALUES (%s, %s, %s, %s, %s)
                """, (dataset_id, session_name, session_path, original_labels_json, file_count))
                
                raw_session_id = cursor.lastrowid
                conn.commit()
                
                return {
                    'raw_session_id': raw_session_id,
                    'dataset_id': dataset_id,
                    'session_name': session_name,
                    'session_path': session_path
                }
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating raw session: {e}")
            raise DatabaseError(f'Failed to create raw session: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    def get_dataset_sessions(self, dataset_id: int) -> List[Dict[str, Any]]:
        """Get all original sessions for a raw dataset"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT raw_session_id, session_name, session_path, original_labels_json, file_count
                    FROM raw_dataset_sessions
                    WHERE dataset_id = %s
                    ORDER BY session_name
                """, (dataset_id,))
                
                results = cursor.fetchall()
                sessions = []
                
                for result in results:
                    sessions.append({
                        'raw_session_id': result[0],
                        'session_name': result[1],
                        'session_path': result[2],
                        'original_labels_json': result[3],
                        'file_count': result[4]
                    })
                
                return sessions
                
        except Exception as e:
            logger.error(f"Error getting dataset sessions: {e}")
            raise DatabaseError(f'Failed to get dataset sessions: {str(e)}')
        finally:
            cursor.close()
            conn.close()

    def link_project_to_dataset(self, project_id: int, dataset_id: int) -> Dict[str, Any]:
        """Create a link between a project and a raw dataset"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO project_dataset_refs (project_id, dataset_id)
                    VALUES (%s, %s)
                """, (project_id, dataset_id))
                
                ref_id = cursor.lastrowid
                conn.commit()
                
                return {
                    'ref_id': ref_id,
                    'project_id': project_id,
                    'dataset_id': dataset_id
                }
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error linking project to dataset: {e}")
            raise DatabaseError(f'Failed to link project to dataset: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    def get_project_datasets(self, project_id: int) -> List[Dict[str, Any]]:
        """Get all raw datasets linked to a project"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT rd.dataset_id, rd.dataset_name, rd.dataset_hash, rd.file_path,
                           rd.upload_timestamp, rd.file_size_bytes, rd.session_count,
                           rd.description, rd.metadata
                    FROM raw_datasets rd
                    JOIN project_dataset_refs pdr ON rd.dataset_id = pdr.dataset_id
                    WHERE pdr.project_id = %s
                    ORDER BY rd.dataset_name
                """, (project_id,))
                
                results = cursor.fetchall()
                datasets = []
                
                for result in results:
                    datasets.append({
                        'dataset_id': result[0],
                        'dataset_name': result[1],
                        'dataset_hash': result[2],
                        'file_path': result[3],
                        'upload_timestamp': result[4],
                        'file_size_bytes': result[5],
                        'session_count': result[6],
                        'description': result[7],
                        'metadata': json.loads(result[8]) if result[8] else {}
                    })
                
                return datasets
                
        except Exception as e:
            logger.error(f"Error getting project datasets: {e}")
            raise DatabaseError(f'Failed to get project datasets: {str(e)}')
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def calculate_directory_hash(directory_path: str) -> str:
        """Calculate SHA256 hash of directory contents for deduplication"""
        if not os.path.exists(directory_path):
            raise ValueError(f"Directory does not exist: {directory_path}")
        
        hash_sha256 = hashlib.sha256()
        
        # Walk through directory and hash all file contents and paths
        for root, dirs, files in os.walk(directory_path):
            # Sort to ensure consistent ordering
            dirs.sort()
            files.sort()
            
            for filename in files:
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, directory_path)
                
                # Hash the relative path
                hash_sha256.update(relative_path.encode('utf-8'))
                
                # Hash the file contents
                try:
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hash_sha256.update(chunk)
                except (IOError, OSError) as e:
                    logger.warning(f"Could not read file {file_path}: {e}")
                    continue
        
        return hash_sha256.hexdigest()

    @staticmethod
    def calculate_directory_size(directory_path: str) -> int:
        """Calculate total size of directory in bytes"""
        total_size = 0
        
        for root, dirs, files in os.walk(directory_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                try:
                    total_size += os.path.getsize(file_path)
                except (IOError, OSError) as e:
                    logger.warning(f"Could not get size of file {file_path}: {e}")
                    continue
        
        return total_size

    @staticmethod
    def count_sessions_in_directory(directory_path: str) -> int:
        """Count the number of session directories in a dataset"""
        if not os.path.exists(directory_path):
            return 0
        
        session_count = 0
        for item in os.listdir(directory_path):
            item_path = os.path.join(directory_path, item)
            if os.path.isdir(item_path):
                session_count += 1
        
        return session_count