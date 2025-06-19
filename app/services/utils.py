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