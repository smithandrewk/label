-- Sample data for smoking detection database

-- Clear existing data (in reverse order of dependencies)
DELETE FROM session_lineage;
DELETE FROM sessions;
DELETE FROM projects;
DELETE FROM participants;

-- Reset auto-increment counters
ALTER TABLE participants AUTO_INCREMENT = 1;
ALTER TABLE projects AUTO_INCREMENT = 1;
ALTER TABLE sessions AUTO_INCREMENT = 1;

-- Insert sample participants
INSERT INTO participants (participant_code, first_name, last_name, email, notes) VALUES
('P001', 'John', 'Doe', 'john.doe@example.com', 'Test participant for smoking detection study'),
('P002', 'Jane', 'Smith', 'jane.smith@example.com', 'Control group participant'),
('P003', 'Bob', 'Johnson', 'bob.johnson@example.com', 'Heavy smoker participant for calibration');

-- Insert sample projects
INSERT INTO projects (project_name, participant_id, path, watch_assigned_at, watch_returned_at) VALUES
('P001_2025_Study', 1, '/data/P001_2025_Study', '2025-01-01 09:00:00', NULL),
('P002_2025_Study', 2, '/data/P002_2025_Study', '2025-01-01 10:00:00', '2025-01-07 15:00:00'),
('P003_2025_Study', 3, '/data/P003_2025_Study', '2025-01-02 08:30:00', NULL);

-- Insert sample sessions
INSERT INTO sessions (project_id, session_name, status, keep, is_visible, bouts, verified) VALUES
(1, '2025-01-01_morning', 'Initial', NULL, 1, '[[1735689600000000000, 1735689660000000000], [1735689800000000000, 1735689860000000000]]', 0),
(1, '2025-01-01_afternoon', 'Reviewed', 1, 1, '[[1735718400000000000, 1735718460000000000]]', 1),
(1, '2025-01-02_morning', 'Split', 0, 0, '[]', 0),
(2, '2025-01-01_session1', 'Initial', NULL, 1, '[]', 0),
(2, '2025-01-02_session1', 'Reviewed', 0, 1, '[]', 1),
(3, '2025-01-02_calibration', 'Initial', NULL, 1, '[[1735776000000000000, 1735776120000000000], [1735776300000000000, 1735776360000000000], [1735776600000000000, 1735776720000000000]]', 0);

-- Insert sample session lineage (showing split relationships)
INSERT INTO session_lineage (child_session_id, parent_session_id, split_timestamp) VALUES
(1, 3, '2025-01-02 10:15:00'),
(2, 3, '2025-01-02 10:15:00');
