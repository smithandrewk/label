from flask import Flask, jsonify, send_from_directory, request
import os
import pandas as pd
import mysql.connector
from mysql.connector import Error
import json
import shutil
from datetime import datetime

app = Flask(__name__, static_folder='static')

# Directory containing session data
DATA_DIR = '~/.delta/data'

# MySQL configuration
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Password123!',
    'database': 'adb'
}

# Initialize MySQL connection
def get_db_connection():
    try:
        return mysql.connector.connect(**MYSQL_CONFIG)
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def test_db_connection():
    conn = get_db_connection()
    if conn:
        print("Database connection successful")
        conn.close()
    else:
        print("Database connection failed")

def show_tables():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    cursor.close()
    conn.close()
    return tables

test_db_connection()
print(show_tables())