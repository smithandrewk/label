CREATE TABLE participants (
    participant_id INT AUTO_INCREMENT PRIMARY KEY,
    participant_code VARCHAR(50) UNIQUE NOT NULL, -- Unique code (e.g., P001)
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE projects (
    project_id INT AUTO_INCREMENT PRIMARY KEY,
    project_name VARCHAR(255) UNIQUE NOT NULL, -- e.g., P001_2025_Study
    participant_id INT NOT NULL,
    path TEXT,
    watch_assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    watch_returned_at TIMESTAMP NULL, -- Date when participant returns the watch
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (participant_id) REFERENCES participants(participant_id) ON DELETE RESTRICT,
    UNIQUE (participant_id, project_name), -- Ensure unique project names per participant
    labelings JSON
);

CREATE TABLE sessions (
    session_id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    session_name VARCHAR(255) NOT NULL, -- e.g., 2025-01-01
    status VARCHAR(50) DEFAULT 'Initial',
    keep BOOLEAN,
    is_visible TINYINT(1) NOT NULL DEFAULT 1,
    bouts JSON,
    verified TINYINT(1) DEFAULT 0,
    start_ns BIGINT NOT NULL,
    stop_ns BIGINT NOT NULL,
    UNIQUE (project_id, session_name),
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);

CREATE TABLE session_lineage (
    id INT AUTO_INCREMENT PRIMARY KEY,
    child_session_id INT NOT NULL,
    parent_session_id INT NOT NULL,
    split_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (child_session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (parent_session_id) REFERENCES sessions(session_id)
);

CREATE TABLE models (
    model_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    py_filename VARCHAR(255) NOT NULL,
    pt_filename VARCHAR(255) NOT NULL,
    class_name VARCHAR(255) NOT NULL,
    model_settings JSON DEFAULT NULL,
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);