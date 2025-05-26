from flask import Flask, jsonify, send_from_directory, request
from werkzeug.utils import secure_filename
import os
import pandas as pd
import mysql.connector
from mysql.connector import Error
import json
import shutil
from datetime import datetime
import numpy as np

app = Flask(__name__, static_folder='static')

# Directory containing session data
DATA_DIR = '~/.delta/data'

# MySQL configuration
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Password123!',
    'database': 'smoking_data'
}

# Initialize MySQL connection
def get_db_connection():
    try:
        return mysql.connector.connect(**MYSQL_CONFIG)
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

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
        # Handle multipart form data for file uploads
        if 'files' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        # Get form data
        project_name = request.form.get('name')
        participant_code = request.form.get('participant')
        folder_name = request.form.get('folderName')
        
        if not all([project_name, participant_code, folder_name]):
            return jsonify({'error': 'Missing required fields: name, participant, or folderName'}), 400
        
        # Get uploaded files
        uploaded_files = request.files.getlist('files')
        if not uploaded_files:
            return jsonify({'error': 'No files uploaded'}), 400

        # Get database connection
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor()

        # First check if participant exists
        cursor.execute("""
            SELECT participant_id FROM participants WHERE participant_code = %s
        """, (participant_code,))
        participant = cursor.fetchone()

        if participant:
            # Use existing participant
            participant_id = participant[0]
        else:
            # Create new participant
            cursor.execute("""
                INSERT INTO participants (participant_code) 
                VALUES (%s)
            """, (participant_code,))
            participant_id = cursor.lastrowid

        # Create new directory in central data store
        central_data_dir = os.path.expanduser(DATA_DIR)
        os.makedirs(central_data_dir, exist_ok=True)
        
        # Create a unique project directory name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        project_dir_name = f"{project_name}_{participant_code}_{timestamp}"
        new_project_path = os.path.join(central_data_dir, project_dir_name)
        
        # Create the project directory structure from uploaded files
        try:
            os.makedirs(new_project_path, exist_ok=True)
            
            # Process uploaded files and recreate directory structure
            for file in uploaded_files:
                if file.filename and file.filename != '':
                    # Get relative path within the selected folder
                    relative_path = file.filename
                    if '/' in relative_path:
                        # Remove the root folder name from the path since we're creating our own structure
                        path_parts = relative_path.split('/')
                        if len(path_parts) > 1:
                            relative_path = '/'.join(path_parts[1:])  # Remove the first part (root folder name)
                    
                    # Create full file path
                    file_path = os.path.join(new_project_path, relative_path)
                    
                    # Create directories if they don't exist
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    
                    # Save the file
                    file.save(file_path)
                    
        except Exception as e:
            # Clean up on error
            if os.path.exists(new_project_path):
                shutil.rmtree(new_project_path)
            return jsonify({'error': f'Failed to save uploaded files: {str(e)}'}), 500

        # Insert project with the participant_id
        cursor.execute("""
            INSERT INTO projects (project_name, participant_id, path)
            VALUES (%s, %s, %s)
        """, (project_name, participant_id, new_project_path))

        # Get the new project_id
        project_id = cursor.lastrowid

        # Find all session directories in the uploaded project
        sessions = []
        if os.path.exists(new_project_path):
            for item in os.listdir(new_project_path):
                item_path = os.path.join(new_project_path, item)
                if os.path.isdir(item_path):
                    accel_file = os.path.join(item_path, 'accelerometer_data.csv')
                    if os.path.exists(accel_file):
                        sessions.append({'name': item, 'file': 'accelerometer_data.csv'})
            
            # Sort sessions by date/time in the name
            try:
                sessions.sort(key=lambda s: datetime.strptime('_'.join(s['name'].split('_')[:4]), '%Y-%m-%d_%H_%M_%S'))
            except:
                # If sorting fails, keep original order
                pass

            # Process each session (with automatic splitting on time gaps)
            all_created_sessions = []
            for session in sessions:
                try:
                    # Look for log.csv to extract bouts data
                    bouts_json = '{}'
                    log_path = os.path.join(new_project_path, session['name'], 'log.csv')
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
                    
                    # Auto-split session on time gaps larger than 30 minutes
                    created_sessions = auto_split_session_on_upload(
                        session['name'], new_project_path, project_id, bouts_json, conn
                    )
                    all_created_sessions.extend(created_sessions)
                    
                except Exception as e:
                    print(f"Error processing session {session['name']}: {e}")
                    continue  # Skip this session and continue with others
                    
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'message': 'Project uploaded successfully',
            'project_id': project_id,
            'participant_id': participant_id,
            'central_path': new_project_path,
            'sessions_created': all_created_sessions,
            'total_sessions': len(all_created_sessions),
            'auto_split_applied': len(all_created_sessions) > len(sessions) if sessions else False,
            'files_uploaded': len(uploaded_files)
        })
        
    except Exception as e:
        print(f"Error in upload_new_project: {e}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/sessions')
def list_sessions():
    try:
        project_id = request.args.get('project_id')
        show_split = request.args.get('show_split', '0') == '1'  # Optional parameter to show split sessions
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Base query filtering out split sessions
        visibility_condition = "" if show_split else "AND (s.status != 'Split' OR s.status IS NULL) "
        
        if project_id:
            # Get sessions for a specific project
            cursor.execute(f"""
                SELECT s.session_id, s.session_name, s.status, s.keep,
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
                SELECT s.session_id, s.session_name, s.status, s.keep,
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
            SELECT s.session_id, s.session_name, s.status, s.keep, s.bouts,
                p.project_id, p.project_name, p.path AS project_path
            FROM sessions s
            JOIN projects p ON s.project_id = p.project_id
            WHERE s.session_id = %s
        """, (session_id,))
        
        session_info = cursor.fetchone()
        cursor.close()
        conn.close()
        print(session_id,session_info)
        if not session_info:
            return jsonify({'error': 'Session not found'}), 404
        
        # Use the project path stored in the description field
        project_path = session_info['project_path']
        session_name = session_info['session_name']
        
        # Path to the session's data files
        csv_path = os.path.join(project_path, session_name, 'accelerometer_data.csv')
        print(csv_path)
        if not os.path.exists(csv_path):
            return jsonify({'error': f'CSV file not found at {csv_path}'}), 404
        
        # Continue with your existing code to process the CSV file...
        df = pd.read_csv(csv_path)
        df = df.iloc[::20]  # Downsampling
        
        # Extract bouts from log file if it exists
        bouts = session_info['bouts']
        
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
@app.route('/api/session/<int:session_id>/metadata', methods=['PUT'])
def update_session_metadata(session_id):
    try:
        data = request.get_json()
        status = data.get('status')
        keep = data.get('keep')
        bouts = data.get('bouts')
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        # Update the SQL query to use session_id
        cursor.execute("""
            UPDATE sessions
            SET status = %s, keep = %s, bouts = %s
            WHERE session_id = %s
        """, (status, keep, bouts, session_id))
        
        # Check if any rows were updated
        rows_affected = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        if rows_affected == 0:
            return jsonify({'warning': 'No session found with that ID'}), 200
            
        return jsonify({'message': 'Metadata updated', 'rows_affected': rows_affected})
    except Exception as e:
        print(f"Error updating session metadata: {e}")
        return jsonify({'error': str(e)}), 500

# Split session
@app.route('/api/session/<int:session_id>/split', methods=['POST'])
def split_session(session_id):
    try:
        data = request.get_json()
        split_points = data.get('split_points')  # Array of ns_since_reboot timestamps
        if not split_points or not isinstance(split_points, list) or len(split_points) == 0:
            return jsonify({'error': 'At least one split point required'}), 400

        # First get session info including project path
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.session_id, s.session_name, s.status, s.keep, s.project_id, s.bouts, 
                   p.path AS project_path
            FROM sessions s
            JOIN projects p ON s.project_id = p.project_id
            WHERE s.session_id = %s
        """, (session_id,))
        
        session_info = cursor.fetchone()
        if not session_info:
            conn.close()
            return jsonify({'error': 'Session not found'}), 404
        
        session_name = session_info['session_name']
        project_path = session_info['project_path']
        
        # Parse the bouts from the session info
        try:
            parent_bouts = json.loads(session_info['bouts'] or '[]')
            # Convert to list if it's not already
            if isinstance(parent_bouts, str):
                parent_bouts = json.loads(parent_bouts)
        except json.JSONDecodeError:
            parent_bouts = []
        
        # Read original CSV from the project directory
        csv_path = os.path.join(project_path, session_name, 'accelerometer_data.csv')
        if not os.path.exists(csv_path):
            return jsonify({'error': f'CSV file not found at {csv_path}'}), 404
        
        df = pd.read_csv(csv_path)
        expected_columns = ['ns_since_reboot', 'x', 'y', 'z']
        if not all(col in df.columns for col in expected_columns):
            return jsonify({'error': f'Invalid CSV format. Expected columns: {expected_columns}, Found: {list(df.columns)}'}), 400

        # Find split indices
        split_points = sorted(set(float(p) for p in split_points))  # Ensure unique and sorted
        split_indices = []
        split_timestamps = []  # Store the actual timestamps at split points
        for point in split_points:
            df['time_diff'] = abs(df['ns_since_reboot'] - point)
            split_index = df['time_diff'].idxmin()
            if split_index == 0 or split_index == len(df) - 1:
                continue  # Skip points at start or end
            split_indices.append(split_index)
            split_timestamps.append(df.loc[split_index, 'ns_since_reboot'])
        split_indices = sorted(set(split_indices))  # Ensure unique and sorted
        split_timestamps = sorted(set(split_timestamps))  # Ensure unique and sorted

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

        # Define time ranges for each segment
        segment_ranges = []
        for i, segment in enumerate(segments):
            start_time = segment['ns_since_reboot'].min()
            end_time = segment['ns_since_reboot'].max()
            segment_ranges.append((start_time, end_time))
        
        # Assign bouts to segments based on time ranges
        segment_bouts = [[] for _ in segments]
        
        for bout in parent_bouts:
            # Each bout is [start_time, stop_time]
            if len(bout) != 2:
                continue  # Skip malformed bouts
                
            bout_start = bout[0]
            bout_end = bout[1]
            
            for i, (segment_start, segment_end) in enumerate(segment_ranges):
                # If bout is entirely within segment
                if segment_start <= bout_start <= segment_end and segment_start <= bout_end <= segment_end:
                    segment_bouts[i].append(bout)
                    break
                # If bout overlaps with segment start
                elif bout_start < segment_start and segment_start <= bout_end <= segment_end:
                    # Adjust bout to start at segment boundary
                    adjusted_bout = [float(segment_start), float(bout_end)]
                    segment_bouts[i].append(adjusted_bout)
                    break
                # If bout overlaps with segment end
                elif segment_start <= bout_start <= segment_end and bout_end > segment_end:
                    # Adjust bout to end at segment boundary
                    adjusted_bout = [float(bout_start), float(segment_end)]
                    segment_bouts[i].append(adjusted_bout)
                    break
                # If bout spans entire segment
                elif bout_start < segment_start and bout_end > segment_end:
                    # Create a bout for the entire segment
                    adjusted_bout = [float(segment_start), float(segment_end)]
                    segment_bouts[i].append(adjusted_bout)
                    break

        # Create new session names and directories
        new_sessions = []
        for i, segment in enumerate(segments):
            # Generate unique name instead of using suffix
            new_name = generate_unique_session_name(session_name, project_path, conn, session_info['project_id'])
            new_dir = os.path.join(project_path, new_name)
            
            os.makedirs(new_dir)
            segment.to_csv(os.path.join(new_dir, 'accelerometer_data.csv'), index=False)
            new_sessions.append({
                'name': new_name,
                'bouts': segment_bouts[i]
            })

        # Copy original log file to new directories
        log_path = os.path.join(project_path, session_name, 'log.csv')
        if os.path.exists(log_path):
            for session_data in new_sessions:
                shutil.copy(log_path, os.path.join(project_path, session_data['name'], 'log.csv'))
        else:
            print(f"Log file not found at {log_path}. Skipping copy.")
            
        # Insert new sessions into database
        with conn.cursor() as cursor:
            # Store the original session ID before deleting it
            parent_id = session_id
            for session_data in new_sessions:
                # Keep the same project_id
                cursor.execute("""
                    INSERT INTO sessions (project_id, session_name, status, keep, bouts)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    session_info['project_id'], 
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
            """, (session_id,))        
        conn.commit()
        conn.close()

        # Delete original session directory
        shutil.rmtree(os.path.join(project_path, session_name))

        return jsonify({
            'message': 'Session split successfully', 
            'new_sessions': [s['name'] for s in new_sessions]
        })
    except Exception as e:
        print(f"Error splitting session: {e}")
        return jsonify({'error': str(e)}), 500
def generate_unique_session_name(original_name, project_path, conn, project_id):
    """Generate a unique session name by adding numeric suffixes"""
    base_counter = 1
    while True:
        candidate_name = f"{original_name}.{base_counter}"
        
        # Check filesystem for collision
        if os.path.exists(os.path.join(project_path, candidate_name)):
            base_counter += 1
            continue
            
        # Check database for collision
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM sessions 
            WHERE session_name = %s AND project_id = %s
        """, (candidate_name, project_id))
        count = cursor.fetchone()[0]
        cursor.close()
        
        if count == 0:
            return candidate_name
        
        base_counter += 1

