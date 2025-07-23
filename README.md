# Smoking Detection Data Labeling Application

A Flask-based web application for labeling smoking detection data from accelerometer sensors.

## Prerequisites

1. **MySQL Server** - Install MySQL server on your system
2. **Python 3.8+** - Ensure Python 3.8 or later is installed
3. **pip** - Python package installer

## Quick Setup

1. **Clone and navigate to the project**
   ```bash
   cd label-smoking-data
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your MySQL credentials
   ```

3. **Run complete setup**
   ```bash
   make setup
   ```

4. **Start the application**
   ```bash
   make run-app
   ```

## Manual Setup

If you prefer to set up manually:

1. **Install Python dependencies**
   ```bash
   make install-deps
   ```

2. **Create database user** (requires MySQL root access)
   ```bash
   make setup-user
   ```

3. **Create database and tables**
   ```bash
   make create-db
   ```

4. **Optional: Add sample data**
   ```bash
   make seed-db
   ```

## Available Make Targets

- `make setup` - Complete setup process
- `make create-db` - Create database and tables
- `make reset-db` - Drop and recreate database
- `make seed-db` - Add sample data
- `make backup-db` - Create database backup
- `make run-app` - Start the Flask application
- `make test-db` - Test database connection

## Usage

1. Open your browser to `http://localhost:5000`
2. Upload project data containing accelerometer CSV files
3. Label smoking sessions using the web interface
4. Export labeled data in JSON or CSV format

## Uploading Scoring Models


1. Add the `.py` and `.pt` file to the `MODEL_DIR` specified in the `.env` file
2. Add model `.py` file path, `.pt` file path, display name, and model class name to the UI 
3. All models should implement the following three methods in the `.py` files that defines the **Class** as well:
   - `preprocess(self, data)`
   - `run(self, preprocessed_data, device='cpu')`
   - `postprocess(self, raw_predictions, data)`



### `preprocess(self, data)`


Converts raw session data to model input format.


Parameters: 
   - data: Raw pandas DataFrame with accelerometer data


Returns: 
   - Model-ready data object (a PyTorch tensor)

Example:
``` python
def preprocess(self, data):
    """Convert DataFrame to windowed tensor data"""
    # Extract accelerometer columns
    accel_data = data[['accel_x', 'accel_y', 'accel_z']].values
    
    # Create sliding windows
    fs = 50  # Sample rate
    window_size = fs * 60  # 60 second windows
    window_stride = fs * 60  # Non-overlapping
    
    # Convert to tensor and create windows
    tensor_data = torch.tensor(accel_data, dtype=torch.float32)
    windowed_data = tensor_data.unfold(dimension=0, size=window_size, step=window_stride)
    
    return windowed_data
```

### `run(self, preprocessed_data, device='cpu')`

Executes model inference on preprocessed data.


Parameters: 
   - preprocessed_data: Output from preprocess() method
   - device: Target device string ('cpu' or 'cuda')

Returns:
   - Raw model predictions (typically logits or probabilities)

Example:
```python 
def run(self, preprocessed_data, device='cpu'):
    """Run model inference"""
    # Ensure model and data are on correct device
    self.to(device)
    preprocessed_data = preprocessed_data.to(device)
    
    # Run inference
    with torch.no_grad():
        predictions = self.forward(preprocessed_data)
    
    return predictions
```

### `postprocess(self, raw_predictions, raw_data)`
Converts raw model output to time-domain predictions.


Parameters:
   - raw_predictions: Raw output from run() method
   - raw_data: Raw data athat was also passed to preprocess() method

Returns:
   - Time-aligned predictions ready for bout extraction

Example:
``` python 

def postprocess(self, raw_predictions, raw_data):
    """Convert predictions to time domain"""
    # Apply sigmoid and threshold
    predictions = raw_predictions.sigmoid().cpu()
    predictions = (predictions > 0.6).float()
    predictions = predictions.numpy().flatten()
    
    # Expand to match original time resolution
    # (each prediction covers 60 seconds at 50Hz = 3000 samples)
    expanded_predictions = predictions.repeat(3000)
    
    return expanded_predictions

```