from .base_repository import BaseRepository
from app.exceptions import DatabaseError

class ModelRepository(BaseRepository):
    """Repository for model-related database operations"""
    
    def get_all_active(self):
        """Get all active models"""
        query = """
            SELECT model_id, name, description, py_filename, pt_filename, 
                   class_name, model_settings, is_active, created_at, updated_at
            FROM models 
            WHERE is_active = 1
            ORDER BY created_at DESC
        """
        return self._execute_query(query, fetch_all=True)
    
    def get_all(self):
        """Get all models including inactive ones"""
        query = """
            SELECT model_id, name, description, py_filename, pt_filename, 
                   class_name, model_settings, is_active, created_at, updated_at
            FROM models 
            ORDER BY created_at DESC
        """
        return self._execute_query(query, fetch_all=True)
    
    def find_by_id(self, model_id):
        """Find model by ID"""
        query = """
            SELECT model_id, name, description, py_filename, pt_filename, 
                   class_name, model_settings, is_active, created_at, updated_at
            FROM models 
            WHERE model_id = %s
        """
        return self._execute_query(query, (model_id,), fetch_one=True)
    
    def create(self, model_data):
        """Create a new model"""
        import json
        
        # Set default model settings if not provided
        default_settings = {
            "threshold": 0.5,
            "min_bout_duration_ns": 250000000  # 0.25 seconds in nanoseconds
        }
        model_settings = model_data.get('model_settings', default_settings)
        
        query = """
            INSERT INTO models (name, description, py_filename, pt_filename, class_name, model_settings, is_active) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, (
                model_data['name'],
                model_data.get('description', ''),
                model_data['py_filename'],
                model_data['pt_filename'],
                model_data['class_name'],
                json.dumps(model_settings) if model_settings else None,
                model_data.get('is_active', True)
            ))
            conn.commit()
            model_id = cursor.lastrowid
            
            # return the created model
            return self.find_by_id(model_id)
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f'failed to create model: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    def update(self, model_id, model_data):
        """Update an existing model"""
        import json
        
        # build dynamic update query based on provided fields
        update_fields = []
        params = []
        
        updatable_fields = ['name', 'description', 'py_filename', 'pt_filename', 'class_name', 'model_settings', 'is_active']
        for field in updatable_fields:
            if field in model_data:
                update_fields.append(f"{field} = %s")
                # Handle JSON serialization for model_settings
                if field == 'model_settings' and model_data[field] is not None:
                    params.append(json.dumps(model_data[field]))
                else:
                    params.append(model_data[field])
        
        if not update_fields:
            raise DatabaseError('no fields to update')
        
        params.append(model_id)
        query = f"""
            UPDATE models 
            SET {', '.join(update_fields)}
            WHERE model_id = %s
        """
        
        rows_affected = self._execute_query(query, params, commit=True)
        
        if rows_affected == 0:
            raise DatabaseError('model not found')
        
        return self.find_by_id(model_id)
    
    def delete(self, model_id):
        """Soft delete a model by setting is_active to 0"""
        query = "UPDATE models SET is_active = 0 WHERE model_id = %s"
        rows_affected = self._execute_query(query, (model_id,), commit=True)
        
        if rows_affected == 0:
            raise DatabaseError('model not found')
        
        return True
    
    def hard_delete(self, model_id):
        """Hard delete a model (permanently remove from database)"""
        query = "DELETE FROM models WHERE model_id = %s"
        rows_affected = self._execute_query(query, (model_id,), commit=True)
        
        if rows_affected == 0:
            raise DatabaseError('model not found')
        
        return True
    
    def find_by_name(self, name):
        """Find model by name"""
        query = """
            SELECT model_id, name, description, py_filename, pt_filename, 
                   class_name, model_settings, is_active, created_at, updated_at
            FROM models 
            WHERE name = %s AND is_active = 1
        """
        return self._execute_query(query, (name,), fetch_one=True)
    
    def count_active(self):
        """Count active models"""
        query = "SELECT COUNT(*) as count FROM models WHERE is_active = 1"
        result = self._execute_query(query, fetch_one=True)
        return result['count'] if result else 0