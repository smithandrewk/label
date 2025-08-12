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
    labelings JSON,
    legacy_path VARCHAR(500) NULL COMMENT 'Original path for backward compatibility',
    project_type ENUM('legacy', 'dataset_based') DEFAULT 'legacy' COMMENT 'Type of project for migration support',
    analysis_config JSON COMMENT 'Project-specific analysis configuration'
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
    parent_session_data_path VARCHAR(500) NULL, -- Path to parent data file for virtual splits
    data_start_offset BIGINT NULL, -- Start row index for pandas slicing
    data_end_offset BIGINT NULL, -- End row index for pandas slicing
    dataset_id INT NULL COMMENT 'Reference to raw dataset for dataset-based sessions',
    raw_session_name VARCHAR(255) NULL COMMENT 'Original session name in raw dataset',
    split_config_id INT NULL COMMENT 'Reference to split configuration used',
    UNIQUE (project_id, session_name),
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    INDEX idx_session_dataset (dataset_id),
    INDEX idx_session_raw_name (raw_session_name)
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

-- Raw datasets management tables
CREATE TABLE raw_datasets (
    dataset_id INT AUTO_INCREMENT PRIMARY KEY,
    dataset_name VARCHAR(255) NOT NULL,
    dataset_hash VARCHAR(64) UNIQUE NOT NULL COMMENT 'SHA256 hash of dataset contents for deduplication',
    file_path VARCHAR(500) NOT NULL COMMENT 'Path to raw data directory',
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_size_bytes BIGINT COMMENT 'Total size of dataset files',
    session_count INT DEFAULT 0 COMMENT 'Number of original sessions in dataset',
    description TEXT COMMENT 'Optional description of the dataset',
    metadata JSON COMMENT 'Additional metadata about the dataset',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_dataset_hash (dataset_hash),
    INDEX idx_dataset_name (dataset_name)
);

-- Table to store original session structure from raw datasets
CREATE TABLE raw_dataset_sessions (
    raw_session_id INT AUTO_INCREMENT PRIMARY KEY,
    dataset_id INT NOT NULL,
    session_name VARCHAR(255) NOT NULL,
    session_path VARCHAR(500) NOT NULL COMMENT 'Path to session directory within dataset',
    original_labels_json TEXT COMMENT 'Original labels.json content if present',
    file_count INT DEFAULT 0 COMMENT 'Number of files in session directory',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES raw_datasets(dataset_id) ON DELETE CASCADE,
    INDEX idx_dataset_session (dataset_id, session_name),
    UNIQUE KEY unique_dataset_session (dataset_id, session_name)
);

-- Many-to-many relationship between projects and raw datasets
CREATE TABLE project_dataset_refs (
    ref_id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    dataset_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    FOREIGN KEY (dataset_id) REFERENCES raw_datasets(dataset_id) ON DELETE CASCADE,
    UNIQUE KEY unique_project_dataset (project_id, dataset_id),
    INDEX idx_project_refs (project_id),
    INDEX idx_dataset_refs (dataset_id)
);

-- Table to store virtual splitting configurations per project
CREATE TABLE project_split_configs (
    config_id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    dataset_id INT NOT NULL,
    raw_session_name VARCHAR(255) NOT NULL COMMENT 'Original session name from raw dataset',
    split_strategy ENUM('time_based', 'bout_based', 'custom') DEFAULT 'time_based',
    split_parameters JSON COMMENT 'Parameters for splitting strategy (time windows, bout boundaries, etc.)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    FOREIGN KEY (dataset_id) REFERENCES raw_datasets(dataset_id) ON DELETE CASCADE,
    INDEX idx_project_splits (project_id),
    INDEX idx_dataset_splits (dataset_id)
);