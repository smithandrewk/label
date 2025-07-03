import pytest
import sys
import os
from dotenv import load_dotenv

# Load environment variables before any imports
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.repositories.session_repository import SessionRepository
from app.services.database_service import get_db_connection


@pytest.fixture
def session_repo():
    """Fixture to provide a SessionRepository instance"""
    return SessionRepository(get_db_connection=get_db_connection)


@pytest.fixture
def db_connection():
    """Fixture to provide a database connection"""
    conn = get_db_connection()
    yield conn
    if conn:
        conn.close()


class TestSessionRepository:
    
    def test_database_connection(self, db_connection):
        """Test that we can connect to the database"""
        assert db_connection is not None, "Database connection should not be None"
        assert db_connection.is_connected(), "Database should be connected"
    
    def test_get_bouts_by_session_exists(self, session_repo):
        """Test getting bouts for an existing session"""
        session_id = 144  # Replace with a known session ID
        
        bouts = session_repo.get_bouts_by_session(session_id)
        
        print(f"Session ID: {session_id}")
        print(f"Bouts: {bouts}")
        print(f"Type: {type(bouts)}")
        print(f"Length: {len(bouts) if bouts else 'None'}")
        
        # Basic assertions - adjust based on your expected data structure
        assert bouts is not None, "Bouts should not be None"
    
    def test_get_bouts_by_session_nonexistent(self, session_repo):
        """Test getting bouts for a non-existent session"""
        session_id = 999999  # Should not exist
        
        bouts = session_repo.get_bouts_by_session(session_id)
        
        # Should return None or empty result for non-existent session
        assert bouts is None or bouts == [] or bouts == {}, f"Expected None/empty for non-existent session, got {bouts}"
    
    @pytest.mark.parametrize("session_id", [144, 145, 146])  # Add your test session IDs
    def test_get_bouts_multiple_sessions(self, session_repo, session_id):
        """Test getting bouts for multiple sessions"""
        bouts = session_repo.get_bouts_by_session(session_id)
        
        # Adjust assertions based on your data structure expectations
        if bouts is not None:
            print(f"Session {session_id}: {len(bouts) if hasattr(bouts, '__len__') else 'N/A'} bouts")
