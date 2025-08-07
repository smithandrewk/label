from app.exceptions import DatabaseError
from app.repositories.users_repository import UserRepository
from werkzeug.security import check_password_hash, generate_password_hash
from app.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)

class UserService:
    def __init__(self, user_repository=None):
        self.user_repo = user_repository or UserRepository()


    def signup_user(self, username: str, password: str):
        """Create a new user with a hashed password"""
        existing_user = self.user_repo.find_by_username(username)
        if existing_user:
            logger.warning(f"Signup failed: Username '{username}' already exists")
            raise DatabaseError("Username already exists")

        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        user = self.user_repo.create_user(username, password_hash)
        logger.info(f"User '{username}' signed up successfully")
        return user

    def authenticate_user(self, username: str, password: str):
        """Check if the username exists and password matches"""
        user = self.user_repo.find_by_username(username)
        if user is None:
            logger.warning(f"Authentication failed: Username '{username}' not found")
            return None
        if check_password_hash(user['password_hash'], password):
            logger.info(f"User '{username}' authenticated successfully")
            return user
        logger.warning(f"Authentication failed: Incorrect password for '{username}'")
        return None
    
    def get_user_by_id(self, user_id):
        """Retrieve user by their user id"""
        return self.user_repo.find_by_id(user_id)

    def check_password(self, user_id, old_password, new_password):
        """Change a user's password"""
        user = self.get_user_by_id(user_id)
        if user is None:
            raise DatabaseError("User not found")

        if not check_password_hash(user['password_hash'], old_password):
            raise DatabaseError("Old password does not match")

        new_hash = generate_password_hash(new_password)
        self.user_repo.update_password(user_id, new_hash)
        logger.info("Password sucessfully changed")
        return True
        
    def delete_user(self, user_id: int):
        """Delete a user by their user_id."""
        self.user_repo.delete_user_by_id(user_id)
