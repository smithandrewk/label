import pandas as pd
import time
import functools
import os
import logging
import traceback

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
    
def resample(df,target_hz=50):
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['ns_since_reboot'], unit='ns')
    df = df.set_index('timestamp')
    freq = f'{1000//target_hz}ms'  # 20ms for 50Hz
    df_resampled = df.resample(freq).mean().ffill()
    df_resampled = df_resampled.reset_index()
    df_resampled['ns_since_reboot'] = df_resampled['timestamp'].astype('int64')
    df = df_resampled.drop('timestamp', axis=1)
    return df

def load_accelerometer_data_csv(csv_path):
    try:
        df = pd.read_csv(csv_path).iloc[:-1] 
        df['ns_since_reboot'] = df['ns_since_reboot'].astype(float)
        df['x'] = df['x'].astype(float)
        df['y'] = df['y'].astype(float)
        df['z'] = df['z'].astype(float)
        df = df.sort_values('ns_since_reboot').reset_index(drop=True)
        return df
    except Exception as e:
        logging.error(f"Error in {load_accelerometer_data_csv.__name__}: {e}")
        logging.error(traceback.format_exc())
        return None
    
def find_time_gaps(df):
    gap_threshold_minutes = 5
    gap_threshold_ns = gap_threshold_minutes * 60 * 1_000_000_000
    df = df.sort_values('ns_since_reboot').reset_index(drop=True)
    time_diffs = df['ns_since_reboot'].diff()
    gap_indices = time_diffs[time_diffs > gap_threshold_ns].index
    print(f"Found {len(gap_indices)} time gaps.")
    return gap_indices.tolist()