@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

# Detect time gaps larger than 30 minutes in accelerometer data and return split points
def detect_time_gaps(csv_path, gap_threshold_minutes=30):
    """
    Detect time gaps larger than the threshold in accelerometer data.
    Returns list of timestamps where splits should occur.
    
    Args:
        csv_path: Path to the accelerometer_data.csv file
        gap_threshold_minutes: Minimum gap size in minutes to trigger a split
    
    Returns:
        List of ns_since_reboot timestamps where splits should occur
    """
    try:
        df = pd.read_csv(csv_path)
        expected_columns = ['ns_since_reboot', 'x', 'y', 'z']
        if not all(col in df.columns for col in expected_columns):
            print(f"Invalid CSV format in {csv_path}. Expected columns: {expected_columns}, Found: {list(df.columns)}")
            return []
        
        if len(df) < 2:
            return []
        
        # Convert gap threshold from minutes to nanoseconds
        gap_threshold_ns = gap_threshold_minutes * 60 * 1_000_000_000  # 30 minutes in nanoseconds
        
        # Sort by timestamp to ensure proper order
        df = df.sort_values('ns_since_reboot').reset_index(drop=True)
        
        # Calculate time differences between consecutive readings
        time_diffs = df['ns_since_reboot'].diff()
        
        # Find gaps larger than threshold
        gap_indices = time_diffs[time_diffs > gap_threshold_ns].index
        
        # Get the timestamps where gaps end (start of new segment)
        split_points = []
        for idx in gap_indices:
            if idx > 0 and idx < len(df) - 1:  # Don't split at very beginning or end
                split_points.append(float(df.loc[idx, 'ns_since_reboot']))
        
        return split_points
        
    except Exception as e:
        print(f"Error detecting time gaps in {csv_path}: {e}")
        return []

