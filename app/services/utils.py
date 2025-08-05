import pandas as pd
import time
import functools
import os
import sys
import json
from app.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)

def timeit(func):
    """Decorator to time function execution"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        
        # Get the first argument (csv_path) for logging
        csv_path = args[0] if args else "unknown"
        logger.debug(f"Function {func.__name__} took {elapsed_time:.3f}s for {csv_path}")
        
        return result
    return wrapper

def performance_monitor(track_memory=False):
    """Enhanced performance monitoring decorator with memory tracking and data size measurement"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = None
            
            if track_memory:
                import psutil
                process = psutil.Process(os.getpid())
                start_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            result = func(*args, **kwargs)
            
            elapsed_time = time.time() - start_time
            end_memory = None
            memory_delta = None
            
            if track_memory:
                end_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_delta = end_memory - start_memory
            
            # Estimate response size for API endpoints
            response_size = 0
            if hasattr(result, 'get_data'):
                # Flask response object
                response_size = len(result.get_data()) / 1024  # KB
            elif isinstance(result, (dict, list)):
                # JSON serializable data
                response_size = len(json.dumps(result).encode('utf-8')) / 1024  # KB
            
            # Log performance metrics
            perf_info = {
                'function': func.__name__,
                'elapsed_time': f"{elapsed_time:.3f}s",
                'response_size_kb': f"{response_size:.2f}KB" if response_size else "N/A"
            }
            
            if track_memory and memory_delta is not None:
                perf_info['memory_delta_mb'] = f"{memory_delta:.2f}MB"
            
            logger.info(f"PERFORMANCE: {json.dumps(perf_info)}")
            
            return result
        return wrapper
    return decorator

def api_performance_monitor(func):
    """Specialized performance monitor for API endpoints"""
    return performance_monitor(track_memory=True)(func)
    
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

def load_dataframe_from_csv(csv_path, column_prefix='accel', target_hz=50):
    df = pd.read_csv(csv_path).iloc[:-1]
    df = df.rename(columns={'x': f'{column_prefix}_x', 'y': f'{column_prefix}_y', 'z': f'{column_prefix}_z'})
    df['ns_since_reboot'] = df['ns_since_reboot'].astype(float)
    df[f'{column_prefix}_x'] = df[f'{column_prefix}_x'].astype(float)
    df[f'{column_prefix}_y'] = df[f'{column_prefix}_y'].astype(float)
    df[f'{column_prefix}_z'] = df[f'{column_prefix}_z'].astype(float)
    df = df.sort_values('ns_since_reboot').reset_index(drop=True)
    return df

def get_sample_rate_from_dataframe(df):
    sample_interval = df['ns_since_reboot'].diff().median() * 1e-9
    sample_rate = 1 / sample_interval
    return sample_rate

def check_sample_rate_consistency(sample_rate1, sample_rate2):
    if abs(sample_rate1 - sample_rate2) > 0.01:
        raise ValueError(f"Sample rates differ significantly: {sample_rate1:.2f} Hz vs {sample_rate2:.2f} Hz")
    
    return True