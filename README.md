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
