import mysql.connector
from mysql.connector import Error
import os

# Initialize MySQL connection
def get_db_connection():
    try:
        # MySQL configuration from environment variables (read at runtime)
        MYSQL_CONFIG = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'user': os.getenv('MYSQL_USER', 'smoking_app'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DATABASE', 'smoking_data')
        }
        return mysql.connector.connect(**MYSQL_CONFIG)
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None