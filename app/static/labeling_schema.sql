-- Schema definition for the labelings table

CREATE TABLE labelings (
    labeling_id VARCHAR(36) PRIMARY KEY, -- UUID format
    name VARCHAR(255) NOT NULL,
    color CHAR(7) NOT NULL, -- Hex color code format (#RRGGBB)
    visible BOOLEAN NOT NULL DEFAULT TRUE,
    data JSON, -- Will store the labeling data as JSON
    project_id INT, -- Can be NULL if it's a global/system labeling
    session_id INT, -- Can be NULL if it applies to multiple sessions
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    
    -- Ensure unique names within the same context (project/session)
    UNIQUE KEY unique_labeling_name (name, project_id, session_id),
    
    -- Add indexes for faster queries
    INDEX idx_project (project_id),
    INDEX idx_session (session_id)
);

-- Comments explaining the schema:

-- labeling_id: Primary key using UUID format for globally unique identifiers
--   This matches the 'id' attribute in the Labeling class

-- name: Required name field for the labeling
--   This matches the 'name' attribute in the Labeling class

-- color: Required color field in hex format (#RRGGBB)
--   This matches the 'color' attribute in the Labeling class

-- visible: Boolean field indicating if the labeling is visible
--   This matches the 'visible' attribute in the Labeling class

-- data: JSON field to store the actual labeling data
--   This matches the 'data' attribute in the Labeling class
--   Stores timestamps and labels in the format:
--   {
--     "timestamps": [
--       {"start": 1000.0, "end": 1500.0, "label": "walking"},
--       ...
--     ]
--   }

-- project_id: Foreign key to projects table
--   Can be NULL for global/system labelings
--   Allows scoping labelings to specific projects

-- session_id: Foreign key to sessions table
--   Can be NULL for project-level labelings
--   Allows scoping labelings to specific sessions

-- created_at: Timestamp of when the labeling was created
--   This matches the 'created_at' attribute in the Labeling class

-- updated_at: Timestamp of the last update
--   This matches the 'updated_at' attribute in the Labeling class
--   Automatically updates when the row is updated

-- Constraints:
-- - The unique key ensures that labeling names are unique within the same context
--   (i.e., within the same project/session)
-- - ON DELETE CASCADE ensures that when a project or session is deleted,
--   its associated labelings are also deleted
