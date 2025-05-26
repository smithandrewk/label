#!/usr/bin/env python3

import sys
import os
sys.path.append('/Users/andrew/label-smoking-data')

# Import the validation function from app.py
from app import validate_session_data

# Test the validation function with our test data
test_files = [
    '/tmp/test_smoking_data/2024-01-01_10_00_00_session1/accelerometer_data.csv',  # Valid data
    '/tmp/test_smoking_data/empty_session1/accelerometer_data.csv',               # Empty file
    '/tmp/test_smoking_data/empty_session2/accelerometer_data.csv',               # Headers only
    '/tmp/test_smoking_data/invalid_session3/accelerometer_data.csv',             # Wrong columns
    '/tmp/test_smoking_data/tiny_session4/accelerometer_data.csv',                # NaN data
]

print("Testing validation function:")
print("=" * 50)

for file_path in test_files:
    print(f"\nTesting: {file_path}")
    is_valid = validate_session_data(file_path)
    print(f"Result: {'VALID' if is_valid else 'INVALID'}")
    print("-" * 30)
