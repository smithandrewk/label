from flask import jsonify

class SessionService:
    def __init__(self, db):
        self.db = db
    
    def list_sessions(self,request):
        project_id = request.args.get('project_id')
        show_split = request.args.get('show_split', '0') == '1'  # Optional parameter to show split sessions
        
        conn = self.db()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Base query filtering out split sessions
        visibility_condition = "" if show_split else "AND (s.status != 'Split' OR s.status IS NULL) "
        
        if project_id:
            # Get sessions for a specific project
            cursor.execute(f"""
                SELECT s.session_id, s.session_name, s.status, s.keep, s.verified,
                       p.project_name, p.project_id, part.participant_code
                FROM sessions s
                JOIN projects p ON s.project_id = p.project_id
                JOIN participants part ON p.participant_id = part.participant_id
                WHERE s.project_id = %s {visibility_condition}
                ORDER BY s.session_name
            """, (project_id,))
        else:
            # Get all sessions
            cursor.execute(f"""
                SELECT s.session_id, s.session_name, s.status, s.keep, s.verified,
                       p.project_name, p.project_id, part.participant_code
                FROM sessions s
                JOIN projects p ON s.project_id = p.project_id
                JOIN participants part ON p.participant_id = part.participant_id
                WHERE 1=1 {visibility_condition}
                ORDER BY s.session_name
            """)
        
        sessions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(sessions),200