def auto_split_session_on_upload(session_name, project_path, project_id, bouts_json, conn):
    """
    Automatically split a session based on time gaps during upload.
    
    Args:
        session_name: Name of the session to potentially split
        project_path: Path to the project directory
        project_id: Database project ID
        bouts_json: JSON string of bouts data
        conn: Database connection
    
    Returns:
        List of session names that were created (original name if no split occurred)
    """
    try:
        csv_path = os.path.join(project_path, session_name, 'accelerometer_data.csv')
        split_points = detect_time_gaps(csv_path)
        
        if not split_points:
            # No splits needed, just insert the original session
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (project_id, session_name, status, keep, bouts)
                VALUES (%s, %s, %s, %s, %s)
            """, (project_id, session_name, 'Initial', None, bouts_json))
            return [session_name]
        
        print(f"Auto-splitting session {session_name} at {len(split_points)} time gaps")
        
        # Read the CSV data
        df = pd.read_csv(csv_path)
        expected_columns = ['ns_since_reboot', 'x', 'y', 'z']
        df = df.sort_values('ns_since_reboot').reset_index(drop=True)
        
        # Parse bouts data
        try:
            parent_bouts = json.loads(bouts_json or '[]')
            if isinstance(parent_bouts, str):
                parent_bouts = json.loads(parent_bouts)
        except json.JSONDecodeError:
            parent_bouts = []
        
        # Find split indices
        split_points = sorted(set(float(p) for p in split_points))
        split_indices = []
        for point in split_points:
            df['time_diff'] = abs(df['ns_since_reboot'] - point)
            split_index = df['time_diff'].idxmin()
            if split_index > 0 and split_index < len(df) - 1:
                split_indices.append(split_index)
        split_indices = sorted(set(split_indices))
        
        if not split_indices:
            # No valid split points, insert original session
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (project_id, session_name, status, keep, bouts)
                VALUES (%s, %s, %s, %s, %s)
            """, (project_id, session_name, 'Initial', None, bouts_json))
            return [session_name]
        
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
            # Split didn't create multiple segments, insert original
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (project_id, session_name, status, keep, bouts)
                VALUES (%s, %s, %s, %s, %s)
            """, (project_id, session_name, 'Initial', None, bouts_json))
            return [session_name]
        
        # Define time ranges for each segment
        segment_ranges = []
        for segment in segments:
            start_time = segment['ns_since_reboot'].min()
            end_time = segment['ns_since_reboot'].max()
            segment_ranges.append((start_time, end_time))
        
        # Assign bouts to segments based on time ranges
        segment_bouts = [[] for _ in segments]
        for bout in parent_bouts:
            if len(bout) != 2:
                continue
                
            bout_start = bout[0]
            bout_end = bout[1]
            
            for i, (segment_start, segment_end) in enumerate(segment_ranges):
                # If bout is entirely within segment
                if segment_start <= bout_start <= segment_end and segment_start <= bout_end <= segment_end:
                    segment_bouts[i].append(bout)
                    break
                # If bout overlaps with segment start
                elif bout_start < segment_start and segment_start <= bout_end <= segment_end:
                    adjusted_bout = [float(segment_start), float(bout_end)]
                    segment_bouts[i].append(adjusted_bout)
                    break
                # If bout overlaps with segment end
                elif segment_start <= bout_start <= segment_end and bout_end > segment_end:
                    adjusted_bout = [float(bout_start), float(segment_end)]
                    segment_bouts[i].append(adjusted_bout)
                    break
                # If bout spans entire segment
                elif bout_start < segment_start and bout_end > segment_end:
                    adjusted_bout = [float(segment_start), float(segment_end)]
                    segment_bouts[i].append(adjusted_bout)
                    break
        
        # Create new session names and directories
        new_sessions = []
        cursor = conn.cursor()
        
        for i, segment in enumerate(segments):
            # Generate unique name
            new_name = generate_unique_session_name_upload(session_name, project_path, conn, project_id)
            new_dir = os.path.join(project_path, new_name)
            
            # Create directory and save CSV
            os.makedirs(new_dir, exist_ok=True)
            segment.to_csv(os.path.join(new_dir, 'accelerometer_data.csv'), index=False)
            
            # Copy log file if it exists
            log_path = os.path.join(project_path, session_name, 'log.csv')
            if os.path.exists(log_path):
                shutil.copy(log_path, os.path.join(new_dir, 'log.csv'))
            
            # Insert session into database
            cursor.execute("""
                INSERT INTO sessions (project_id, session_name, status, keep, bouts)
                VALUES (%s, %s, %s, %s, %s)
            """, (project_id, new_name, 'Initial', None, json.dumps(segment_bouts[i])))
            
            new_sessions.append(new_name)
        
        # Remove the original session directory
        original_dir = os.path.join(project_path, session_name)
        if os.path.exists(original_dir):
            shutil.rmtree(original_dir)
        
        return new_sessions
        
    except Exception as e:
        print(f"Error auto-splitting session {session_name}: {e}")
        # Fallback: insert original session
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (project_id, session_name, status, keep, bouts)
                VALUES (%s, %s, %s, %s, %s)
            """, (project_id, session_name, 'Initial', None, bouts_json))
            return [session_name]
        except:
            return []

