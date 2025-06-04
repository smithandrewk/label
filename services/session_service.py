from flask import session
from utils.database_helpers import safe_fetchone_dict,get_db_cursor
from utils.logging import log
import json
import os
class SessionService:
    def __init__(self, db):
        self.db = db
    
    def list_sessions(self,project_id=None, show_split=False):
        """
        List sessions with optional filtering by project and split status.
        
        Args:
            project_id: Optional project ID to filter by
            show_split: Whether to include sessions with 'Split' status
        """
        # Build query based on parameters
        base_query = """
            SELECT s.session_id, s.session_name, s.status, s.keep, s.verified,
                p.project_name, p.project_id, part.participant_code
            FROM sessions s
            JOIN projects p ON s.project_id = p.project_id
            JOIN participants part ON p.participant_id = part.participant_id
            WHERE 1=1
        """
        
        params = []
        conditions = []
        
        if project_id:
            conditions.append("s.project_id = %s")
            params.append(project_id)
        
        if not show_split:
            conditions.append("(s.status != 'Split' OR s.status IS NULL)")
        
        # Add conditions to query
        if conditions:
            base_query += " AND " + " AND ".join(conditions)
        
        base_query += " ORDER BY s.session_name"
        
        with get_db_cursor(self.db) as cursor:
            cursor.execute(base_query, params)
            sessions = cursor.fetchall()
        
            if not sessions:
                raise ValueError(f'No sessions found for project_id: {project_id}')
            return sessions

    def get_session_metadata(self,session_id):
        with get_db_cursor(self.db) as cursor:
            cursor.execute("""
                SELECT s.session_id, s.session_name, s.status, s.keep, s.verified, s.bouts,
                    p.project_id, p.project_name, p.path AS project_path
                FROM sessions s
                JOIN projects p ON s.project_id = p.project_id
                WHERE s.session_id = %s
            """, (session_id,))

            session_metadata = cursor.fetchone()

            if not session_metadata:
                raise ValueError(f'Session data not found: {session_id}')
            
            return session_metadata
        
    def update_session_metadata(self, status, keep, bouts, verified, session_id):
        with get_db_cursor(self.db, write=True) as cursor:
            cursor.execute("""
                UPDATE sessions
                SET status = %s, keep = %s, bouts = %s, verified = %s
                WHERE session_id = %s
            """, (status, keep, bouts, verified, session_id))

            rows_affected = cursor.rowcount

            if rows_affected == 0:
                raise ValueError(f'Session not found: {session_id}')

    def insert_new_sessions_after_split(self, session_info, new_sessions):
        with get_db_cursor(self.db, write=True) as cursor:
            parent_id = session_info['session_id']
            for session_data in new_sessions:
                # Keep the same project_id
                cursor.execute("""
                    INSERT INTO sessions (project_id, session_name, status, keep, bouts)
                    VALUES (%s, %s, %s, %s, %s)
                """, (session_info['project_id'],
                    session_data['name'], 
                    'Initial',
                    session_info['keep'],
                    json.dumps(session_data['bouts'])
                ))
                # Get the new session ID
                child_id = cursor.lastrowid

                # Record lineage
                cursor.execute("""
                    INSERT INTO session_lineage (child_session_id, parent_session_id)
                    VALUES (%s, %s)
                """, (child_id, parent_id))
                
            # Delete original session
            cursor.execute("""
                UPDATE sessions
                SET status = 'Split', 
                    keep = 0,
                    is_visible = 0  # Make sure to add this column to your sessions table
                WHERE session_id = %s
            """, (parent_id,))

    def generate_unique_session_name(self, original_name, project_path, project_id):
        with get_db_cursor(self.db) as cursor:
            base_counter = 1
            max_attempts = 1000  # Safety limit to prevent infinite loops
            
            while base_counter <= max_attempts:
                candidate_name = f"{original_name}.{base_counter}"
                
                # Check filesystem for collision
                candidate_path = os.path.join(project_path, candidate_name)
                if os.path.exists(candidate_path):
                    log(f"Filesystem collision for {candidate_name}")
                    base_counter += 1
                    continue
                    
                # Check database for collision
                cursor.execute("""
                    SELECT COUNT(*) as count FROM sessions 
                    WHERE session_name = %s AND project_id = %s
                """, (candidate_name, project_id))
                
                result = cursor.fetchone()
                count = result['count'] if isinstance(result, dict) else result[0]
                
                if count == 0:
                    log(f"Generated unique session name: {candidate_name}")
                    return candidate_name
                
                log(f"Database collision for {candidate_name}")
                base_counter += 1
            
            # If we've exhausted all attempts, raise an error
            raise RuntimeError(f"Could not generate unique session name after {max_attempts} attempts")