#!/usr/bin/env python3
"""
Comprehensive test script for the verified status feature.
This script tests both backend API endpoints and verifies database consistency.
"""

import requests
import mysql.connector
import json
import sys

# Configuration
BASE_URL = "http://127.0.0.1:5050"
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Password123!',
    'database': 'smoking_data'
}

def test_database_schema():
    """Test that the verified column exists in the database"""
    print("Testing database schema...")
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute("DESCRIBE sessions")
        columns = [row[0] for row in cursor.fetchall()]
        
        if 'verified' in columns:
            print("✅ Database schema: 'verified' column exists")
            return True
        else:
            print("❌ Database schema: 'verified' column missing")
            return False
    except Exception as e:
        print(f"❌ Database schema test failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def test_sessions_api():
    """Test that the sessions API returns verified field"""
    print("Testing sessions API...")
    try:
        response = requests.get(f"{BASE_URL}/api/sessions")
        if response.status_code == 200:
            sessions = response.json()
            if sessions and 'verified' in sessions[0]:
                print("✅ Sessions API: Returns verified field")
                return True, sessions[0]['session_id']
            else:
                print("❌ Sessions API: Missing verified field")
                return False, None
        else:
            print(f"❌ Sessions API: HTTP {response.status_code}")
            return False, None
    except Exception as e:
        print(f"❌ Sessions API test failed: {e}")
        return False, None

def test_session_data_api(session_id):
    """Test that individual session API returns verified field"""
    print(f"Testing session data API for session {session_id}...")
    try:
        response = requests.get(f"{BASE_URL}/api/session/{session_id}")
        if response.status_code == 200:
            data = response.json()
            if 'session_info' in data and 'verified' in data['session_info']:
                print("✅ Session Data API: Returns verified field")
                return True
            else:
                print("❌ Session Data API: Missing verified field")
                return False
        else:
            print(f"❌ Session Data API: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Session Data API test failed: {e}")
        return False

def test_metadata_update(session_id):
    """Test updating verified status via metadata endpoint"""
    print(f"Testing metadata update for session {session_id}...")
    try:
        # First, get current status
        response = requests.get(f"{BASE_URL}/api/session/{session_id}")
        current_data = response.json()
        current_verified = current_data['session_info']['verified']
        
        # Toggle verified status
        new_verified = 1 if current_verified == 0 else 0
        
        # Update metadata
        update_data = {
            'status': current_data['session_info']['status'],
            'keep': current_data['session_info']['keep'],
            'verified': new_verified,
            'bouts': current_data['session_info']['bouts']
        }
        
        response = requests.put(
            f"{BASE_URL}/api/session/{session_id}/metadata",
            json=update_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('rows_affected', 0) > 0:
                print("✅ Metadata Update: Successfully updated verified status")
                return True, new_verified
            else:
                print("❌ Metadata Update: No rows affected")
                return False, None
        else:
            print(f"❌ Metadata Update: HTTP {response.status_code}")
            return False, None
    except Exception as e:
        print(f"❌ Metadata Update test failed: {e}")
        return False, None

def test_database_persistence(session_id, expected_verified):
    """Test that verified status is properly persisted in database"""
    print(f"Testing database persistence for session {session_id}...")
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT verified FROM sessions WHERE session_id = %s", (session_id,))
        result = cursor.fetchone()
        
        if result and result[0] == expected_verified:
            print("✅ Database Persistence: Verified status correctly stored")
            return True
        else:
            print(f"❌ Database Persistence: Expected {expected_verified}, got {result[0] if result else 'None'}")
            return False
    except Exception as e:
        print(f"❌ Database Persistence test failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    print("🚀 Starting comprehensive verified status feature tests...\n")
    
    tests_passed = 0
    total_tests = 5
    
    # Test 1: Database schema
    if test_database_schema():
        tests_passed += 1
    print()
    
    # Test 2: Sessions API
    sessions_api_success, test_session_id = test_sessions_api()
    if sessions_api_success:
        tests_passed += 1
    print()
    
    if not test_session_id:
        print("❌ Cannot continue tests without a valid session ID")
        sys.exit(1)
    
    # Test 3: Session Data API
    if test_session_data_api(test_session_id):
        tests_passed += 1
    print()
    
    # Test 4: Metadata Update
    metadata_success, new_verified = test_metadata_update(test_session_id)
    if metadata_success:
        tests_passed += 1
    print()
    
    # Test 5: Database Persistence
    if new_verified is not None and test_database_persistence(test_session_id, new_verified):
        tests_passed += 1
    print()
    
    # Summary
    print("=" * 50)
    print(f"TEST SUMMARY: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! The verified status feature is working correctly.")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
