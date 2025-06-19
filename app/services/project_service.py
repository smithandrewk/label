from app.exceptions import DatabaseError
class ProjectService:
    def __init__(self, get_db_connection=None):
        self.get_db_connection = get_db_connection
    
    def list_projects(self):
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT p.project_id, p.project_name, p.path, pt.participant_code
                FROM projects p
                JOIN participants pt ON p.participant_id = pt.participant_id
            """)
            projects = cursor.fetchall()
            return projects
        finally:
            cursor.close()
            conn.close()
    
    def get_participant_by_code(self, participant_code):
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT participant_id FROM participants WHERE participant_code = %s
            """, (participant_code,))
            participant = cursor.fetchone()
            return participant
        finally:
            cursor.close()
            conn.close()

    def insert_project(self, project_name, participant_id, path):
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO projects (project_name, participant_id, path) 
                VALUES (%s, %s, %s)
            """, (project_name, participant_id, path))
            conn.commit()
            project_id = cursor.lastrowid
            return {'project_id': project_id}
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f'Failed to insert project: {str(e)}')
        finally:
            cursor.close()
            conn.close()

    def create_participant(self, participant_code):
        """Create a new participant, handling race conditions if it already exists"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor()
        try:
            # Create new participant - use INSERT IGNORE to handle race conditions
            cursor.execute("""
                INSERT INTO participants (participant_code) 
                VALUES (%s)
            """, (participant_code,))
            participant_id = cursor.lastrowid
            conn.commit()
            return {'participant_id': participant_id}
        except Exception as e:
            if hasattr(e, 'errno') and e.errno == 1062:  # Duplicate entry error
                # Another process created the participant, fetch it
                cursor.execute("""
                    SELECT participant_id FROM participants WHERE participant_code = %s
                """, (participant_code,))
                participant = cursor.fetchone()
                if participant:
                    return {'participant_id': participant[0]}
                else:
                    raise DatabaseError("Failed to create or find participant")
            else:
                conn.rollback()
                raise DatabaseError(f'Failed to create participant: {str(e)}')
        finally:
            cursor.close()
            conn.close()

    def create_participant_with_details(self, participant_code, first_name, last_name, email, notes):
        """Create a new participant with detailed information"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO participants (participant_code, first_name, last_name, email, notes)
                VALUES (%s, %s, %s, %s, %s)
            """, (participant_code, first_name, last_name, email, notes))
            participant_id = cursor.lastrowid
            conn.commit()
            
            return {
                'participant_id': participant_id,
                'participant_code': participant_code
            }
        except Exception as e:
            conn.rollback()
            if hasattr(e, 'errno') and e.errno == 1062:  # Duplicate entry error
                raise DatabaseError(f'Participant code "{participant_code}" already exists')
            else:
                raise DatabaseError(f'Failed to create participant: {str(e)}')
        finally:
            cursor.close()
            conn.close()

    def get_project_with_participant(self, project_id):
        """Get detailed project information including participant data"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT p.project_id, p.project_name, p.path, p.participant_id,
                    pt.participant_code
                FROM projects p
                JOIN participants pt ON p.participant_id = pt.participant_id
                WHERE p.project_id = %s
            """, (project_id,))
            
            project_info = cursor.fetchone()
            return project_info
        finally:
            cursor.close()
            conn.close()

    def cleanup_participant_if_needed(self, participant_id):
        """Check if participant has any remaining projects and delete if none exist"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Check if participant has any other projects
            cursor.execute("""
                SELECT COUNT(*) as project_count FROM projects WHERE participant_id = %s
            """, (participant_id,))
            remaining_projects = cursor.fetchone()['project_count']
            
            participant_deleted = False
            if remaining_projects == 0:
                # Delete participant if they have no other projects
                cursor.execute("""
                    DELETE FROM participants WHERE participant_id = %s
                """, (participant_id,))
                participant_deleted = True
            
            conn.commit()
            return participant_deleted
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f'Failed to cleanup participant: {str(e)}')
        finally:
            cursor.close()
            conn.close()

    def delete_project(self, project_id):
        """Delete a project by ID"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                DELETE FROM projects WHERE project_id = %s
            """, (project_id,))
            
            if cursor.rowcount == 0:
                raise DatabaseError('Project not found or already deleted')
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            if 'Project not found' in str(e):
                raise e
            raise DatabaseError(f'Failed to delete project: {str(e)}')
        finally:
            cursor.close()
            conn.close()

    def get_all_participants_with_stats(self):
        """Get all participants with their project and session statistics"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    pt.participant_id, 
                    pt.participant_code, 
                    pt.first_name, 
                    pt.last_name, 
                    pt.email, 
                    pt.notes,
                    pt.created_at,
                    COUNT(DISTINCT p.project_id) as project_count,
                    GROUP_CONCAT(DISTINCT p.project_name SEPARATOR ', ') as project_names,
                    GROUP_CONCAT(DISTINCT p.project_id SEPARATOR ',') as project_ids,
                    SUM(CASE WHEN s.keep != 0 OR s.keep IS NULL THEN 1 ELSE 0 END) as total_sessions
                FROM participants pt
                LEFT JOIN projects p ON pt.participant_id = p.participant_id
                LEFT JOIN sessions s ON p.project_id = s.project_id 
                    AND (s.status != 'Split' OR s.status IS NULL)
                GROUP BY pt.participant_id, pt.participant_code, pt.first_name, pt.last_name, pt.email, pt.notes, pt.created_at
                ORDER BY pt.participant_code
            """)
            participants = cursor.fetchall()
            return participants
        finally:
            cursor.close()
            conn.close()

    def update_participant(self, participant_id, participant_code, first_name, last_name, email, notes):
        """Update an existing participant's information"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE participants 
                SET participant_code = %s, first_name = %s, last_name = %s, email = %s, notes = %s
                WHERE participant_id = %s
            """, (participant_code, first_name, last_name, email, notes, participant_id))
            
            if cursor.rowcount == 0:
                raise DatabaseError('Participant not found')
            
            conn.commit()
            return {
                'participant_id': participant_id,
                'participant_code': participant_code
            }
        except Exception as e:
            conn.rollback()
            if 'Participant not found' in str(e):
                raise e
            if hasattr(e, 'errno') and e.errno == 1062:  # Duplicate entry error
                raise DatabaseError(f'Participant code "{participant_code}" already exists')
            else:
                raise DatabaseError(f'Failed to update participant: {str(e)}')
        finally:
            cursor.close()
            conn.close()

    def get_participant_info(self, participant_id):
        """Get basic participant information"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT participant_id, participant_code FROM participants WHERE participant_id = %s
            """, (participant_id,))
            
            participant_info = cursor.fetchone()
            return participant_info
        finally:
            cursor.close()
            conn.close()

    def get_participant_projects(self, participant_id):
        """Get all projects for a participant"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT project_id, project_name, path FROM projects WHERE participant_id = %s
            """, (participant_id,))
            projects = cursor.fetchall()
            return projects
        finally:
            cursor.close()
            conn.close()

    def count_participant_sessions(self, participant_id):
        """Count total sessions for a participant across all their projects"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT COUNT(*) as session_count FROM sessions s
                JOIN projects p ON s.project_id = p.project_id
                WHERE p.participant_id = %s
            """, (participant_id,))
            result = cursor.fetchone()
            return result['session_count']
        finally:
            cursor.close()
            conn.close()

    def delete_participant_cascade(self, participant_id):
        """Delete participant and all associated data (projects, sessions, lineage)"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Delete session lineage records first (due to foreign key constraints)
            cursor.execute("""
                DELETE sl FROM session_lineage sl
                JOIN sessions s ON (sl.child_session_id = s.session_id OR sl.parent_session_id = s.session_id)
                JOIN projects p ON s.project_id = p.project_id
                WHERE p.participant_id = %s
            """, (participant_id,))
            
            # Delete sessions
            cursor.execute("""
                DELETE s FROM sessions s
                JOIN projects p ON s.project_id = p.project_id
                WHERE p.participant_id = %s
            """, (participant_id,))
            sessions_deleted = cursor.rowcount
            
            # Delete projects
            cursor.execute("""
                DELETE FROM projects WHERE participant_id = %s
            """, (participant_id,))
            projects_deleted = cursor.rowcount
            
            # Delete participant
            cursor.execute("""
                DELETE FROM participants WHERE participant_id = %s
            """, (participant_id,))
            
            conn.commit()
            return {
                'sessions_deleted': sessions_deleted,
                'projects_deleted': projects_deleted
            }
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f'Failed to delete participant: {str(e)}')
        finally:
            cursor.close()
            conn.close()