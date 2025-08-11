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

    def insert_single_session(self, session_name, project_id, bouts_json, start_ns, stop_ns, 
                             parent_data_path=None, data_start_offset=None, data_end_offset=None):
        """
        Insert a single session into the database.
        
        Args:
            session_name: Name of the session
            project_id: ID of the project this session belongs to
            bouts_json: JSON string of bouts data
            start_ns: Start timestamp in nanoseconds since reboot
            stop_ns: Stop timestamp in nanoseconds since reboot
            parent_data_path: Path to parent data file for virtual splits (optional)
            data_start_offset: Start row index for pandas slicing (optional)
            data_end_offset: End row index for pandas slicing (optional)
            
        Returns:
            list: List containing the session name if successful, empty list if failed
        """
        try:
            query = """
                INSERT INTO sessions (project_id, session_name, status, keep, bouts, start_ns, stop_ns, 
                                    parent_session_data_path, data_start_offset, data_end_offset)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            self._execute_query(query, (project_id, session_name, 'Initial', None, bouts_json, start_ns, stop_ns,
                                      parent_data_path, data_start_offset, data_end_offset), commit=True)
            logger.debug(f"Successfully inserted session '{session_name}' for project {project_id} (start_ns: {start_ns}, stop_ns: {stop_ns}, virtual_split: {parent_data_path is not None})")
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

    def insert_virtual_split_session(self, session_name, project_id, bouts_json, start_ns, stop_ns, 
                                   parent_data_path, data_start_offset, data_end_offset):
        """
        Insert a virtual split session into the database.
        
        Args:
            session_name: Name of the new session
            project_id: ID of the project this session belongs to
            bouts_json: JSON string of bouts data for this split
            start_ns: Start timestamp in nanoseconds since reboot
            stop_ns: Stop timestamp in nanoseconds since reboot
            parent_data_path: Path to parent data file
            data_start_offset: Start row index for pandas slicing
            data_end_offset: End row index for pandas slicing
            
        Returns:
            int: Session ID if successful, None if failed
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                INSERT INTO sessions (project_id, session_name, status, keep, bouts, start_ns, stop_ns, 
                                    parent_session_data_path, data_start_offset, data_end_offset)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (project_id, session_name, 'Initial', None, bouts_json, start_ns, stop_ns,
                                 parent_data_path, data_start_offset, data_end_offset))
            conn.commit()
            session_id = cursor.lastrowid
            
            cursor.close()
            conn.close()
            
            logger.debug(f"Successfully inserted virtual split session '{session_name}' with ID {session_id}")
            return session_id
        except Exception as e:
            logger.error(f"Error inserting virtual split session {session_name}: {e}", exc_info=True)
            return None

    def get_session_split_info(self, session_id):
        """
        Get virtual split information for a session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            dict: Contains parent_data_path, data_start_offset, data_end_offset, or None if not found
        """
        query = """
            SELECT parent_session_data_path, data_start_offset, data_end_offset
            FROM sessions 
            WHERE session_id = %s
        """
        result = self._execute_query(query, (session_id,), fetch_one=True)
        if result:
            return {
                'parent_data_path': result['parent_session_data_path'],
                'data_start_offset': result['data_start_offset'],
                'data_end_offset': result['data_end_offset']
            }
        return None

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