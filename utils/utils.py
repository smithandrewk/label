import pandas as pd
import time
import functools
import os

def timeit(func):
    """Decorator to time function execution"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        
        # Get the first argument (csv_path) for logging
        csv_path = args[0] if args else "unknown"
        print(f"Function {func.__name__} took {elapsed_time:.3f}s for {csv_path}")
        
        return result
    return wrapper
    
@timeit
def validate_session_data(csv_path, min_rows=10):
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
            print(f"Data file does not exist: {csv_path}")
            return False
        
        # Check file size (empty files or very small files are invalid)
        file_size = os.path.getsize(csv_path)
        if file_size < 100:  # Less than 100 bytes is likely empty or just headers
            print(f"Data file is too small ({file_size} bytes): {csv_path}")
            return False
        
        # Try to read the CSV and validate content
        df = pd.read_csv(csv_path,nrows=1000) # tested to save ~1 second per file
        expected_columns = ['ns_since_reboot', 'x', 'y', 'z']
        
        # Check if required columns exist
        if not all(col in df.columns for col in expected_columns):
            print(f"Invalid CSV format in {csv_path}. Expected columns: {expected_columns}, Found: {list(df.columns)}")
            return False
        
        # Check if we have enough data rows
        if len(df) < min_rows:
            print(f"Insufficient data rows ({len(df)}) in {csv_path}. Minimum required: {min_rows}")
            return False
        
        # Check for valid timestamp data (not all NaN or zeros)
        if df['ns_since_reboot'].isna().all() or (df['ns_since_reboot'] == 0).all():
            print(f"Invalid timestamp data in {csv_path}")
            return False
        
        # Check for valid accelerometer data (not all NaN)
        accel_cols = ['x', 'y', 'z']
        if df[accel_cols].isna().all().all():
            print(f"No valid accelerometer data in {csv_path}")
            return False
        
        print(f"Data validation passed for {csv_path}: {len(df)} rows")
        return True
        
    except Exception as e:
        print(f"Error validating data in {csv_path}: {e}")
        return False