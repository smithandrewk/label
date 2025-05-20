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
    'user': 'app_user',
    'password': 'app_user_password',
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

# List sessions
@app.route('/api/sessions')
def list_sessions():
    try:
        sessions = [
            {'name': d, 'file': 'accelerometer_data.csv'}
            for d in os.listdir(DATA_DIR)
            if os.path.isdir(os.path.join(DATA_DIR, d))
        ]
        sessions.sort(key=lambda s: datetime.strptime('_'.join(s['name'].split('_')[:4]), '%Y-%m-%d_%H_%M_%S'))
        # Initialize sessions in DB if not present
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor()
        for session in sessions:
            cursor.execute("""
                INSERT IGNORE INTO sessions (session_name, status, keep, label, segments)
                VALUES (%s, %s, %s, %s, %s)
            """, (session['name'], 'Initial', None, '', '{}'))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify(sessions)
    except Exception as e:
        print(f"Error listing sessions: {e}")
        return jsonify({'error': str(e)}), 500

# Get session data (CSV)
@app.route('/api/session/<session_name>')
def get_session_data(session_name):
    try:
        ## Labels
        log_path = os.path.join(DATA_DIR, session_name, 'log.csv')
        if not os.path.exists(log_path):
            return jsonify({'error': f'CSV file not found at {log_path}'}), 404
        log = pd.read_csv(log_path,skiprows=5)
        bouts = pd.concat([
            log.loc[log['Message'] == 'Updating walking status from false to true'].reset_index(drop=True).rename({'ns_since_reboot': 'start_time'}, axis=1)['start_time'],
            log[log['Message'] == 'Updating walking status from true to false'].reset_index(drop=True).rename({'ns_since_reboot': 'stop_time'}, axis=1)['stop_time']
        ], axis=1).values.tolist()
        ## Labels

        csv_path = os.path.join(DATA_DIR, session_name, 'accelerometer_data.csv')
        if not os.path.exists(csv_path):
            return jsonify({'error': f'CSV file not found at {csv_path}'}), 404
        
        df = pd.read_csv(csv_path)
        df = df.iloc[::10]
        print(bouts)
        bouts = [bout for bout in bouts if (bout[0] > df['ns_since_reboot'].min() and bout[1] < df['ns_since_reboot'].max())]
        expected_columns = ['ns_since_reboot', 'x', 'y', 'z']
        if not all(col in df.columns for col in expected_columns):
            return jsonify({'error': f'Invalid CSV format. Expected columns: {expected_columns}, Found: {list(df.columns)}'}), 400
        
        data = df[expected_columns].to_dict(orient='records')
        data = {
            'bouts':bouts,
            'data': data,
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
    app.run(debug=True, port=5000)