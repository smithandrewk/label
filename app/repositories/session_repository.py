from .base_repository import BaseRepository
from app.logging_config import get_logger

logger = get_logger(__name__)

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
        result = self._execute_query(query, (session_id,), fetch_one=True)
        return result['bouts'] if result else None
    
    def set_bouts_by_session(self, session_id, bouts):
        """Set smoking bouts for a session"""
        query = "UPDATE sessions SET bouts = %s WHERE session_id = %s"
        return self._execute_query(query, (bouts, session_id), commit=True)

    def insert_single_session(self, session_name, project_id, bouts_json, start_ns, stop_ns):
        """
        Insert a single session into the database.
        
        Args:
            session_name: Name of the session
            project_id: ID of the project this session belongs to
            bouts_json: JSON string of bouts data
            start_ns: Start timestamp in nanoseconds since reboot
            stop_ns: Stop timestamp in nanoseconds since reboot
            
        Returns:
            list: List containing the session name if successful, empty list if failed
        """
        try:
            query = """
                INSERT INTO sessions (project_id, session_name, status, keep, bouts, start_ns, stop_ns)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            self._execute_query(query, (project_id, session_name, 'Initial', None, bouts_json, start_ns, stop_ns), commit=True)
            logger.debug(f"Successfully inserted single session '{session_name}' for project {project_id} (start_ns: {start_ns}, stop_ns: {stop_ns})")
            return [session_name]
        except Exception as e:
            logger.error(
                f"Error inserting session {session_name}: {e}", 
                exc_info=True,
                extra={
                    'session_name': session_name,
                    'project_id': project_id
                }
            )
            return []

    def count_sessions_by_name_and_project(self, session_name, project_id):
        """
        Count sessions with a specific name in a project.
        
        Args:
            session_name: Name of the session to check
            project_id: ID of the project
            
        Returns:
            int: Number of sessions with that name in the project
        """
        query = "SELECT COUNT(*) as count FROM sessions WHERE session_name = %s AND project_id = %s"
        result = self._execute_query(query, (session_name, project_id), fetch_one=True)
        return result['count'] if result else 0