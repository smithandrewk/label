-- Version Control Schema for Label History
-- This provides git-like version control for bout labeling

-- Main version tracking table
CREATE TABLE label_versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    version_hash VARCHAR(32) UNIQUE NOT NULL,
    parent_hash VARCHAR(32) NULL,
    branch_name VARCHAR(100) DEFAULT 'main',
    author_name VARCHAR(100) DEFAULT 'user',
    commit_message TEXT,
    commit_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_current BOOLEAN DEFAULT FALSE,
    metadata JSON, -- Store additional info like commit statistics
    
    INDEX idx_session_id (session_id),
    INDEX idx_version_hash (version_hash),
    INDEX idx_branch_name (branch_name),
    INDEX idx_commit_timestamp (commit_timestamp),
    
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- Individual label changes within each version
CREATE TABLE label_changes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version_hash VARCHAR(32) NOT NULL,
    change_type ENUM('add', 'delete', 'modify', 'split', 'merge') NOT NULL,
    bout_id VARCHAR(64), -- Internal bout identifier for tracking
    start_time BIGINT,
    end_time BIGINT,
    label VARCHAR(100),
    confidence FLOAT DEFAULT 1.0, -- For future AI suggestions
    
    -- Previous values (for modify/delete operations)
    old_start_time BIGINT,
    old_end_time BIGINT,
    old_label VARCHAR(100),
    
    -- Change metadata
    change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT, -- Why this change was made
    
    INDEX idx_version_hash (version_hash),
    INDEX idx_change_type (change_type),
    INDEX idx_bout_id (bout_id),
    
    FOREIGN KEY (version_hash) REFERENCES label_versions(version_hash) ON DELETE CASCADE
);

-- Branch management
CREATE TABLE label_branches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    branch_name VARCHAR(100) NOT NULL,
    created_from_hash VARCHAR(32) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'user',
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX idx_session_id (session_id),
    INDEX idx_branch_name (branch_name),
    
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (created_from_hash) REFERENCES label_versions(version_hash),
    UNIQUE(session_id, branch_name)
);

-- Views for easier querying
CREATE VIEW label_history_view AS
SELECT 
    lv.id,
    lv.session_id,
    s.session_name,
    lv.version_hash,
    lv.parent_hash,
    lv.branch_name,
    lv.author_name,
    lv.commit_message,
    lv.commit_timestamp,
    lv.is_current,
    COUNT(lc.id) as change_count,
    GROUP_CONCAT(DISTINCT lc.change_type ORDER BY lc.change_type) as change_types
FROM label_versions lv
LEFT JOIN sessions s ON lv.session_id = s.session_id
LEFT JOIN label_changes lc ON lv.version_hash = lc.version_hash
GROUP BY lv.id, lv.session_id, s.session_name, lv.version_hash, 
         lv.parent_hash, lv.branch_name, lv.author_name, 
         lv.commit_message, lv.commit_timestamp, lv.is_current
ORDER BY lv.commit_timestamp DESC;

-- Detailed change view
CREATE VIEW label_changes_detailed_view AS
SELECT 
    lc.*,
    lv.session_id,
    lv.branch_name,
    lv.author_name,
    lv.commit_message,
    lv.commit_timestamp,
    s.session_name
FROM label_changes lc
JOIN label_versions lv ON lc.version_hash = lv.version_hash
JOIN sessions s ON lv.session_id = s.session_id
ORDER BY lc.change_timestamp DESC;
