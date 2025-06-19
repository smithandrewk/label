import mysql.connector
from mysql.connector import Error
import os

# MySQL configuration from environment variables
MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'user': os.getenv('MYSQL_USER', 'smoking_app'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE', 'smoking_data')
}

# Initialize MySQL connection
def get_db_connection():
    try:
        return mysql.connector.connect(**MYSQL_CONFIG)
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None