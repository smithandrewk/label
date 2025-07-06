from .base_repository import BaseRepository
from app.exceptions import DatabaseError

class ParticipantRepository(BaseRepository):
    """Repository for participant-related database operations"""
    
    def find_by_code(self, participant_code):
        """Find participant by their code"""
        query = "SELECT participant_id FROM participants WHERE participant_code = %s"
        participant = self._execute_query(query, (participant_code,), fetch_one=True)
        print(participant)
        if participant:
            participant['participant_code'] = participant_code
        return participant

    def create(self, participant_code):
        """Create a new participant with just the code"""
        query = "INSERT INTO participants (participant_code) VALUES (%s)"
        try:
            self._execute_query(query, (participant_code,), commit=True)
            # Get the created participant
            return self.find_by_code(participant_code)
        except DatabaseError as e:
            # Handle duplicate entry - try to find existing participant
            if 'Duplicate entry' in str(e) or '1062' in str(e):
                existing = self.find_by_code(participant_code)
                if existing:
                    return existing
                raise DatabaseError("Failed to create or find participant")
            raise e
    
    def create_with_details(self, participant_code, first_name, last_name, email, notes):
        """Create a new participant with detailed information"""
        query = """
            INSERT INTO participants (participant_code, first_name, last_name, email, notes)
            VALUES (%s, %s, %s, %s, %s)
        """
        try:
            self._execute_query(query, (participant_code, first_name, last_name, email, notes), commit=True)
            return self.find_by_code(participant_code)
        except DatabaseError as e:
            if 'Duplicate entry' in str(e) or '1062' in str(e):
                raise DatabaseError(f'Participant code "{participant_code}" already exists')
            raise e
    
    def update(self, participant_id, participant_code, first_name, last_name, email, notes):
        """Update participant information"""
        query = """
            UPDATE participants 
            SET participant_code = %s, first_name = %s, last_name = %s, email = %s, notes = %s
            WHERE participant_id = %s
        """
        try:
            rows_affected = self._execute_query(
                query, 
                (participant_code, first_name, last_name, email, notes, participant_id), 
                commit=True
            )
            if rows_affected == 0:
                raise DatabaseError('Participant not found')
            return self.find_by_id(participant_id)
        except DatabaseError as e:
            if 'Duplicate entry' in str(e) or '1062' in str(e):
                raise DatabaseError(f'Participant code "{participant_code}" already exists')
            raise e
    
    def find_by_id(self, participant_id):
        """Find participant by ID"""
        query = "SELECT participant_id, participant_code FROM participants WHERE participant_id = %s"
        return self._execute_query(query, (participant_id,), fetch_one=True)
    
    def get_all_with_stats(self):
        """Get all participants with their project and session statistics"""
        query = """
            SELECT 
                pt.participant_id, 
                pt.participant_code, 
                pt.first_name, 
                pt.last_name, 
                pt.email, 
                pt.notes,
                pt.created_at,
                COUNT(DISTINCT p.project_id) as project_count,
                GROUP_CONCAT(DISTINCT p.project_name ORDER BY p.project_id SEPARATOR ', ') as project_names,
                GROUP_CONCAT(DISTINCT p.project_id ORDER BY p.project_id SEPARATOR ',') as project_ids,
                SUM(CASE WHEN s.keep != 0 OR s.keep IS NULL THEN 1 ELSE 0 END) as total_sessions
            FROM participants pt
            LEFT JOIN projects p ON pt.participant_id = p.participant_id
            LEFT JOIN sessions s ON p.project_id = s.project_id 
                AND (s.status != 'Split' OR s.status IS NULL)
            GROUP BY pt.participant_id, pt.participant_code, pt.first_name, pt.last_name, pt.email, pt.notes, pt.created_at
            ORDER BY pt.participant_code
        """
        return self._execute_query(query, fetch_all=True)
    
    def count_projects(self, participant_id):
        """Count projects for a participant"""
        query = "SELECT COUNT(*) as project_count FROM projects WHERE participant_id = %s"
        result = self._execute_query(query, (participant_id,), fetch_one=True)
        return result['project_count'] if result else 0
    
    def count_sessions(self, participant_id):
        """Count sessions for a participant across all projects"""
        query = """
            SELECT COUNT(*) as session_count FROM sessions s
            JOIN projects p ON s.project_id = p.project_id
            WHERE p.participant_id = %s
        """
        result = self._execute_query(query, (participant_id,), fetch_one=True)
        return result['session_count'] if result else 0
    
    def delete(self, participant_id):
        """Delete a participant"""
        query = "DELETE FROM participants WHERE participant_id = %s"
        return self._execute_query(query, (participant_id,), commit=True)
    
    def delete_cascade(self, participant_id):
        """Delete participant and all associated data in the correct order"""
        operations = [
            # Delete session lineage records first (due to foreign key constraints)
            ("""
                DELETE sl FROM session_lineage sl
                JOIN sessions s ON (sl.child_session_id = s.session_id OR sl.parent_session_id = s.session_id)
                JOIN projects p ON s.project_id = p.project_id
                WHERE p.participant_id = %s
            """, (participant_id,)),
            
            # Delete sessions
            ("""
                DELETE s FROM sessions s
                JOIN projects p ON s.project_id = p.project_id
                WHERE p.participant_id = %s
            """, (participant_id,)),
            
            # Delete projects
            ("DELETE FROM projects WHERE participant_id = %s", (participant_id,)),
            
            # Delete participant
            ("DELETE FROM participants WHERE participant_id = %s", (participant_id,))
        ]
        
        results = self._execute_transaction(operations)
        return {
            'sessions_deleted': results[1],  # sessions delete result
            'projects_deleted': results[2]   # projects delete result
        }
