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