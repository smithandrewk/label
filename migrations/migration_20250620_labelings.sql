-- Migration script to add the labelings table
-- Date: 2025-06-20

-- Check if the table already exists to avoid errors
SET @table_exists = (
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_schema = DATABASE() AND table_name = 'labelings'
);

-- Only create the table if it doesn't exist
SET @sql = IF(@table_exists = 0, 
    'CREATE TABLE labelings (
        labeling_id VARCHAR(36) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        color CHAR(7) NOT NULL,
        visible BOOLEAN NOT NULL DEFAULT TRUE,
        data JSON,
        project_id INT,
        session_id INT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        
        FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
        
        UNIQUE KEY unique_labeling_name (name, project_id, session_id),
        
        INDEX idx_project (project_id),
        INDEX idx_session (session_id)
    )',
    'SELECT "Table labelings already exists, skipping creation." AS message'
);

-- Execute the dynamic SQL
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Create a stored procedure to add default labelings
-- This will run only once when the table is created
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS create_default_labelings()
BEGIN
    -- Check if we have any labelings
    DECLARE labeling_count INT;
    SELECT COUNT(*) INTO labeling_count FROM labelings;
    
    -- Only create default labelings if the table is empty
    IF labeling_count = 0 THEN
        -- Create a default system-wide labeling 
        INSERT INTO labelings (
            labeling_id, 
            name, 
            color, 
            visible, 
            data,
            project_id,
            session_id
        ) VALUES (
            UUID(), 
            'Default Activity Labels', 
            '#1f77b4', 
            TRUE, 
            JSON_OBJECT(
                'timestamps', JSON_ARRAY()
            ),
            NULL, -- NULL for system-wide
            NULL  -- NULL for system-wide
        );
        
        -- Output a message for logging
        SELECT CONCAT('Created default labelings at ', NOW()) AS message;
    ELSE
        -- Output a message for logging
        SELECT 'Default labelings already exist, skipping creation.' AS message;
    END IF;
END //
DELIMITER ;

-- Execute the stored procedure to create default labelings
CALL create_default_labelings();

-- Clean up by dropping the procedure
DROP PROCEDURE IF EXISTS create_default_labelings;

-- Add migration record
-- Note: You may have a migrations tracking table in your schema
-- If so, uncomment and adapt this code:
/*
INSERT INTO schema_migrations (
    version,
    description,
    applied_at
) VALUES (
    '20250620_001',
    'Add labelings table',
    NOW()
);
*/
