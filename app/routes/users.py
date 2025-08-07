from flask import Blueprint, request, jsonify, session
from app.services.users_service import UserService 
from app.exceptions import DatabaseError
from app.logging_config import get_logger
import traceback

logger = get_logger(__name__)

users_bp = Blueprint('users', __name__)


class UsersController:
    def __init__(self, user_service):
        self.user_service: UserService = user_service

    def signup(self):
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return jsonify({'error': 'Username and password are required'}), 400

            user = self.user_service.signup_user(username, password)

            session['current_user_id'] = user['user_id']

            return jsonify({
                'message': 'User created successfully',
                'user_id': user['user_id'],
                'username': user['username']
            }), 201

        except DatabaseError as e:
            logger.warning(f"Signup failed: {e}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Unexpected error in signup: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': 'Internal server error'}), 500

    def login(self):
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return jsonify({'error': 'Username and password are required'}), 400

            user = self.user_service.authenticate_user(username, password)

            if not user:
                return jsonify({'error': 'Invalid username or password'}), 401

            session['current_user_id'] = user['user_id']

            return jsonify({
                'message': 'Login successful',
                'user_id': user['user_id'],
                'username': user['username']
            })

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': 'Internal server error'}), 500
    
    def logout(self):
        session.pop('current_user_id', None)
        return jsonify({'message': 'Logged out successfully'})
    
    def delete_user(self, user_id):
        try:
            current_user_id = session.get('current_user_id')
            if not current_user_id:
                return jsonify({'error': 'Not logged in'}), 401
            
            if int(user_id) != int(current_user_id):
                return jsonify({'error': 'Unauthorized'}), 403

            self.user_service.delete_user(user_id)
            session.pop('current_user_id', None)
            return jsonify({'message': 'User deleted successfully'})
    
        except DatabaseError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': 'Internal server error'}), 500

    def get_current_user(self):
        user_id = session.get('current_user_id')
        if not user_id:
            return jsonify({'error': 'Not logged in'}), 401
        
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user_id': user['user_id'],
            'username': user['username'],
            'created_at': user['created_at']
        })

    def change_password(self, user_id):
        try:
            data = request.get_json()
            old_password = data.get('old_password')
            new_password = data.get('new_password')

            if not old_password or not new_password:
                return jsonify({'error': 'Old and new password required'}), 400

            self.user_service.change_password(user_id, old_password, new_password)

            return jsonify({'message': 'Password changed successfully'})

        except DatabaseError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': 'Internal server error'}), 500


@users_bp.route('/api/users/signup', methods=['POST'])
def signup():
    return controller.signup()

@users_bp.route('/api/users/login', methods=['POST'])
def login():
    return controller.login()

@users_bp.route('/api/users/logout', methods=['POST'])
def logout():
    return controller.logout()

@users_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    return controller.delete_user(user_id)

@users_bp.route('/api/users/current', methods=['GET'])
def get_current_user():
    return controller.get_current_user()

@users_bp.route('/api/users/change-password', methods=['POST'])
def change_password():
    return controller.change_password()

controller = None 

def init_controller(user_service: UserService):
    global controller
    controller = UsersController(user_service)