from flask import Flask, jsonify, send_from_directory, request
import os
import pandas as pd
import mysql.connector
from mysql.connector import Error
import json
import shutil

app = Flask(__name__, static_folder='static')

# Directory containing session data
DATA_DIR = 'data'

# MySQL configuration
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Password123!',
    'database': 'accelerometer_db'
}

# Initialize MySQL connection
def get_db_connection():
    try:
        return mysql.connector.connect(**MYSQL_CONFIG)
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

from datetime import datetime

# Get list of projects
@app.route('/api/projects')
def list_projects():
    try:
        conn = get_db_connection()
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
        return jsonify(projects)
    except Exception as e:
        print(f"Error listing projects: {e}")
        return jsonify({'error': str(e)}), 500
# Upload new project
@app.route('/api/project/upload', methods=['POST'])
def upload_new_project():
    try:
        data = request.get_json()
        print(data)

        # Get database connection
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor()

        # First check if participant exists
        cursor.execute("""
            SELECT participant_id FROM participants WHERE participant_code = %s
        """, (data['participant'],))
        participant = cursor.fetchone()

        if participant:
            # Use existing participant
            participant_id = participant[0]
        else:
            # Create new participant
            cursor.execute("""
                INSERT INTO participants (participant_code) 
                VALUES (%s)
            """, (data['participant'],))
            participant_id = cursor.lastrowid

        # Then insert project with the participant_id
        cursor.execute("""
            INSERT INTO projects (project_name, participant_id, path)
            VALUES (%s, %s, %s)
        """, (data['name'], participant_id, data['path']))

        # Get the new project_id
        project_id = cursor.lastrowid

        # Now scan the project path for sessions and insert them
        project_path = data['path']

        if os.path.exists(project_path) and os.path.isdir(project_path):
            # Find all session directories in this project path
            sessions = [
                {'name': d, 'file': 'accelerometer_data.csv'}
                for d in os.listdir(project_path)
                if os.path.isdir(os.path.join(project_path, d)) 
                and os.path.exists(os.path.join(project_path, d, 'accelerometer_data.csv'))
            ]
            # Sort sessions by date/time in the name (assuming similar format as in list_sessions)
            try:
                sessions.sort(key=lambda s: datetime.strptime('_'.join(s['name'].split('_')[:4]), '%Y-%m-%d_%H_%M_%S'))
            except:
                # If sorting fails (due to different naming convention), keep original order
                pass

            # Insert each session into the database
            for session in sessions:
                try:
                    # Look for log.csv to extract bouts data
                    bouts_json = '{}'
                    log_path = os.path.join(project_path, session['name'], 'log.csv')
                    if os.path.exists(log_path):
                        try:
                            log = pd.read_csv(log_path, skiprows=5)
                            bouts = pd.concat([
                                log.loc[log['Message'] == 'Updating walking status from false to true'].reset_index(drop=True).rename({'ns_since_reboot': 'start_time'}, axis=1)['start_time'],
                                log[log['Message'] == 'Updating walking status from true to false'].reset_index(drop=True).rename({'ns_since_reboot': 'stop_time'}, axis=1)['stop_time']
                            ], axis=1).values.tolist()
                            bouts_json = json.dumps(bouts)
                        except Exception as e:
                            print(f"Error processing log file for bouts: {e}")
                    
                    cursor.execute("""
                        INSERT INTO sessions (project_id, session_name, status, keep, label, segments, bouts)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (project_id, session['name'], 'Initial', None, '', '{}', bouts_json))
                except Exception as e:
                    print(f"Error inserting session {session['name']}: {e}")
                    continue  # Skip this session and continue with others
        else:
            return jsonify({'error': f'Project path {project_path} does not exist or is not a directory'}), 400
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'message': 'Project uploaded successfully',
            'project_id': project_id,
            'participant_id': participant_id
        })
    except Exception as e:
        print(f"Error parsing request data: {e}")
        return jsonify({'error': 'Invalid request data'}), 400


@app.route('/api/sessions')
def list_sessions():
    try:
        project_id = request.args.get('project_id')
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        if project_id:
            # Get sessions for a specific project
            cursor.execute("""
                SELECT s.session_id, s.session_name, s.status, s.keep, s.label,
                       p.project_name, p.project_id, part.participant_code
                FROM sessions s
                JOIN projects p ON s.project_id = p.project_id
                JOIN participants part ON p.participant_id = part.participant_id
                WHERE s.project_id = %s
                ORDER BY s.session_name
            """, (project_id,))
        else:
            # Get all sessions
            cursor.execute("""
                SELECT s.session_id, s.session_name, s.status, s.keep, s.label,
                       p.project_name, p.project_id, part.participant_code
                FROM sessions s
                JOIN projects p ON s.project_id = p.project_id
                JOIN participants part ON p.participant_id = part.participant_id
                ORDER BY s.session_name
            """)
        
        sessions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(sessions)
    except Exception as e:
        print(f"Error listing sessions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<int:session_id>')
def get_session_data(session_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.session_name, p.project_id, p.project_name, 
                   p.path AS project_path
            FROM sessions s
            JOIN projects p ON s.project_id = p.project_id
            WHERE s.session_id = %s
        """, (session_id,))
        
        session_info = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not session_info:
            return jsonify({'error': 'Session not found'}), 404
        
        # Use the project path stored in the description field
        project_path = session_info['project_path']
        session_name = session_info['session_name']
        
        # Path to the session's data files
        csv_path = os.path.join(project_path, session_name, 'accelerometer_data.csv')
        if not os.path.exists(csv_path):
            return jsonify({'error': f'CSV file not found at {csv_path}'}), 404
        
        # Continue with your existing code to process the CSV file...
        df = pd.read_csv(csv_path)
        df = df.iloc[::30]  # Downsampling
        
        # Extract bouts from log file if it exists
        bouts = []
        log_path = os.path.join(project_path, session_name, 'log.csv')
        if os.path.exists(log_path):
            try:
                log = pd.read_csv(log_path, skiprows=5)
                bouts = pd.concat([
                    log.loc[log['Message'] == 'Updating walking status from false to true'].reset_index(drop=True).rename({'ns_since_reboot': 'start_time'}, axis=1)['start_time'],
                    log[log['Message'] == 'Updating walking status from true to false'].reset_index(drop=True).rename({'ns_since_reboot': 'stop_time'}, axis=1)['stop_time']
                ], axis=1).values.tolist()
                bouts = [bout for bout in bouts if (bout[0] > df['ns_since_reboot'].min() and bout[1] < df['ns_since_reboot'].max())]
            except Exception as e:
                print(f"Error processing log file: {e}")
        
        expected_columns = ['ns_since_reboot', 'x', 'y', 'z']
        if not all(col in df.columns for col in expected_columns):
            return jsonify({'error': f'Invalid CSV format. Expected columns: {expected_columns}, Found: {list(df.columns)}'}), 400
        
        data = df[expected_columns].to_dict(orient='records')
        data = {
            'bouts': bouts,
            'data': data,
            'session_info': session_info
        }
        
        return jsonify(data)
    except Exception as e:
        print(f"Error retrieving session data: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500
# Get session metadata
@app.route('/api/session/<session_name>/metadata')
def get_session_metadata(session_name):
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT session_name, status, keep, label, segments
            FROM sessions
            WHERE session_name = %s
        """, (session_name,))
        metadata = cursor.fetchone()
        cursor.close()
        conn.close()
        if not metadata:
            return jsonify({'error': 'Session not found'}), 404
        return jsonify(metadata)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Update session metadata
@app.route('/api/session/<session_name>/metadata', methods=['PUT'])
def update_session_metadata(session_name):
    try:
        data = request.get_json()
        status = data.get('status')
        keep = data.get('keep')
        label = data.get('label')
        segments = data.get('segments')

        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions
            SET status = %s, keep = %s, label = %s, segments = %s
            WHERE session_name = %s
        """, (status, keep, label, json.dumps(segments), session_name))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Metadata updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Split session
