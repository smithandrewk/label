from utils.logging import log
from flask import jsonify
import os
import pandas as pd

DATA_DIR = os.getenv('DATA_DIR', '~/.delta/data')

def load_data_from_csv_path(csv_path):
    try:
        df = pd.read_csv(csv_path)
        df = df.iloc[::2]
        expected_columns = ['ns_since_reboot', 'x', 'y', 'z']
        if not all(col in df.columns for col in expected_columns):
            return jsonify({'error': f'Invalid CSV format. Expected columns: {expected_columns}, Found: {list(df.columns)}'}), 400
        data = df[expected_columns].to_dict(orient='records')
        return data
    except Exception as e:
        log(f"Error loading data from {csv_path}: {e}")
        return []

def get_csv_path_from_session_info(session_info) -> str:
    project_dir_name = session_info['project_path']
    central_data_dir = os.path.expanduser(DATA_DIR)
    project_path = os.path.join(central_data_dir, project_dir_name)
    session_name = session_info['session_name']
    csv_path = os.path.join(project_path, session_name, 'accelerometer_data.csv')
    return csv_path

