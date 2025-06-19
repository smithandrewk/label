from time import sleep
import uuid
import threading
import time
import uuid
import json
import torch
import numpy as np
import pandas as pd
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.nn.functional import relu
from torch.utils.data import DataLoader, TensorDataset

class ModelService:
    def __init__(self, get_db_connection=None):
        self.get_db_connection = get_db_connection
        self.model = SmokingCNN(window_size=3000, num_features=3)
        self.model.load_state_dict(torch.load('model.pth', map_location='cpu'))
        self.model.eval()
        self.scoring_status = {}  # Track scoring operations
        self.models = []

    def list_models(self):
        """List all available models"""
        # TODO: Implement logic to list models from the database or filesystem
        return self.models
    
    def score_session_async(self, project_path, session_name, session_id):
        """Start async scoring of a session"""
        # Generate unique scoring ID
        scoring_id = str(uuid.uuid4())

        # Initialize status tracking
        self.scoring_status[scoring_id] = {
            'status': 'running',
            'session_id': session_id,
            'session_name': session_name,
            'start_time': time.time(),
            'error': None
        }
        # Start async processing in a separate thread
        scoring_thread = threading.Thread(
            target=self._score_session_worker,  
            args=(scoring_id, project_path, session_name, session_id)
        )
        scoring_thread.daemon = True
        scoring_thread.start()
        
        return scoring_id

    def _score_session_worker(self, scoring_id, project_path, session_name, session_id):
        try:
            print(f"Starting scoring for session {scoring_id}")

            df = pd.read_csv(f"{project_path}/{session_name}/accelerometer_data.csv")
            sample_interval = df['ns_since_reboot'].diff().median() * 1e-9
            sample_rate = 1 / sample_interval
            print(f"Sample rate: {sample_rate} Hz")

            fs = 50
            window_size_seconds = 60
            window_stride_seconds = 60

            X = []
            data = torch.tensor(df[['x', 'y', 'z']].values, dtype=torch.float32)
            window_size = fs * window_size_seconds
            window_stride = fs * window_stride_seconds
            windowed_data = data.unfold(dimension=0,size=window_size,step=window_stride)
            X.append(windowed_data)

            X = torch.cat(X)

            with torch.no_grad():
                y_pred = self.model(X).sigmoid().cpu()
                y_pred = y_pred > .6
                y_pred = y_pred.numpy().flatten()
                y_pred = y_pred.repeat(3000)

            if len(y_pred) < len(df):
                y_pred = torch.cat([torch.tensor(y_pred), torch.zeros(len(df) - len(y_pred))])
            df['y_pred'] = y_pred*20

            smoking_bouts = []
            current_bout = None
            for i in range(len(df)):
                if df['y_pred'].iloc[i] > 0:
                    if current_bout is None:
                        current_bout = [int(df['ns_since_reboot'].iloc[i]), None]
                    else:
                        current_bout[1] = int(df['ns_since_reboot'].iloc[i])
                else:
                    if current_bout is not None:
                        smoking_bouts.append(current_bout)
                        current_bout = None

            # Remove bouts shorter than 20 seconds
            smoking_bouts = [bout for bout in smoking_bouts if (bout[1] - bout[0]) >= 30 * 1e9]
            print(smoking_bouts)

            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions
                SET bouts = %s
                WHERE session_id = %s
            """, (json.dumps(smoking_bouts), session_id))
            
            conn.commit()
            cursor.close()
            conn.close()

            # Update status on completion
            self.scoring_status[scoring_id].update({
                'status': 'completed',
                'end_time': time.time(),
                'bouts_count': len(smoking_bouts)
            })
        except Exception as e:
            print(f"Error during scoring: {e}")
            # Handle error (e.g., log it, update status, etc.)
            print(f"Error scoring session {scoring_id}: {e}")
            self.scoring_status[scoring_id].update({
                'status': 'error',
                'error': str(e),
                'end_time': time.time()
            })

        return smoking_bouts
    def get_scoring_status(self, scoring_id):
        """Get the status of a scoring operation"""
        return self.scoring_status.get(scoring_id, {'status': 'not_found'})
    
class SmokingCNN(nn.Module):
    def __init__(self, window_size=100, num_features=6):
        super(SmokingCNN, self).__init__()
        kernel_size = 3

        self.c1 = nn.Conv1d(in_channels=num_features, out_channels=4, kernel_size=kernel_size)
        self.c2 = nn.Conv1d(in_channels=4, out_channels=8, kernel_size=kernel_size)
        self.c3 = nn.Conv1d(in_channels=8, out_channels=16, kernel_size=kernel_size)

        self.classifier = nn.Linear(16, 1)
    
    
    def forward(self, x):
        x = self.c1(x)
        x = relu(x)
        x = self.c2(x)
        x = relu(x)
        x = self.c3(x)
        x = relu(x)
        x = x.mean(dim=2)

        x = self.classifier(x)
        return x
    
