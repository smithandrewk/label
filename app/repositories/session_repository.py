from .base_repository import BaseRepository

class SessionRepository(BaseRepository):
    """Repository for session-related database operations"""
    
    def delete_by_project(self, project_id):
        """Delete all sessions for a project"""
        query = "DELETE FROM sessions WHERE project_id = %s"
        return self._execute_query(query, (project_id,), commit=True)
    
    def delete_lineage_by_project(self, project_id):
        """Delete session lineage records for a project"""
        query = """
            DELETE sl FROM session_lineage sl
            JOIN sessions s ON (sl.child_session_id = s.session_id OR sl.parent_session_id = s.session_id)
            WHERE s.project_id = %s
        """
        return self._execute_query(query, (project_id,), commit=True)
    
    def delete_lineage_by_participant(self, participant_id):
        """Delete session lineage records for all sessions of a participant"""
        query = """
            DELETE sl FROM session_lineage sl
            JOIN sessions s ON (sl.child_session_id = s.session_id OR sl.parent_session_id = s.session_id)
            JOIN projects p ON s.project_id = p.project_id
            WHERE p.participant_id = %s
        """
        return self._execute_query(query, (participant_id,), commit=True)

    def get_bouts_by_session(self, session_id):
        """Get smoking bouts for a session"""
        query = "SELECT bouts FROM sessions WHERE session_id = %s"
        return self._execute_query(query, (session_id,), fetch_one=True)
    
    def set_bouts_by_session(self, session_id, bouts):
        """Set smoking bouts for a session"""
        query = "UPDATE sessions SET bouts = %s WHERE session_id = %s"
        return self._execute_query(query, (bouts, session_id), commit=True)