from .base_repository import BaseRepository
from app.exceptions import DatabaseError
from werkzeug.security import generate_password_hash, check_password_hash


class UserRepository(BaseRepository):
    """Repository for user-related database operations"""

    def find_by_username(self, username):
        """Retrieve a user by their username"""
        query = """
            SELECT user_id, username, password_hash, created_at
            FROM users
            WHERE username = %s
        """
        return self._execute_query(query, (username,), fetch_one=True)

    def create_user(self, username, password_hash):
        """Create a new user with a hashed password"""

        query = """
            INSERT INTO users (username, password_hash)
            VALUES (%s, %s)
        """

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(query, (username, password_hash))
            conn.commit()

            user_id = cursor.lastrowid

            return self.find_by_id(user_id)

        except Exception as e:
            conn.rollback()
            raise DatabaseError(f"Error creating user: {str(e)}")

        finally:
            cursor.close()
            conn.close()

    def find_by_id(self, user_id):
        """Retrieve user by their user_id"""
        query = """
            SELECT user_id, username, password_hash, created_at
            FROM users
            WHERE user_id = %s
        """
        return self._execute_query(query, (user_id,), fetch_one=True)

    def check_password(self, user_record, password):
        """Check if provided password matches the hash"""
        return check_password_hash(user_record['password_hash'], password)

    def delete_user_by_id(self, user_id: int):
        query = "DELETE FROM users WHERE user_id = %s"
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(query, (user_id,))
            conn.commit()

        except Exception as e:
            conn.rollback()
            raise DatabaseError(f"Error deleting user: {str(e)}")

        finally:
            cursor.close()
            conn.close()
