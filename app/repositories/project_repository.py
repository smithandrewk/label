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
