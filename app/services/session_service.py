import time
import os
import shutil
import json
import traceback
from app.services.utils import timeit, resample
import pandas as pd
from app.exceptions import DatabaseError
from app.repositories.session_repository import SessionRepository
from app.repositories.project_repository import ProjectRepository
from app.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)

class SessionService:
    def __init__(self, get_db_connection=None, session_repository=None, project_repository=None):
        self.get_db_connection = get_db_connection
        self.session_repo: SessionRepository = session_repository
        self.project_repo: ProjectRepository = project_repository
    
    def delete_sessions_by_project(self, project_id):
        """Delete all sessions for a project"""
        return self.session_repo.delete_by_project(project_id)
    
    def delete_session_lineage_by_project(self, project_id):
        """Delete session lineage records for a project"""
        return self.session_repo.delete_lineage_by_project(project_id)

    def process_sessions_async(self, upload_id, sessions, new_project_path, project_id):
        try:
            logger.info(f"Starting async processing for upload {upload_id} with {len(sessions)} sessions")
            
            # Get new database connection for this thread
            conn = self.get_db_connection()
            
            all_created_sessions = []
            skipped_sessions = []
            
            for i, session in enumerate(sessions):
                try:
                    logger.debug(f"Processing session {i+1}/{len(sessions)}: {session['name']}")
                    
                    # First, validate the session data
                    csv_path = os.path.join(new_project_path, session['name'], 'accelerometer_data.csv')
                    
                    if not self.validate_session_data(csv_path):
                        logger.warning(f"Skipping session {session['name']} - no valid data")
                        skipped_sessions.append(session['name'])
                        
                        # Remove the invalid session directory
                        session_dir = os.path.join(new_project_path, session['name'])
                        if os.path.exists(session_dir):
                            shutil.rmtree(session_dir)
                        
                        continue  # Skip to next session
                    
                    # Look for labels.json first, then fall back to log.csv for bout extraction
                    bouts_json = '{}'
                    labels_json_path = os.path.join(new_project_path, session['name'], 'labels.json')
                    log_csv_path = os.path.join(new_project_path, session['name'], 'log.csv')
                    
                    if os.path.exists(labels_json_path):
                        try:
                            with open(labels_json_path, 'r') as f:
                                labels_data = json.load(f)
                            
                            # Extract bouts from labels.json
                            # Expected format: array of objects with "start" and "end" properties
                            bouts = []
                            
                            if isinstance(labels_data, list):
                                # Direct array of bout objects or bout arrays
                                bouts = labels_data
                            elif isinstance(labels_data, dict):
                                # Check for common keys that might contain bouts
                                if 'bouts' in labels_data:
                                    bouts = labels_data['bouts']
                                elif 'labels' in labels_data:
                                    bouts = labels_data['labels']
                                elif 'smoking_bouts' in labels_data:
                                    bouts = labels_data['smoking_bouts']
                                else:
                                    # If no recognized key, try to use the whole dict as bouts
                                    bouts = labels_data
                            
                            # Validate and clean the bouts data
                            valid_bouts = []
                            for bout in bouts:
                                if isinstance(bout, dict) and 'start' in bout and 'end' in bout:
                                    # Handle object format: {"start": 123, "end": 456}
                                    start_time = bout['start']
                                    end_time = bout['end']
                                    if isinstance(start_time, (int, float)) and isinstance(end_time, (int, float)):
                                        # Convert to array format [start, end] for consistency with existing code
                                        bout_array = [start_time, end_time]
                                        # Add label and confidence if present
                                        if 'label' in bout:
                                            bout_array.append(bout['label'])
                                        if 'confidence' in bout:
                                            bout_array.append(bout['confidence'])
                                        valid_bouts.append(bout_array)
                                elif isinstance(bout, list) and len(bout) >= 2:
                                    # Handle array format: [start, end] or [start, end, label, confidence]
                                    if isinstance(bout[0], (int, float)) and isinstance(bout[1], (int, float)):
                                        valid_bouts.append(bout)
                            
                            bouts_json = json.dumps(valid_bouts)
                            logger.info(f"Loaded {len(valid_bouts)} valid bouts from labels.json for {session['name']}")
                            
                        except Exception as e:
                            logger.error(f"Error processing labels.json file for bouts in session {session['name']}: {e}", exc_info=True)
                            bouts_json = '[]'
                    
                    elif os.path.exists(log_csv_path):
                        try:
                            log = pd.read_csv(log_csv_path, skiprows=5)
                            
                            if 'message' in log.columns:
                                log = log.rename(columns={'message': 'Message'})
                                
                            # Extract start and stop transitions
                            start_transitions = log.loc[log['Message'] == 'Updating walking status from false to true'].reset_index(drop=True)['ns_since_reboot'].tolist()
                            stop_transitions = log.loc[log['Message'] == 'Updating walking status from true to false'].reset_index(drop=True)['ns_since_reboot'].tolist()
                            
                            # Handle cases where session starts with "true to false" or ends with "false to true"
                            bouts = []
                            
                            # If we have stop transitions but no start transitions, or first stop comes before first start
                            if stop_transitions and (not start_transitions or stop_transitions[0] < start_transitions[0]):
                                # Remove the first stop transition (session started in walking state)
                                stop_transitions = stop_transitions[1:]
                            
                            # If we have start transitions but no stop transitions, or last start comes after last stop
                            if start_transitions and (not stop_transitions or start_transitions[-1] > (stop_transitions[-1] if stop_transitions else 0)):
                                # Remove the last start transition (session ended in walking state)
                                start_transitions = start_transitions[:-1]
                            
                            # Now pair up the remaining transitions
                            min_length = min(len(start_transitions), len(stop_transitions))
                            for i in range(min_length):
                                bouts.append([start_transitions[i], stop_transitions[i]])
                            
                            bouts_json = json.dumps(bouts)
                            logger.info(f"Extracted {len(bouts)} valid bouts from log.csv for {session['name']}")
                            
                        except Exception as e:
                            logger.error(f"Error processing log file for bouts in session {session['name']}: {e}", exc_info=True)
                            bouts_json = '[]'
                    
                    # Preprocess data
                    project_path = new_project_path
                    session_name = session['name']

                    # Auto-split session on time gaps larger than 30 minutes
                    created_sessions = self.preprocess_and_split_session_on_upload(
                        session_name=session_name,
                        project_path=project_path,
                        project_id=project_id,
                        bouts_json=bouts_json,
                        conn=conn
                    )

                    # Only add to all_created_sessions if sessions were actually created
                    if created_sessions:
                        all_created_sessions.extend(created_sessions)
                    
                    logger.debug(f"Completed processing {session['name']}, created {len(created_sessions)} sessions")
                        
                except Exception as e:
                    logger.error(
                        f"Error processing session {session['name']}: {e}", 
                        exc_info=True,
                        extra={
                            'session_name': session['name'],
                            'upload_id': upload_id,
                            'project_id': project_id
                        }
                    )
                    continue  # Skip this session and continue with others
            
            logger.info(f"Async processing complete for upload {upload_id}. Created {len(all_created_sessions)} sessions, skipped {len(skipped_sessions)} sessions")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Critical error in async processing for upload {upload_id}: {e}", exc_info=True)
            if 'conn' in locals() and conn:
                try:
                    conn.close()
                except:
                    pass
    
    @timeit
    def validate_session_data(self, csv_path, min_rows=10):
        """
        Validate that the accelerometer data file contains valid data.
        
        Args:
            csv_path: Path to the accelerometer_data.csv file
            min_rows: Minimum number of data rows required
        
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            # Check if file exists and has content
            if not os.path.exists(csv_path):
                logger.warning(f"Data file does not exist: {csv_path}")
                return False
            
            # Check file size (empty files or very small files are invalid)
            file_size = os.path.getsize(csv_path)
            if file_size < 100:  # Less than 100 bytes is likely empty or just headers
                logger.warning(f"Data file is too small ({file_size} bytes): {csv_path}")
                return False
            
            # Try to read the CSV and validate content
            df = pd.read_csv(csv_path, nrows=1000) # tested to save ~1 second per file
            expected_columns = ['ns_since_reboot', 'x', 'y', 'z']
            
            # Check if required columns exist
            if not all(col in df.columns for col in expected_columns):
                logger.warning(f"Invalid CSV format in {csv_path}. Expected columns: {expected_columns}, Found: {list(df.columns)}")
                return False
            
            # Check if we have enough data rows
            if len(df) < min_rows:
                logger.warning(f"Insufficient data rows ({len(df)}) in {csv_path}. Minimum required: {min_rows}")
                return False
            # Check for valid timestamp data (not all NaN or zeros)
            if df['ns_since_reboot'].isna().all() or (df['ns_since_reboot'] == 0).all():
                logger.warning(f"Invalid timestamp data in {csv_path}")
                return False
            
            # Check for valid accelerometer data (not all NaN)
            accel_cols = ['x', 'y', 'z']
            if df[accel_cols].isna().all().all():
                logger.warning(f"No valid accelerometer data in {csv_path}")
                return False
            
            logger.debug(f"Data validation passed for {csv_path}: {len(df)} rows")
            return True
            
        except Exception as e:
            logger.error(f"Error validating data in {csv_path}: {e}", exc_info=True)
            return False
    
    def preprocess_and_split_session_on_upload(self, session_name, project_path, project_id, bouts_json, conn, gyro=False):
        """
        Automatically split a session based on time gaps during upload.
        
        Args:
            session_name: Name of the session to potentially split
            project_path: Path to the project directory
            project_id: Database project ID
            bouts_json: JSON string of bouts data
            conn: Database connection
        
        Returns:
            List of session names that were created (empty list if session was invalid/skipped)
        """
        try:
            from app.services.utils import load_dataframe_from_csv, get_sample_rate_from_dataframe, check_sample_rate_consistency
            
            accel_csv_path = os.path.join(project_path, session_name, 'accelerometer_data.csv')
            gyro_csv_path = os.path.join(project_path, session_name, 'gyroscope_data.csv')

            df = load_dataframe_from_csv(accel_csv_path, column_prefix='accel')

            if os.path.exists(gyro_csv_path):
                gyro = True

                accel_sample_rate = get_sample_rate_from_dataframe(df)

                gyro_df = load_dataframe_from_csv(gyro_csv_path, column_prefix='gyro')
                gyro_sample_rate = get_sample_rate_from_dataframe(gyro_df)

                check_sample_rate_consistency(accel_sample_rate, gyro_sample_rate)
                merge_tolerance = min(accel_sample_rate, gyro_sample_rate)

                df = pd.merge_asof(
                    df.sort_values('ns_since_reboot'),
                    gyro_df.sort_values('ns_since_reboot'),
                    on='ns_since_reboot',
                    tolerance=int(1e9 / merge_tolerance),
                    direction='nearest'
                )

                df = df.dropna()

            gap_threshold_minutes = 30
            gap_threshold_ns = gap_threshold_minutes * 60 * 1_000_000_000
            df = df.sort_values('ns_since_reboot').reset_index(drop=True)
            time_diffs = df['ns_since_reboot'].diff()
            gap_indices = time_diffs[time_diffs > gap_threshold_ns].index

            if len(gap_indices) == 0:
                logger.debug(f"No time gaps found in session {session_name}, proceeding without splitting")
                df = resample(df)
                df[['ns_since_reboot', 'accel_x', 'accel_y', 'accel_z']].to_csv(accel_csv_path, index=False)
                if gyro:
                    df[['ns_since_reboot', 'gyro_x', 'gyro_y', 'gyro_z']].to_csv(gyro_csv_path, index=False)
                logger.debug(f"Resampled data for session {session_name}")
                # Parse bouts data
                try:
                    parent_bouts = json.loads(bouts_json or '[]')
                    if isinstance(parent_bouts, str):
                        parent_bouts = json.loads(parent_bouts)
                except json.JSONDecodeError:
                    parent_bouts = []

                logger.debug(f"Parsed {len(parent_bouts)} bouts for single session {session_name}")
                segment_bouts = [{'start':segment_bout[0],'end':segment_bout[1],'label':'smoking'} for segment_bout in parent_bouts]
                
                return self._insert_single_session(session_name, project_id, json.dumps(segment_bouts), conn)

            split_points = []
            for idx in gap_indices:
                if idx > 0 and idx < len(df) - 1:
                    split_points.append(float(df.loc[idx, 'ns_since_reboot']))
            split_points = sorted(set(float(p) for p in split_points))
            split_indices = []
            for point in split_points:
                df['time_diff'] = abs(df['ns_since_reboot'] - point)
                split_index = df['time_diff'].idxmin()
                if split_index > 0 and split_index < len(df) - 1:
                    split_indices.append(split_index)
            split_indices = sorted(set(split_indices))
            split_indices = [0] + split_indices + [len(df)]
            
            segments = []
            for i in range(len(split_indices) - 1):
                start_index = split_indices[i]
                end_index = split_indices[i + 1]
                if start_index < end_index:
                    segment_df = df.iloc[start_index:end_index]
                    if not segment_df.empty:
                        logger.debug(f"Created segment {i + 1} with {len(segment_df)} rows for session {session_name}")
                        segment_df = resample(segment_df)
                        segments.append(segment_df)
                    else:
                        logger.warning(f"Segment {i + 1} is empty, skipping for session {session_name}")
                else:
                    logger.warning(f"Invalid segment indices for session {session_name}: start={start_index}, end={end_index}")
            
            # Define time ranges for each segment
            segment_ranges = []
            for segment in segments:
                start_time = segment['ns_since_reboot'].min()
                end_time = segment['ns_since_reboot'].max()
                segment_ranges.append((start_time, end_time))
            
            # Parse bouts data
            try:
                parent_bouts = json.loads(bouts_json or '[]')
                if isinstance(parent_bouts, str):
                    parent_bouts = json.loads(parent_bouts)
            except json.JSONDecodeError:
                parent_bouts = []
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
                new_name = self.generate_unique_session_name_upload(session_name, project_path, conn, project_id)
                new_dir = os.path.join(project_path, new_name)
                
                # Create directory and save CSV
                os.makedirs(new_dir, exist_ok=True)
                segment[['ns_since_reboot', 'accel_x', 'accel_y', 'accel_z']].to_csv(os.path.join(new_dir, 'accelerometer_data.csv'), index=False)
                if gyro:
                    segment[['ns_since_reboot', 'gyro_x', 'gyro_y', 'gyro_z']].to_csv(os.path.join(new_dir, 'gyroscope_data.csv'), index=False)
                
                # Copy log file if it exists
                log_path = os.path.join(project_path, session_name, 'log.csv')
                if os.path.exists(log_path):
                    shutil.copy(log_path, os.path.join(new_dir, 'log.csv'))
                    
                # Copy labels.json file if it exists
                labels_path = os.path.join(project_path, session_name, 'labels.json')
                if os.path.exists(labels_path):
                    shutil.copy(labels_path, os.path.join(new_dir, 'labels.json'))
                
                segment_bouts[i] = [{'start':segment_bout[0],'end':segment_bout[1],'label':'smoking'} for segment_bout in segment_bouts[i]]
                
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
            logger.error(
                f"Failed to auto-split session '{session_name}' in project {project_id}: {str(e)}", 
                exc_info=True,
                extra={
                    'session_name': session_name,
                    'project_id': project_id,
                    'project_path': project_path,
                    'error_type': type(e).__name__,
                    'traceback': traceback.format_exc()
                }
            )
            # Fallback: insert original session
            try:
                logger.info(f"Attempting fallback: inserting original session '{session_name}' without splitting")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sessions (project_id, session_name, status, keep, bouts)
                    VALUES (%s, %s, %s, %s, %s)
                """, (project_id, session_name, 'Initial', None, bouts_json))
                logger.info(f"Successfully inserted fallback session '{session_name}'")
                return [session_name]
            except Exception as fallback_error:
                logger.error(
                    f"Fallback insertion also failed for session '{session_name}': {str(fallback_error)}", 
                    exc_info=True,
                    extra={
                        'session_name': session_name,
                        'project_id': project_id,
                        'original_error': str(e),
                        'fallback_error': str(fallback_error)
                    }
                )
                return []
    
    def _insert_single_session(self, session_name, project_id, bouts_json, conn):
        """
        Insert a single session into the database.
        """
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (project_id, session_name, status, keep, bouts)
                VALUES (%s, %s, %s, %s, %s)
            """, (project_id, session_name, 'Initial', None, bouts_json))
            cursor.close()
            logger.debug(f"Successfully inserted single session '{session_name}' for project {project_id}")
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

    def generate_unique_session_name_upload(self, original_name, project_path, conn, project_id):
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
    
    def generate_unique_session_name(self, original_name, project_path, project_id):
        """Generate a unique session name by adding numeric suffixes"""
        base_counter = 1
        while True:
            candidate_name = f"{original_name}.{base_counter}"
            
            # Check filesystem for collision
            if os.path.exists(os.path.join(project_path, candidate_name)):
                base_counter += 1
                continue
                
            # Check database for collision
            conn = self.get_db_connection()
            if conn is None:
                raise DatabaseError('Database connection failed')
            
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT COUNT(*) FROM sessions 
                    WHERE session_name = %s AND project_id = %s
                """, (candidate_name, project_id))
                count = cursor.fetchone()[0]
                
                if count == 0:
                    return candidate_name
                
                base_counter += 1
            finally:
                cursor.close()
                conn.close()

    def get_sessions(self, project_id=None, show_split=False):
        """Get sessions, optionally filtered by project and split status"""
        conn = self.get_db_connection()
        
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
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
            return sessions
        finally:
            cursor.close()
            conn.close()
    
    def get_session_details(self, session_id):
        """Get detailed information for a specific session"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT s.session_id, s.session_name, s.status, s.keep, s.verified, s.bouts,
                    p.project_id, p.project_name, p.path AS project_path
                FROM sessions s
                JOIN projects p ON s.project_id = p.project_id
                WHERE s.session_id = %s
            """, (session_id,))
            
            session_info = cursor.fetchone()
            return session_info
        finally:
            cursor.close()
            conn.close()
    
    def get_all_sessions_with_details(self, include_discarded=False):
        """Get all sessions with project and participant information"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Only include non-discarded sessions unless specifically requested
            keep_condition = "" if include_discarded else "WHERE s.keep != 0 OR s.keep IS NULL"
            
            cursor.execute(f"""
                SELECT 
                    s.session_id, 
                    s.session_name, 
                    s.status, 
                    s.keep, 
                    s.verified,
                    s.bouts,
                    p.project_id,
                    p.project_name, 
                    p.path AS project_path,
                    pt.participant_code,
                    pt.participant_id
                FROM sessions s
                JOIN projects p ON s.project_id = p.project_id
                JOIN participants pt ON p.participant_id = pt.participant_id
                {keep_condition}
                ORDER BY pt.participant_code, p.project_name, s.session_name
            """)
            
            sessions = cursor.fetchall()
            return sessions
        finally:
            cursor.close()
            conn.close()
    
    def get_session_data_by_session_name(self, session_name):
        """Get session data by session name"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT session_name, status, keep, label, segments
                FROM sessions
                WHERE session_name = %s
            """, (session_name,))
            metadata = cursor.fetchone()
            return metadata
        finally:
            cursor.close()
            conn.close()
    
    def update_session(self, session_id, status, keep, bouts, verified):
        """Update session data including status, keep flag, bouts, and verified status"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE sessions
                SET status = %s, keep = %s, bouts = %s, verified = %s
                WHERE session_id = %s
            """, (status, keep, bouts, verified, session_id))
            
            rows_affected = cursor.rowcount
            conn.commit()
            return rows_affected
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f'Failed to update session: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    def delete_session_lineage_by_project(self, project_id):
        """Delete all session lineage records for sessions in a project"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                DELETE sl FROM session_lineage sl
                JOIN sessions s ON (sl.child_session_id = s.session_id OR sl.parent_session_id = s.session_id)
                WHERE s.project_id = %s
            """, (project_id,))
            
            lineage_deleted = cursor.rowcount
            conn.commit()
            return lineage_deleted
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f'Failed to delete session lineage: {str(e)}')
        finally:
            cursor.close()
            conn.close()

    def delete_sessions_by_project(self, project_id):
        """Delete all sessions for a project"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                DELETE FROM sessions WHERE project_id = %s
            """, (project_id,))
            
            sessions_deleted = cursor.rowcount
            conn.commit()
            return sessions_deleted
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f'Failed to delete sessions: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    def split_session(self, session_id, session_info, new_sessions):
        """Split a session into multiple new sessions and mark original as split"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        try:
            with conn.cursor() as cursor:
                # Store the original session ID before deleting it
                parent_id = session_id
                created_sessions = []
                
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
                    created_sessions.append(child_id)

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
                        is_visible = 0
                    WHERE session_id = %s
                """, (session_id,))
                
            conn.commit()
            return created_sessions
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f'Failed to split session: {str(e)}')
        finally:
            conn.close()