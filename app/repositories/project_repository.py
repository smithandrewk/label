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
            
        return {'status': 'success', 'message': f'Color updated for labeling "{labeling_name}"'}
