from flask import Flask, jsonify, send_from_directory, request
import os
import pandas as pd
import mysql.connector
from mysql.connector import Error
import json

app = Flask(__name__, static_folder='static')

# Directory containing session data
DATA_DIR = 'data'

# MySQL configuration
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'app_user',  # Replace with your MySQL username
    'password': 'app_user_password',  # Replace with your MySQL password
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
        sessions.sort(key=lambda s: datetime.strptime(s['name'], '%Y-%m-%d_%H_%M_%S'))  # Sort by parsed date
        print(sessions)
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
        ], axis=1).values
        ## Labels

        csv_path = os.path.join(DATA_DIR, session_name, 'accelerometer_data.csv')
        if not os.path.exists(csv_path):
            return jsonify({'error': f'CSV file not found at {csv_path}'}), 404
        
        df = pd.read_csv(csv_path)
        df = df.iloc[::20]
        df['label'] = 0
        for bout in bouts:
            df.loc[(df['ns_since_reboot'] >= bout[0]) & (df['ns_since_reboot'] <= bout[1]), 'label'] = 40

        expected_columns = ['ns_since_reboot', 'x', 'y', 'z','label']
        if not all(col in df.columns for col in expected_columns):
            return jsonify({'error': f'Invalid CSV format. Expected columns: {expected_columns}, Found: {list(df.columns)}'}), 400
        
        data = df[expected_columns].to_dict(orient='records')



        return jsonify(data)
    except Exception as e:
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
        print(metadata)
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

@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)