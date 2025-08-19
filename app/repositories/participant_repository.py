from .base_repository import BaseRepository
from app.exceptions import DatabaseError

class ParticipantRepository(BaseRepository):
    """Repository for participant-related database operations"""
    
    def find_by_code(self, participant_code):
        """Find participant by their code"""
        query = "SELECT participant_id FROM participants WHERE participant_code = %s"
        participant = self._execute_query(query, (participant_code,), fetch_one=True)
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
    
    def update_great_puffs(self, participant_id, great_puffs):
        """Update participant's great puffs status"""
        query = """
            UPDATE participants 
            SET great_puffs = %s
            WHERE participant_id = %s
        """
        try:
            rows_affected = self._execute_query(
                query, 
                (great_puffs, participant_id), 
                commit=True
            )
            if rows_affected == 0:
                raise DatabaseError('Participant not found')
            return self.find_by_id(participant_id)
        except DatabaseError as e:
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
                pt.great_puffs,
                COUNT(DISTINCT p.project_id) as project_count,
                GROUP_CONCAT(DISTINCT p.project_name ORDER BY p.project_id SEPARATOR ', ') as project_names,
                GROUP_CONCAT(DISTINCT p.project_id ORDER BY p.project_id SEPARATOR ',') as project_ids,
                SUM(CASE WHEN s.keep != 0 OR s.keep IS NULL THEN 1 ELSE 0 END) as total_sessions
            FROM participants pt
            LEFT JOIN projects p ON pt.participant_id = p.participant_id
            LEFT JOIN sessions s ON p.project_id = s.project_id 
                AND (s.status != 'Split' OR s.status IS NULL)
            GROUP BY pt.participant_id, pt.participant_code, pt.first_name, pt.last_name, pt.email, pt.notes, pt.created_at, pt.great_puffs
            ORDER BY pt.participant_code
        """
        participants = self._execute_query(query, fetch_all=True)
        
        # Get verification status for each project
        for participant in participants:
            if participant['project_ids']:
                participant['project_verification_status'] = self._get_project_verification_status(participant['project_ids'])
            else:
                participant['project_verification_status'] = {}
                
        return participants
    
    def _get_project_verification_status(self, project_ids_str):
        """Get verification status for each project based on smoking and puff verification"""
        if not project_ids_str:
            return {}
            
        project_ids = [int(id.strip()) for id in project_ids_str.split(',')]
        verification_status = {}
        
        for project_id in project_ids:
            # Check verification status for both smoking and puffs
            query = """
                SELECT 
                    COUNT(*) as total_sessions,
                    COUNT(CASE WHEN (smoking_verified = 1 OR smoking_verified = 100) THEN 1 END) as smoking_verified_sessions,
                    COUNT(CASE WHEN (puffs_verified = 1 OR puffs_verified = 100) THEN 1 END) as puffs_verified_sessions
                FROM sessions 
                WHERE project_id = %s 
                    AND (keep != 0 OR keep IS NULL)
                    AND (status != 'Split' OR status IS NULL)
            """
            result = self._execute_query(query, (project_id,), fetch_one=True)
            
            if result and result['total_sessions'] > 0:
                smoking_percentage = round((result['smoking_verified_sessions'] / result['total_sessions']) * 100, 1)
                puffs_percentage = round((result['puffs_verified_sessions'] / result['total_sessions']) * 100, 1)
                
                verification_status[project_id] = {
                    'all_verified': result['total_sessions'] == result['smoking_verified_sessions'],
                    'verified_count': result['smoking_verified_sessions'],
                    'total_count': result['total_sessions'],
                    'percentage': smoking_percentage,
                    'smoking': {
                        'all_verified': result['total_sessions'] == result['smoking_verified_sessions'],
                        'verified_count': result['smoking_verified_sessions'],
                        'percentage': smoking_percentage
                    },
                    'puffs': {
                        'all_verified': result['total_sessions'] == result['puffs_verified_sessions'],
                        'verified_count': result['puffs_verified_sessions'],
                        'percentage': puffs_percentage
                    }
                }
            else:
                verification_status[project_id] = {
                    'all_verified': False,
                    'verified_count': 0,
                    'total_count': 0,
                    'percentage': 0,
                    'smoking': {
                        'all_verified': False,
                        'verified_count': 0,
                        'percentage': 0
                    },
                    'puffs': {
                        'all_verified': False,
                        'verified_count': 0,
                        'percentage': 0
                    }
                }
        
        return verification_status
    
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
