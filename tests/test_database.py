import pytest
import sys
import os
from dotenv import load_dotenv

# Load environment variables before any imports
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.database_service import get_db_connection


def test_environment_variables():
    """Test that environment variables are loaded correctly"""
    assert os.getenv('MYSQL_HOST') is not None, "MYSQL_HOST should be set"
    assert os.getenv('MYSQL_USER') is not None, "MYSQL_USER should be set"
    assert os.getenv('MYSQL_PASSWORD') is not None, "MYSQL_PASSWORD should be set"
    assert os.getenv('MYSQL_DATABASE') is not None, "MYSQL_DATABASE should be set"


def test_database_connection():
    """Test basic database connection"""
    conn = get_db_connection()
    
    assert conn is not None, "Database connection should not be None"
    assert conn.is_connected(), "Database should be connected"
    
    # Test a simple query
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    assert result == (1,), "Simple query should return (1,)"
    
    cursor.close()
    conn.close()


def test_database_connection_failure():
    """Test database connection with invalid credentials"""
    # Temporarily override environment variables
    original_password = os.environ.get('MYSQL_PASSWORD')
    os.environ['MYSQL_PASSWORD'] = 'invalid_password'
    
    try:
        conn = get_db_connection()
        assert conn is None, "Connection should fail with invalid credentials"
    finally:
        # Restore original password
        if original_password:
            os.environ['MYSQL_PASSWORD'] = original_password
