#!/usr/bin/env python3
"""
Simple test script to spoof project upload requests for testing purposes.
This script mimics the FormData upload that the frontend JavaScript performs.
"""

import requests
import os
import math
from pathlib import Path
import uuid

# Configuration
BASE_URL = "http://localhost:5001"  # Adjust to your Flask app URL
UPLOAD_ENDPOINT = "/api/project/upload"

# Test project configuration
TEST_PROJECT_NAME = str(uuid.uuid4())
TEST_PARTICIPANT_CODE = "TEST001"
TEST_FOLDER_NAME = "test_data"

# Path to a directory containing test files to upload
# You can change this to any directory with files you want to test with
TEST_FILES_DIR = "./tests/data/test_data"  # Change this path as needed

def find_test_files(directory_path):
    """
    Find files in the test directory to upload.
    This mimics selecting files from a folder in the browser.
    """
    files_to_upload = []
    
    if not os.path.exists(directory_path):
        print(f"Test directory not found: {directory_path}")
        print("Creating test session directories with proper structure...")
        
        # Create a simple test directory structure
        os.makedirs(directory_path, exist_ok=True)
        
        # Create multiple test sessions (subdirectories)
        session_names = [
            "2024-01-01_10_00_00_morning_session",
            "2024-01-01_14_30_00_afternoon_session", 
            "2024-01-02_09_15_00_next_day_session"
        ]
        
        for session_name in session_names:
            session_dir = os.path.join(directory_path, session_name)
            os.makedirs(session_dir, exist_ok=True)
            
            # Create accelerometer_data.csv
            accel_file = os.path.join(session_dir, "accelerometer_data.csv")
            with open(accel_file, 'w') as f:
                f.write("ns_since_reboot,x,y,z\n")
                # Create more realistic data with some variation
                base_timestamp = 1000000000000 + hash(session_name) % 1000000000
                for i in range(1000):  # More data points
                    timestamp = base_timestamp + i * 10000000  # 10ms intervals
                    # Add some sine wave variation to make it look more realistic
                    import math
                    x_val = math.sin(i * 0.1) + (i % 10) * 0.05
                    y_val = math.cos(i * 0.1) + (i % 7) * 0.03
                    z_val = 9.8 + math.sin(i * 0.05) * 0.5  # Gravity + small variation
                    f.write(f"{timestamp},{x_val:.3f},{y_val:.3f},{z_val:.3f}\n")
            
            files_to_upload.append(accel_file)
            
            # Create gyroscope_data.csv
            gyro_file = os.path.join(session_dir, "gyroscope_data.csv")
            with open(gyro_file, 'w') as f:
                f.write("ns_since_reboot,x,y,z\n")
                base_timestamp = 1000000000000 + hash(session_name) % 1000000000
                for i in range(1000):  # Match accelerometer data points
                    timestamp = base_timestamp + i * 10000000  # 10ms intervals
                    # Gyroscope data (angular velocity, typically smaller values)
                    x_gyro = math.sin(i * 0.08) * 0.1
                    y_gyro = math.cos(i * 0.12) * 0.1
                    z_gyro = math.sin(i * 0.06) * 0.05
                    f.write(f"{timestamp},{x_gyro:.6f},{y_gyro:.6f},{z_gyro:.6f}\n")
            
            files_to_upload.append(gyro_file)
            
            # Create log.csv (optional but realistic)
            log_file = os.path.join(session_dir, "log.csv")
            with open(log_file, 'w') as f:
                f.write("timestamp,ns_since_reboot,level,message\n")
                base_timestamp = 1000000000000 + hash(session_name) % 1000000000
                # Add some walking status transitions
                f.write(f"2024-01-01 10:00:00,{base_timestamp},INFO,Session started\n")
                f.write(f"2024-01-01 10:02:30,{base_timestamp + 150000000000},INFO,Updating walking status from false to true\n")
                f.write(f"2024-01-01 10:05:15,{base_timestamp + 315000000000},INFO,Updating walking status from true to false\n")
                f.write(f"2024-01-01 10:08:00,{base_timestamp + 480000000000},INFO,Updating walking status from false to true\n")
                f.write(f"2024-01-01 10:10:30,{base_timestamp + 630000000000},INFO,Updating walking status from true to false\n")
                f.write(f"2024-01-01 10:15:00,{base_timestamp + 900000000000},INFO,Session ended\n")
            
            files_to_upload.append(log_file)
            
            print(f"Created test session: {session_dir}")
            print(f"  - accelerometer_data.csv ({1000} data points)")
            print(f"  - gyroscope_data.csv ({1000} data points)")
            print(f"  - log.csv (with walking transitions)")
        
        print(f"\nTest directory structure created at: {directory_path}")
        # Show the directory tree
        for root, dirs, files in os.walk(directory_path):
            level = root.replace(directory_path, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                print(f"{subindent}{file}")
        print()
    else:
        # Recursively find all files in the directory
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                files_to_upload.append(file_path)
    
    return files_to_upload

def create_multipart_files(files_to_upload, base_dir):
    """
    Create the files list for multipart upload.
    This mimics how the browser creates relative paths for uploaded files.
    """
    files_list = []
    base_path = Path(base_dir)
    
    # Get the folder name from TEST_FOLDER_NAME to prepend to all paths
    folder_prefix = TEST_FOLDER_NAME
    
    for file_path in files_to_upload:
        file_path_obj = Path(file_path)
        
        # Create relative path from base directory
        try:
            relative_path = file_path_obj.relative_to(base_path)
        except ValueError:
            # If file is not under base_dir, just use filename
            relative_path = file_path_obj.name
        
        # Prepend the folder name to match browser behavior
        full_relative_path = f"{folder_prefix}/{relative_path}"
        
        # Open file and add to files list
        # The key 'files' matches what the JavaScript sends
        files_list.append(
            ('files', (str(full_relative_path), open(file_path, 'rb'), 'application/octet-stream'))
        )
    
    return files_list

def test_project_upload():
    """
    Test the project upload functionality by sending a POST request
    with multipart form data, mimicking the JavaScript FormData upload.
    """
    print(f"Testing project upload to: {BASE_URL}{UPLOAD_ENDPOINT}")
    print(f"Project: {TEST_PROJECT_NAME}")
    print(f"Participant: {TEST_PARTICIPANT_CODE}")
    print(f"Folder: {TEST_FOLDER_NAME}")
    print(f"Files directory: {TEST_FILES_DIR}")
    print("-" * 50)
    
    # Find files to upload
    files_to_upload = find_test_files(TEST_FILES_DIR)
    print(files_to_upload)
    if not files_to_upload:
        print("No files found to upload!")
        return
    
    print(f"Found {len(files_to_upload)} files to upload:")
    for file_path in files_to_upload:
        print(f"  - {file_path}")
    print()
    
    try:
        # Prepare form data (matches the JavaScript FormData)
        form_data = {
            'name': TEST_PROJECT_NAME,
            'participant': TEST_PARTICIPANT_CODE,
            'folderName': TEST_FOLDER_NAME,
        }
        
        # Prepare files for multipart upload
        files = create_multipart_files(files_to_upload, TEST_FILES_DIR)
        
        print("Files being uploaded:")
        for i, (field_name, (filename, file_obj, content_type)) in enumerate(files):
            print(f"  {i+1}. {field_name}: {filename}")
        print()
        
        print("Sending upload request...")
        
        # Make the POST request (matches the JavaScript fetch call)
        response = requests.post(
            f"{BASE_URL}{UPLOAD_ENDPOINT}",
            data=form_data,
            files=files,
            timeout=30  # 30 second timeout
        )
        
        # Close all file handles
        for _, file_tuple in files:
            if len(file_tuple) >= 2 and hasattr(file_tuple[1], 'close'):
                file_tuple[1].close()
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print("✅ Upload successful!")
                print(f"Response data: {result}")
                
                if 'upload_id' in result:
                    print(f"Upload ID: {result['upload_id']}")
                if 'project_id' in result:
                    print(f"Project ID: {result['project_id']}")
                if 'sessions_found' in result:
                    print(f"Sessions found: {result['sessions_found']}")
                    
            except ValueError as e:
                print("✅ Upload successful (non-JSON response)")
                print(f"Response text: {response.text}")
        else:
            print(f"❌ Upload failed with status {response.status_code}")
            print(f"Response text: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - make sure your Flask app is running!")
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_with_custom_files():
    """
    Alternative test method where you can specify exact files to upload.
    """
    print("=== Custom Files Test ===")
    
    # You can manually specify files here for testing
    custom_files = [
        # Add specific file paths here, e.g.:
        # "/path/to/your/session/accelerometer_data.csv",
        # "/path/to/your/session/gyroscope_data.csv",
        # "/path/to/your/session/log.csv",
    ]
    
    if not custom_files:
        print("No custom files specified. Edit the script to add file paths.")
        return
    
    # Check if files exist
    existing_files = [f for f in custom_files if os.path.exists(f)]
    
    if not existing_files:
        print("None of the specified custom files exist!")
        return
    
    print(f"Testing with {len(existing_files)} custom files:")
    for f in existing_files:
        print(f"  - {f}")
    
    # Similar upload logic but with custom files
    try:
        form_data = {
            'name': "Custom Test Project",
            'participant': "CUSTOM001", 
            'folderName': "custom_test_folder",
        }
        
        files = []
        for file_path in existing_files:
            filename = os.path.basename(file_path)
            files.append(('files', (filename, open(file_path, 'rb'), 'application/octet-stream')))
        
        response = requests.post(
            f"{BASE_URL}{UPLOAD_ENDPOINT}",
            data=form_data,
            files=files,
            timeout=30
        )
        
        # Close file handles
        for _, file_tuple in files:
            file_tuple[1].close()
        
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            try:
                result = response.json()
                print("✅ Custom upload successful!")
                print(f"Response: {result}")
            except ValueError:
                print("✅ Custom upload successful (non-JSON response)")
                print(f"Response: {response.text}")
        else:
            print(f"❌ Custom upload failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error in custom upload: {e}")

if __name__ == "__main__":
    print("🧪 Project Upload Test Script")
    print("=" * 40)
    
    # Run the main test
    test_project_upload()
    
    print("\n" + "=" * 40)
    
    # Optionally run custom files test
    # Uncomment the line below and add files to test_with_custom_files()
    # test_with_custom_files()
    
    print("Test completed!")