@app.route('/api/session/<session_name>/split', methods=['POST'])
def split_session(session_name):
    try:
        data = request.get_json()
        split_points = data.get('split_points')  # Array of ns_since_reboot timestamps
        if not split_points or not isinstance(split_points, list) or len(split_points) == 0:
            return jsonify({'error': 'At least one split point required'}), 400

        # Read original CSV
        csv_path = os.path.join(DATA_DIR, session_name, 'accelerometer_data.csv')
        if not os.path.exists(csv_path):
            return jsonify({'error': f'CSV file not found at {csv_path}'}), 404
        
        df = pd.read_csv(csv_path)
        expected_columns = ['ns_since_reboot', 'x', 'y', 'z']
        if not all(col in df.columns for col in expected_columns):
            return jsonify({'error': f'Invalid CSV format. Expected columns: {expected_columns}, Found: {list(df.columns)}'}), 400

        # Find split indices
        split_points = sorted(set(float(p) for p in split_points))  # Ensure unique and sorted
        split_indices = []
        for point in split_points:
            df['time_diff'] = abs(df['ns_since_reboot'] - point)
            split_index = df['time_diff'].idxmin()
            if split_index == 0 or split_index == len(df) - 1:
                continue  # Skip points at start or end
            split_indices.append(split_index)
        split_indices = sorted(set(split_indices))  # Ensure unique and sorted

        if not split_indices:
            return jsonify({'error': 'No valid split points provided'}), 400

        # Split data into segments
        segments = []
        start_idx = 0
        for idx in split_indices:
            segment = df.iloc[start_idx:idx + 1][expected_columns]
            if not segment.empty:
                segments.append(segment)
            start_idx = idx + 1
        # Add final segment
        final_segment = df.iloc[start_idx:][expected_columns]
        if not final_segment.empty:
            segments.append(final_segment)

        if len(segments) < 2:
            return jsonify({'error': 'Split would not create multiple valid recordings'}), 400

        # Get original metadata
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT status, keep, label, segments
                FROM sessions
                WHERE session_name = %s
            """, (session_name,))
            metadata = cursor.fetchone()
        if not metadata:
            conn.close()
            return jsonify({'error': 'Session metadata not found'}), 404

        # Create new session names
        new_sessions = []
        for i, segment in enumerate(segments):
            suffix = chr(65 + i)  # A, B, C, ...
            new_name = f"{session_name}_{suffix}"
            new_dir = os.path.join(DATA_DIR, new_name)
            if os.path.exists(new_dir):
                conn.close()
                return jsonify({'error': f'New session name {new_name} already exists'}), 400
            os.makedirs(new_dir)
            segment.to_csv(os.path.join(new_dir, 'accelerometer_data.csv'), index=False)
            new_sessions.append(new_name)

        # Copy original log file to new directories
        log_path = os.path.join(DATA_DIR, session_name, 'log.csv')
        if os.path.exists(log_path):
            for new_name in new_sessions:
                shutil.copy(log_path, os.path.join(DATA_DIR, new_name, 'log.csv'))
        else:
            print(f"Log file not found at {log_path}. Skipping copy.")
        # Insert new sessions into database
        with conn.cursor() as cursor:
            for new_name in new_sessions:
                cursor.execute("""
                    INSERT INTO sessions (session_name, status, keep, label, segments)
                    VALUES (%s, %s, %s, %s, %s)
                """, (new_name, 'Initial', metadata['keep'], metadata['label'], '{}'))
            # Delete original session
            cursor.execute("DELETE FROM sessions WHERE session_name = %s", (session_name,))
        
        conn.commit()
        conn.close()

        # Delete original session directory
        shutil.rmtree(os.path.join(DATA_DIR, session_name))

        return jsonify({'message': 'Session split successfully', 'new_sessions': new_sessions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True, port=80)