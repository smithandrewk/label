CREATE DATABASE accelerometer_db;
USE accelerometer_db;

CREATE TABLE sessions (
    session_name VARCHAR(255) PRIMARY KEY,
    status VARCHAR(50) DEFAULT 'Initial',
    keep BOOLEAN,
    bouts JSON
);