-- Migration: Create raw datasets management tables
-- This migration separates raw data storage from project-specific analysis

-- Table to store raw dataset metadata and file locations
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

-- Add columns to existing projects table to support new architecture
ALTER TABLE projects 
ADD COLUMN legacy_path VARCHAR(500) NULL COMMENT 'Original path for backward compatibility',
ADD COLUMN project_type ENUM('legacy', 'dataset_based') DEFAULT 'legacy' COMMENT 'Type of project for migration support',
ADD COLUMN analysis_config JSON COMMENT 'Project-specific analysis configuration';

-- Update the path column to be nullable for dataset-based projects
ALTER TABLE projects 
MODIFY COLUMN path VARCHAR(500) NULL COMMENT 'Legacy project path, null for dataset-based projects';

-- Add columns to sessions table to reference raw datasets
ALTER TABLE sessions
ADD COLUMN dataset_id INT NULL COMMENT 'Reference to raw dataset for dataset-based sessions',
ADD COLUMN raw_session_name VARCHAR(255) NULL COMMENT 'Original session name in raw dataset',
ADD COLUMN split_config_id INT NULL COMMENT 'Reference to split configuration used',
ADD INDEX idx_session_dataset (dataset_id),
ADD INDEX idx_session_raw_name (raw_session_name);

-- Add foreign key constraints for sessions table (will be added after data migration)
-- ALTER TABLE sessions 
-- ADD CONSTRAINT fk_session_dataset FOREIGN KEY (dataset_id) REFERENCES raw_datasets(dataset_id),
-- ADD CONSTRAINT fk_session_split_config FOREIGN KEY (split_config_id) REFERENCES project_split_configs(config_id);