def generate_unique_session_name_upload(original_name, project_path, conn, project_id):
    """Generate a unique session name by adding numeric suffixes (for upload process)"""
    base_counter = 1
    while True:
        candidate_name = f"{original_name}.{base_counter}"
        
        # Check filesystem for collision
        if os.path.exists(os.path.join(project_path, candidate_name)):
            base_counter += 1
            continue
            
        # Check database for collision
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM sessions 
            WHERE session_name = %s AND project_id = %s
        """, (candidate_name, project_id))
        count = cursor.fetchone()[0]
        cursor.close()
        
        if count == 0:
            return candidate_name
        
        base_counter += 1

# Delete project
@app.route('/api/project/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # First, get project information including path
        cursor.execute("""
            SELECT p.project_id, p.project_name, p.path, p.participant_id,
                   pt.participant_code
            FROM projects p
            JOIN participants pt ON p.participant_id = pt.participant_id
            WHERE p.project_id = %s
        """, (project_id,))
        
        project_info = cursor.fetchone()
        if not project_info:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Project not found'}), 404
        
        project_path = project_info['path']
        participant_id = project_info['participant_id']
        
        # Get list of sessions before deletion for cleanup
        cursor.execute("""
            SELECT session_name FROM sessions WHERE project_id = %s
        """, (project_id,))
        sessions_to_delete = cursor.fetchall()
        
        # Delete session lineage records first (due to foreign key constraints)
        cursor.execute("""
            DELETE sl FROM session_lineage sl
            JOIN sessions s ON (sl.child_session_id = s.session_id OR sl.parent_session_id = s.session_id)
            WHERE s.project_id = %s
        """, (project_id,))
        
        # Delete sessions (this will cascade due to foreign key)
        cursor.execute("""
            DELETE FROM sessions WHERE project_id = %s
        """, (project_id,))
        sessions_deleted = cursor.rowcount
        
        # Delete the project
        cursor.execute("""
            DELETE FROM projects WHERE project_id = %s
        """, (project_id,))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Project not found or already deleted'}), 404
        
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
        cursor.close()
        conn.close()
        
        # Delete project directory from filesystem
        import shutil
        directory_deleted = False
        if project_path and os.path.exists(project_path):
            try:
                shutil.rmtree(project_path)
                directory_deleted = True
                print(f"Deleted project directory: {project_path}")
            except Exception as e:
                print(f"Warning: Could not delete project directory {project_path}: {e}")
                # Don't fail the entire operation if directory deletion fails
        
        return jsonify({
            'message': 'Project deleted successfully',
            'project_id': project_id,
            'project_name': project_info['project_name'],
            'participant_code': project_info['participant_code'],
            'sessions_deleted': sessions_deleted,
            'directory_deleted': directory_deleted,
            'participant_deleted': participant_deleted,
            'directory_path': project_path
        })
        
    except Exception as e:
        print(f"Error deleting project: {e}")
        return jsonify({'error': f'Failed to delete project: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5050)