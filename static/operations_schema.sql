-- Operations tracking schema for session lifecycle management
-- This table tracks all operations performed on sessions throughout their lifecycle

CREATE TABLE session_operations (
    operation_id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NULL, -- NULL for operations that create sessions
    target_session_id INT NULL, -- For operations that affect another session
    operation_type ENUM(
        'UPLOAD',           -- Session created from upload
        'VALIDATION_PASS',  -- Session passed validation
        'VALIDATION_FAIL',  -- Session failed validation and was deleted
        'AUTO_SPLIT',       -- Session was automatically split on time gaps
        'MANUAL_SPLIT',     -- Session was manually split by user
        'DELETE',           -- Session was deleted by user
        'STATUS_CHANGE',    -- Session status was changed
        'BOUT_EDIT',        -- Session bouts were modified
        'KEEP_DECISION'     -- Session keep/discard decision was made
    ) NOT NULL,
    operation_data JSON, -- Store operation-specific details
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'system', -- User who performed operation
    project_id INT NOT NULL,
    
    -- Indexes for efficient querying
    INDEX idx_session_id (session_id),
    INDEX idx_project_id (project_id),
    INDEX idx_operation_type (operation_type),
    INDEX idx_created_at (created_at),
    
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE SET NULL,
    FOREIGN KEY (target_session_id) REFERENCES sessions(session_id) ON DELETE SET NULL,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);

-- View for getting operation graph data with session details
CREATE VIEW session_operations_view AS
SELECT 
    so.operation_id,
    so.session_id,
    so.target_session_id,
    so.operation_type,
    so.operation_data,
    so.created_at,
    so.created_by,
    so.project_id,
    s.session_name,
    s.status as session_status,
    s.keep as session_keep,
    ts.session_name as target_session_name,
    ts.status as target_session_status,
    ts.keep as target_session_keep
FROM session_operations so
LEFT JOIN sessions s ON so.session_id = s.session_id
LEFT JOIN sessions ts ON so.target_session_id = ts.session_id
ORDER BY so.created_at ASC;
