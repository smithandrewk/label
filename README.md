# Smoking Detection Data Labeling Application

A Flask-based web application for labeling smoking detection data from accelerometer sensors.

## Prerequisites

1. **Python 3.8+** - Ensure Python 3.8 or later is installed
2. **pip** - Python package installer

## Setup Process

1. **Clone and navigate to the project**
   ```bash
   cd label-smoking-data
   ```

2. **Install SSHFS first**
   This lets you mount the remote data directory over SSH:
   ```bash
   sudo apt install sshfs
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with:
   # - Your MySQL credentials
   # - Your beast username (BEAST_USERNAME)
   # - Keep DATA_DIR path as is for shared setup
   ```

4. **Run the setup script**
   This will install dependencies and mount the data directory automatically:
   ```bash
   make setup
   ```

5. **Additional data directory commands**
   ```bash
   # To manually mount or unmount the data directory:
   make mount-data
   make unmount-data
   ```

## Usage

1. **Start the application**
   ```bash
   make run-app
   ```
   This will automatically mount the data directory (if not already mounted) and start the Flask server.

2. Open your browser to `http://localhost:5000`

3. Upload project data containing accelerometer CSV files

4. Label smoking sessions using the web interface

5. Export labeled data in JSON or CSV format

6. **When finished**
   ```bash
   make unmount-data
   ```
   This will cleanly disconnect from the remote data directory.
