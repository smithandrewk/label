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

    def load_bouts_from_labels_json(self, project_path, session) -> list:
        labels_json_path = os.path.join(project_path, session['name'], 'labels.json')
        
        try:
            with open(labels_json_path, 'r') as f:
                labels_data = json.load(f)
            
            # Ensure we always return a list
            if not isinstance(labels_data, list):
                logger.warning(f"labels.json for session {session['name']} contains non-list data: {type(labels_data)}")
                return []
            
            return labels_data
        except FileNotFoundError:
            logger.warning(f"labels.json not found for session {session['name']}, using empty bouts")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from labels.json for session {session['name']}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error loading labels.json for session {session['name']}: {e}")
            return []
        
    @timeit
    def validate_sessions(self, sessions, project_path):
        skipped_sessions = []
        for session in sessions:
            csv_path = os.path.join(project_path, session['name'], 'accelerometer_data.csv')
            if not self.validate_session_data(csv_path):
                logger.warning(f"Invalid session data for {session['name']}")
                skipped_sessions.append(session['name'])
                session_dir = os.path.join(project_path, session['name'])
                if os.path.exists(session_dir):
                    shutil.rmtree(session_dir)
            else:
                logger.info(f"Session {session['name']} data is valid")
        return skipped_sessions
    
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
    
    @timeit
    def preprocess_and_split_session_on_upload(self, session_name, project_path, project_id, parent_bouts, gyro=False):
        """
        Automatically split a session based on time gaps during upload.
        
        Args:
            session_name: Name of the session to potentially split
            project_path: Path to the project directory
            project_id: Database project ID
            bouts_json: JSON string of bouts data
        
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
                logger.debug(f"Parsed {len(parent_bouts)} parent_bouts for single session {session_name}")
                
                # Calculate start_ns and stop_ns for the whole session
                start_ns = int(df['ns_since_reboot'].min())
                stop_ns = int(df['ns_since_reboot'].max())
                
                return self.session_repo.insert_single_session(session_name, project_id, json.dumps(parent_bouts), start_ns, stop_ns)

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
            
            # Assign bouts to segments based on time ranges
            segment_bouts = [[] for _ in segments]
            
            for bout in parent_bouts:
                if isinstance(bout, dict):
                    bout_start = bout.get('start')
                    bout_end = bout.get('end')
                    bout_label = bout.get('label', 'smoking')
                else:
                    logger.warning(f"Invalid bout format in {parent_bouts}: {bout}, expected dict or list")
                    continue

                for i, (segment_start, segment_end) in enumerate(segment_ranges):
                    # If bout is entirely within segment
                    if segment_start <= bout_start <= segment_end and segment_start <= bout_end <= segment_end:
                        adjusted_bout = {'start': float(bout_start), 'end': float(bout_end), 'label': bout_label}
                        segment_bouts[i].append(adjusted_bout)
                        break
                    # If bout overlaps with segment start
                    elif bout_start < segment_start and segment_start <= bout_end <= segment_end:
                        adjusted_bout = {'start': float(segment_start), 'end': float(bout_end), 'label': bout_label}
                        segment_bouts[i].append(adjusted_bout)
                        break
                    # If bout overlaps with segment end
                    elif segment_start <= bout_start <= segment_end and bout_end > segment_end:
                        adjusted_bout = {'start': float(bout_start), 'end': float(segment_end), 'label': bout_label}
                        segment_bouts[i].append(adjusted_bout)
                        break
                    # If bout spans entire segment
                    elif bout_start < segment_start and bout_end > segment_end:
                        adjusted_bout = {'start': float(segment_start), 'end': float(segment_end), 'label': bout_label}
                        segment_bouts[i].append(adjusted_bout)
                        break


            # Save the complete resampled data to original directory (preserve original)
            original_dir = os.path.join(project_path, session_name)
            df[['ns_since_reboot', 'accel_x', 'accel_y', 'accel_z']].to_csv(os.path.join(original_dir, 'accelerometer_data.csv'), index=False)
            if gyro:
                df[['ns_since_reboot', 'gyro_x', 'gyro_y', 'gyro_z']].to_csv(os.path.join(original_dir, 'gyroscope_data.csv'), index=False)
            
            # Create virtual split sessions (no physical directories)
            new_sessions = []
            
            for i, segment in enumerate(segments):
                # Generate unique name
                new_name = self.generate_unique_session_name_upload(session_name, project_path, project_id)
                
                # Use the original split indices as offsets (they correspond to the un-resampled dataframe)
                segment_start_offset = split_indices[i]
                segment_end_offset = split_indices[i + 1]
                
                
                # Calculate start_ns and stop_ns for this segment
                segment_start_ns = int(segment['ns_since_reboot'].min())
                segment_stop_ns = int(segment['ns_since_reboot'].max())
                
                # Insert virtual split session into database
                result = self.session_repo.insert_single_session(
                    new_name, 
                    project_id, 
                    json.dumps(segment_bouts[i]), 
                    segment_start_ns, 
                    segment_stop_ns,
                    parent_data_path=original_dir,
                    data_start_offset=segment_start_offset,
                    data_end_offset=segment_end_offset
                )
                if result:  # Only add to new_sessions if insertion was successful
                    new_sessions.append(new_name)
            
            # Mark original session as split but keep the data
            conn = self.get_db_connection()
            if conn:
                try:
                    with conn.cursor(dictionary=True) as cursor:
                        cursor.execute("""
                            INSERT INTO sessions (project_id, session_name, status, keep, bouts, start_ns, stop_ns)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (project_id, session_name, 'Split', 0, '[]', int(df['ns_since_reboot'].min()), int(df['ns_since_reboot'].max())))
                        
                        parent_session_id = cursor.lastrowid
                        
                        # Update is_visible to hide the parent session
                        cursor.execute("""
                            UPDATE sessions SET is_visible = 0 WHERE session_id = %s
                        """, (parent_session_id,))
                        
                        # Add lineage for virtual splits
                        for new_session_name in new_sessions:
                            cursor.execute("""
                                SELECT session_id FROM sessions WHERE session_name = %s AND project_id = %s
                            """, (new_session_name, project_id))
                            child_result = cursor.fetchone()
                            if child_result:
                                cursor.execute("""
                                    INSERT INTO session_lineage (child_session_id, parent_session_id)
                                    VALUES (%s, %s)
                                """, (child_result['session_id'], parent_session_id))
                    
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Error creating parent session for virtual splits: {e}")
                finally:
                    conn.close()
            
            logger.info(f"Created {len(new_sessions)} virtual split sessions from upload for {session_name}")
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
                # Calculate start_ns and stop_ns for the original session
                fallback_start_ns = int(df['ns_since_reboot'].min())
                fallback_stop_ns = int(df['ns_since_reboot'].max())
                return self.session_repo.insert_single_session(session_name, project_id, json.dumps(parent_bouts, indent=2), fallback_start_ns, fallback_stop_ns)
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

    def generate_unique_session_name_upload(self, original_name, project_path, project_id):
        """Generate a unique session name by adding numeric suffixes (for upload process)"""
        base_counter = 1
        while True:
            candidate_name = f"{original_name}.{base_counter}"
            
            # Check filesystem for collision
            if os.path.exists(os.path.join(project_path, candidate_name)):
                base_counter += 1
                continue
                
            # Check database for collision using repository
            count = self.session_repo.count_sessions_by_name_and_project(candidate_name, project_id)
            
            if count == 0:
                return candidate_name
            
            base_counter += 1
    
    def generate_unique_session_name(self, original_name, project_path, project_id):
        """Generate a unique session name by adding numeric suffixes"""
        base_counter = 1
        while True:
            candidate_name = f"{original_name}.{base_counter}"
            
            # For virtual splits, only check database (no filesystem check needed)
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
                    s.start_ns, s.stop_ns, s.dataset_id, s.raw_session_name,
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
                    s.start_ns,
                    s.stop_ns,
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
    
    def update_session_bouts_labeling_name(self, project_id, old_name, new_name):
        """Update all session bouts that use a specific labeling name to use a new name
        
        Args:
            project_id: ID of the project containing the sessions
            old_name: Current labeling name to replace
            new_name: New labeling name to use
        """
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Get all sessions for this project that have bouts
            cursor.execute("""
                SELECT session_id, bouts 
                FROM sessions 
                WHERE project_id = %s AND bouts IS NOT NULL AND bouts != '[]'
            """, (project_id,))
            
            sessions_to_update = cursor.fetchall()
            updated_count = 0
            
            for session_row in sessions_to_update:
                session_id = session_row['session_id']
                bouts_json = session_row['bouts']
                
                if not bouts_json:
                    continue
                    
                try:
                    # Parse the bouts JSON
                    bouts = json.loads(bouts_json)
                    if not isinstance(bouts, list):
                        continue
                    
                    # Update any bouts that have the old labeling name
                    bouts_modified = False
                    for bout in bouts:
                        if isinstance(bout, dict) and bout.get('label') == old_name:
                            bout['label'] = new_name
                            bouts_modified = True
                    
                    # If we modified any bouts, update the session
                    if bouts_modified:
                        updated_bouts_json = json.dumps(bouts)
                        cursor.execute("""
                            UPDATE sessions 
                            SET bouts = %s 
                            WHERE session_id = %s
                        """, (updated_bouts_json, session_id))
                        updated_count += 1
                        
                except json.JSONDecodeError:
                    # Skip sessions with invalid JSON
                    logger.warning(f'Invalid bouts JSON for session {session_id}, skipping')
                    continue
            
            conn.commit()
            logger.info(f'Updated labeling name from "{old_name}" to "{new_name}" in {updated_count} sessions')
            return updated_count
            
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f'Failed to update session bouts labeling names: {str(e)}')
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
        """Split a session into multiple virtual sessions and mark original as split"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        try:
            with conn.cursor() as cursor:
                # Store the original session ID before deleting it
                parent_id = session_id
                created_sessions = []
                
                # Get the original session directory path for virtual splits
                session_name = session_info['session_name']
                project_path = session_info['project_path']
                
                # Check if we're splitting a virtual split session
                split_info = self.session_repo.get_session_split_info(session_id)
                if split_info and split_info['parent_data_path']:
                    # Use the existing parent data path for virtual splits
                    parent_data_path = split_info['parent_data_path']
                else:
                    # Regular session - use session directory
                    parent_data_path = os.path.join(project_path, session_name)
                
                for session_data in new_sessions:
                    # Extract start_ns and stop_ns from session_data and ensure they're integers
                    start_ns = int(session_data.get('start_ns'))
                    stop_ns = int(session_data.get('stop_ns'))
                    
                    # Get data offsets for virtual splitting
                    data_start_offset = session_data.get('data_start_offset')
                    data_end_offset = session_data.get('data_end_offset')
                    
                    # Insert virtual split session
                    cursor.execute("""
                        INSERT INTO sessions (project_id, session_name, status, keep, bouts, start_ns, stop_ns,
                                            parent_session_data_path, data_start_offset, data_end_offset)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        session_info['project_id'], 
                        session_data['name'], 
                        'Initial', 
                        session_info['keep'], 
                        json.dumps(session_data['bouts']),
                        start_ns,
                        stop_ns,
                        parent_data_path,
                        data_start_offset,
                        data_end_offset
                    ))
                    # Get the new session ID
                    child_id = cursor.lastrowid
                    created_sessions.append(child_id)

                    # Record lineage
                    cursor.execute("""
                        INSERT INTO session_lineage (child_session_id, parent_session_id)
                        VALUES (%s, %s)
                    """, (child_id, parent_id))
                    
                # Mark original session as split (but don't delete data)
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

    def duplicate_session_bouts_for_labeling(self, project_id, original_name, new_name):
        """Duplicate all session bouts from one labeling to create bouts for a new labeling
        
        Args:
            project_id: ID of the project containing the sessions
            original_name: Name of the original labeling to copy bouts from
            new_name: Name of the new labeling to create duplicate bouts for
        """
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Get all sessions for this project that have bouts
            cursor.execute("""
                SELECT session_id, bouts 
                FROM sessions 
                WHERE project_id = %s AND bouts IS NOT NULL AND bouts != '[]'
            """, (project_id,))
            
            sessions_to_update = cursor.fetchall()
            updated_count = 0
            total_bouts_duplicated = 0
            
            for session_row in sessions_to_update:
                session_id = session_row['session_id']
                bouts_json = session_row['bouts']
                
                if not bouts_json:
                    continue
                    
                try:
                    # Parse the bouts JSON
                    bouts = json.loads(bouts_json)
                    if not isinstance(bouts, list):
                        continue
                    
                    # Find bouts that match the original labeling name and duplicate them
                    new_bouts = []
                    for bout in bouts:
                        if isinstance(bout, dict) and bout.get('label') == original_name:
                            # Create a duplicate bout with the new labeling name
                            duplicate_bout = bout.copy()
                            duplicate_bout['label'] = new_name
                            new_bouts.append(duplicate_bout)
                            total_bouts_duplicated += 1
                    
                    # If we found bouts to duplicate, add them to the session
                    if new_bouts:
                        # Add the new bouts to the existing bouts list
                        bouts.extend(new_bouts)
                        updated_bouts_json = json.dumps(bouts)
                        
                        cursor.execute("""
                            UPDATE sessions 
                            SET bouts = %s 
                            WHERE session_id = %s
                        """, (updated_bouts_json, session_id))
                        updated_count += 1
                        
                except json.JSONDecodeError:
                    # Skip sessions with invalid JSON
                    logger.warning(f'Invalid bouts JSON for session {session_id}, skipping')
                    continue
            
            conn.commit()
            logger.info(f'Duplicated {total_bouts_duplicated} bouts from labeling "{original_name}" to "{new_name}" across {updated_count} sessions')
            
        except Exception as e:
            conn.rollback()
            logger.error(f'Error duplicating session bouts for labeling: {str(e)}')
            raise DatabaseError(f'Failed to duplicate session bouts: {str(e)}')
        finally:
            cursor.close()
            conn.close()

    def get_root_session_info(self, session_id):
        import os
        """
        Get root session information for labeling export/import.
        For virtual splits, returns the root parent session name and path.
        For regular sessions, returns the session itself.
        
        Args:
            session_id: ID of the session
            
        Returns:
            dict: Contains root_session_name, root_data_path, is_virtual_split
        """
        # Get session split info
        split_info = self.session_repo.get_session_split_info(session_id)
        
        if split_info and split_info['parent_data_path']:
            # Virtual split - extract root session name from parent path
            parent_path = split_info['parent_data_path']
            root_session_name = os.path.basename(parent_path)
            
            return {
                'root_session_name': root_session_name,
                'root_data_path': parent_path,
                'is_virtual_split': True,
                'data_start_offset': split_info['data_start_offset'],
                'data_end_offset': split_info['data_end_offset']
            }
        else:
            # Regular session - get session details
            session_info = self.get_session_details(session_id)
            if session_info:
                session_path = os.path.join(session_info['project_path'], session_info['session_name'])
                return {
                    'root_session_name': session_info['session_name'],
                    'root_data_path': session_path,
                    'is_virtual_split': False,
                    'data_start_offset': None,
                    'data_end_offset': None
                }
        
        return None

    def import_session(self, project_id, session_name, status='unlabeled', verified=False, 
                      bouts=None, dataset_id=None, raw_session_name=None, start_ns=None, stop_ns=None,
                      parent_session_data_path=None, data_start_offset=None, data_end_offset=None):
        """
        Import a session with all its data fields for project import functionality
        
        Args:
            project_id: ID of the project this session belongs to
            session_name: Name of the session
            status: Status of the session (default: 'unlabeled')
            verified: Whether the session is verified (default: False)
            bouts: List of bouts data
            dataset_id: Reference to raw dataset (for dataset-based sessions)
            raw_session_name: Original session name in raw dataset
            start_ns: Start timestamp in nanoseconds
            stop_ns: Stop timestamp in nanoseconds
            parent_session_data_path: Path to parent data for virtual splits
            data_start_offset: Start row index for pandas slicing
            data_end_offset: End row index for pandas slicing
            
        Returns:
            dict: Contains session_id and session_name if successful
        """
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor()
        try:
            # Convert bouts to JSON string
            bouts_json = json.dumps(bouts) if bouts else None
            
            # Insert session with all fields
            query = """
                INSERT INTO sessions (
                    project_id, session_name, status, verified, bouts, dataset_id, raw_session_name,
                    start_ns, stop_ns, parent_session_data_path, data_start_offset, data_end_offset
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(query, (
                project_id, session_name, status, verified, bouts_json, dataset_id, raw_session_name,
                start_ns, stop_ns, parent_session_data_path, data_start_offset, data_end_offset
            ))
            
            session_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"Successfully imported session '{session_name}' for project {project_id} (ID: {session_id})")
            return {
                'session_id': session_id,
                'session_name': session_name
            }
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error importing session {session_name}: {e}")
            raise DatabaseError(f'Failed to import session: {str(e)}')
        finally:
            cursor.close()
            conn.close()