from .base_repository import BaseRepository
from app.exceptions import DatabaseError

class ProjectRepository(BaseRepository):
    """Repository for project-related database operations"""
    
    def get_all(self):
        """Get all projects with participant information"""
        query = """
            SELECT p.project_id, p.project_name, p.path, pt.participant_code
            FROM projects p
            JOIN participants pt ON p.participant_id = pt.participant_id
        """
        return self._execute_query(query, fetch_all=True)
    
    def create(self, project_name, participant_id, path):
        """Create a new project"""
        query = """
            INSERT INTO projects (project_name, participant_id, path) 
            VALUES (%s, %s, %s)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, (project_name, participant_id, path))
            conn.commit()
            project_id = cursor.lastrowid
            return {'project_id': project_id}
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f'Failed to insert project: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    def find_by_id(self, project_id):
        """Find project by ID"""
        query = "SELECT * FROM projects WHERE project_id = %s"
        return self._execute_query(query, (project_id,), fetch_one=True)
    
    def find_with_participant(self, project_id):
        """Get detailed project information including participant data"""
        query = """
            SELECT p.project_id, p.project_name, p.path, p.participant_id,
                pt.participant_code
            FROM projects p
            JOIN participants pt ON p.participant_id = pt.participant_id
            WHERE p.project_id = %s
        """
        return self._execute_query(query, (project_id,), fetch_one=True)
    
    def find_by_participant(self, participant_id):
        """Get all projects for a participant"""
        query = "SELECT project_id, project_name, path FROM projects WHERE participant_id = %s"
        return self._execute_query(query, (participant_id,), fetch_all=True)
    
    def delete(self, project_id):
        """Delete a project by ID"""
        query = "DELETE FROM projects WHERE project_id = %s"
        rows_affected = self._execute_query(query, (project_id,), commit=True)
        
        if rows_affected == 0:
            raise DatabaseError('Project not found or already deleted')
        
        return True

    def update_name(self, project_id, new_name):
        """Update a project's name"""
        query = "UPDATE projects SET project_name = %s WHERE project_id = %s"
        rows_affected = self._execute_query(query, (new_name, project_id), commit=True)
        
        if rows_affected == 0:
            raise DatabaseError('Project not found')
        
        return True

    def get_labelings(self, project_id):
        """Get labelings for a specific project"""
        query = """
            SELECT labelings
            FROM projects
            WHERE project_id = %s
        """
        return self._execute_query(query, (project_id,), fetch_all=True)
        
    def update_labelings(self, project_id, label):
        """
        Add a new labeling to a project's labelings list
        
        Args:
            project_id: ID of the project to update
            label: The labeling to add (can be string or dict with name/color)
            
        Returns:
            dict: Updated labelings array
        """
        import json
        
        # First, get the current labelings
        query = """
            SELECT labelings
            FROM projects
            WHERE project_id = %s
        """
        result = self._execute_query(query, (project_id,), fetch_one=True)
        
        if not result:
            raise DatabaseError('Project not found')
            
        # Parse existing labelings or initialize empty array
        labelings = []
        if result.get('labelings'):
            try:
                labelings = json.loads(result['labelings'])
                if not isinstance(labelings, list):
                    labelings = []
            except (json.JSONDecodeError, TypeError):
                labelings = []
        
        # Add the new labeling
        labelings.append(label)
        
        # Update the project with new labelings
        update_query = """
            UPDATE projects
            SET labelings = %s
            WHERE project_id = %s
        """
        rows_affected = self._execute_query(update_query, (json.dumps(labelings), project_id), commit=True)
        
        if rows_affected == 0:
            raise DatabaseError('Failed to update labelings')
            
        return {'status': 'success', 'labelings': labelings}
        
    def update_labeling_color(self, project_id, labeling_name, color):
        """
        Update the color of an existing labeling in a project
        
        Args:
            project_id: ID of the project containing the labeling
            labeling_name: Name of the labeling to update
            color: New color value in hex format
            
        Returns:
            dict: Status and message indicating success or failure
        """
        import json
        
        # First, get the current labelings
        query = """
            SELECT labelings
            FROM projects
            WHERE project_id = %s
        """
        result = self._execute_query(query, (project_id,), fetch_one=True)
        
        if not result or not result.get('labelings'):
            raise DatabaseError('Project not found or no labelings exist')
            
        # Parse the labelings JSON
        labelings = json.loads(result['labelings'])
        updated = False
        
        # Find and update the matching labeling
        for i, labeling in enumerate(labelings):
            # Handle both string type and object type labelings
            if isinstance(labeling, str) and labeling == labeling_name:
                # Convert string labeling to object with color
                labelings[i] = {"name": labeling_name, "color": color}
                updated = True
            elif isinstance(labeling, dict) and labeling.get('name') == labeling_name:
                # Update existing object labeling
                labelings[i]['color'] = color
                updated = True
            # Handle JSON string that's not yet parsed
            elif isinstance(labeling, str) and labeling.startswith('{'):
                try:
                    labeling_obj = json.loads(labeling)
                    if isinstance(labeling_obj, dict) and labeling_obj.get('name') == labeling_name:
                        labeling_obj['color'] = color
                        labelings[i] = labeling_obj
                        updated = True
                except:
                    pass
        
        if not updated:
            raise DatabaseError(f'Labeling "{labeling_name}" not found in project')
            
        # Save the updated labelings back to the database
        update_query = """
            UPDATE projects
            SET labelings = %s
            WHERE project_id = %s
        """
        rows_affected = self._execute_query(update_query, (json.dumps(labelings), project_id), commit=True)
        
        if rows_affected == 0:
            raise DatabaseError('Failed to update labeling color')
            
        return {
            'status': 'success',
            'labeling_name': labeling_name,
            'color': color
        }
        
    def rename_labeling(self, project_id, old_name, new_name):
        """
        Rename an existing labeling in a project
        
        Args:
            project_id: ID of the project containing the labeling
            old_name: Current name of the labeling  
            new_name: New name for the labeling
            
        Returns:
            dict: Status and message indicating success or failure
        """
        import json
        
        # First, get the current labelings
        query = """
            SELECT labelings
            FROM projects
            WHERE project_id = %s
        """
        result = self._execute_query(query, (project_id,), fetch_one=True)
        
        if not result or not result.get('labelings'):
            raise DatabaseError('Project not found or no labelings exist')
            
        # Parse the labelings JSON
        labelings = json.loads(result['labelings'])
        found = False
        print(labelings)
        # Check if new name already exists
        for labeling in labelings:
            if isinstance(labeling, str) and labeling == new_name:
                raise DatabaseError(f'Labeling with name "{new_name}" already exists')
            elif isinstance(labeling, dict) and labeling.get('name') == new_name:
                raise DatabaseError(f'Labeling with name "{new_name}" already exists')
        
        # Find and rename the matching labeling
        for i, labeling in enumerate(labelings):
            if isinstance(labeling, str) and labeling == old_name:
                # Convert string labeling to object and rename
                labelings[i] = {"name": new_name, "color": None}
                found = True
            elif isinstance(labeling, dict) and labeling.get('name') == old_name:
                # Rename existing object labeling
                labelings[i]['name'] = new_name
                found = True
            # Handle JSON string that's not yet parsed
            elif isinstance(labeling, str) and labeling.startswith('{'):
                try:
                    labeling_obj = json.loads(labeling)
                    if isinstance(labeling_obj, dict) and labeling_obj.get('name') == old_name:
                        labeling_obj['name'] = new_name
                        labelings[i] = labeling_obj
                        found = True
                except:
                    pass

        if not found:
            raise DatabaseError(f'Labeling "{old_name}" not found in project')
            
        # Save the updated labelings back to the database
        update_query = """
            UPDATE projects
            SET labelings = %s
            WHERE project_id = %s
        """
        rows_affected = self._execute_query(update_query, (json.dumps(labelings), project_id), commit=True)
        
        if rows_affected == 0:
            raise DatabaseError('Failed to rename labeling')
            
        return {
            'status': 'success',
            'old_name': old_name,
            'new_name': new_name
        }

    def delete_labeling(self, project_id, labeling_name):
        """
        Mark a labeling as deleted in a project
        
        Args:
            project_id: ID of the project containing the labeling
            labeling_name: Name of the labeling to mark as deleted
            
        Returns:
            dict: Status and message indicating success or failure
        """
        import json
        
        # First, get the current labelings
        query = """
            SELECT labelings
            FROM projects
            WHERE project_id = %s
        """
        result = self._execute_query(query, (project_id,), fetch_one=True)
        
        if not result or not result.get('labelings'):
            raise DatabaseError('Project not found or no labelings exist')
            
        # Parse the labelings JSON
        labelings = json.loads(result['labelings'])
        found = False
        
        # Find and mark the matching labeling as deleted
        for i, labeling in enumerate(labelings):
            if isinstance(labeling, str) and labeling == labeling_name:
                # Convert string labeling to object and mark as deleted
                labelings[i] = {"name": labeling_name, "color": None, "is_deleted": True}
                found = True
            elif isinstance(labeling, dict) and labeling.get('name') == labeling_name:
                # Mark existing object labeling as deleted
                labelings[i]['is_deleted'] = True
                found = True
            # Handle JSON string that's not yet parsed
            elif isinstance(labeling, str) and labeling.startswith('{'):
                try:
                    labeling_obj = json.loads(labeling)
                    if isinstance(labeling_obj, dict) and labeling_obj.get('name') == labeling_name:
                        labeling_obj['is_deleted'] = True
                        labelings[i] = labeling_obj
                        found = True
                except:
                    pass

        if not found:
            raise DatabaseError(f'Labeling "{labeling_name}" not found in project')
            
        # Save the updated labelings back to the database
        update_query = """
            UPDATE projects
            SET labelings = %s
            WHERE project_id = %s
        """
        rows_affected = self._execute_query(update_query, (json.dumps(labelings), project_id), commit=True)
        
        if rows_affected == 0:
            raise DatabaseError('Failed to mark labeling as deleted')
            
        return {
            'status': 'success',
            'labeling_name': labeling_name
        }
    
    def update_participant(self, project_id, new_participant_id):
        """Update the participant assigned to a project"""
        query = "UPDATE projects SET participant_id = %s WHERE project_id = %s"
        rows_affected = self._execute_query(query, (new_participant_id, project_id), commit=True)
        
        if rows_affected == 0:
            raise DatabaseError('Project not found')
        
        return True
    
    def update_project_type(self, project_id: int, project_type: str, analysis_config: dict = None):
        """Update project type and analysis configuration"""
        import json
        
        query = """
            UPDATE projects 
            SET project_type = %s, analysis_config = %s 
            WHERE project_id = %s
        """
        
        analysis_config_json = json.dumps(analysis_config) if analysis_config else None
        rows_affected = self._execute_query(query, (project_type, analysis_config_json, project_id), commit=True)
        
        if rows_affected == 0:
            raise DatabaseError('Project not found')
        
        return True
