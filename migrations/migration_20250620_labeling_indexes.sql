-- Migration script to add additional indexes for efficient querying of the labelings table
-- Date: 2025-06-20

-- Create an index for visibility filtering
-- This will improve queries that filter by the visible flag
SET @visibility_index_exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'labelings' AND index_name = 'idx_visible'
);

SET @sql_visibility = IF(@visibility_index_exists = 0,
    'CREATE INDEX idx_visible ON labelings(visible)',
    'SELECT "Index idx_visible already exists, skipping creation." AS message'
);

PREPARE stmt FROM @sql_visibility;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Create a composite index for project_id and visibility
-- This will improve queries that filter by both project and visibility status
SET @project_visible_index_exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'labelings' AND index_name = 'idx_project_visible'
);

SET @sql_project_visible = IF(@project_visible_index_exists = 0,
    'CREATE INDEX idx_project_visible ON labelings(project_id, visible)',
    'SELECT "Index idx_project_visible already exists, skipping creation." AS message'
);

PREPARE stmt FROM @sql_project_visible;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Create a composite index for session_id and visibility
-- This will improve queries that filter by both session and visibility status
SET @session_visible_index_exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'labelings' AND index_name = 'idx_session_visible'
);

SET @sql_session_visible = IF(@session_visible_index_exists = 0,
    'CREATE INDEX idx_session_visible ON labelings(session_id, visible)',
    'SELECT "Index idx_session_visible already exists, skipping creation." AS message'
);

PREPARE stmt FROM @sql_session_visible;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Create a full-text index on name for search functionality
-- This will enable efficient text search on labeling names
SET @fulltext_index_exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'labelings' AND index_name = 'idx_name_fulltext'
);

SET @sql_fulltext = IF(@fulltext_index_exists = 0,
    'CREATE FULLTEXT INDEX idx_name_fulltext ON labelings(name)',
    'SELECT "Fulltext index idx_name_fulltext already exists, skipping creation." AS message'
);

PREPARE stmt FROM @sql_fulltext;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Create an index on updated_at for efficient sorting by last modified
-- This will improve queries that sort by last modified date
SET @updated_index_exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'labelings' AND index_name = 'idx_updated_at'
);

SET @sql_updated = IF(@updated_index_exists = 0,
    'CREATE INDEX idx_updated_at ON labelings(updated_at)',
    'SELECT "Index idx_updated_at already exists, skipping creation." AS message'
);

PREPARE stmt FROM @sql_updated;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Create an index document to explain the purpose of each index
CREATE TABLE IF NOT EXISTS schema_documentation (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(64) NOT NULL,
    index_name VARCHAR(64) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document the indexes
INSERT INTO schema_documentation (table_name, index_name, description)
VALUES 
    ('labelings', 'PRIMARY', 'Primary key using labeling_id for unique identification of each labeling record.'),
    ('labelings', 'idx_project', 'Simple index on project_id to improve the performance of queries filtering by project.'),
    ('labelings', 'idx_session', 'Simple index on session_id to improve the performance of queries filtering by session.'),
    ('labelings', 'unique_labeling_name', 'Unique key on (name, project_id, session_id) to ensure labeling names are unique within the same context.'),
    ('labelings', 'idx_visible', 'Simple index on the visible flag to improve performance of queries filtering by visibility.'),
    ('labelings', 'idx_project_visible', 'Composite index on (project_id, visible) for efficient filtering of visible labelings within a project.'),
    ('labelings', 'idx_session_visible', 'Composite index on (session_id, visible) for efficient filtering of visible labelings within a session.'),
    ('labelings', 'idx_name_fulltext', 'Fulltext index on name to enable efficient text search on labeling names.'),
    ('labelings', 'idx_updated_at', 'Index on updated_at for efficient sorting by last modified date.')
ON DUPLICATE KEY UPDATE description = VALUES(description);

SELECT 'Successfully added and documented indexes for the labelings table' AS result;
