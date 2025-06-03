from flask import jsonify

class ProjectService:
    def __init__(self, db):
        self.db = db
    def list_projects(self):
        conn = self.db()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.project_id, p.project_name, p.path, pt.participant_code
            FROM projects p
            JOIN participants pt ON p.participant_id = pt.participant_id
        """)
        projects = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(projects), 200