-- Add great_puffs field to participants table
-- This field tracks whether a participant has been marked as having "great puffs"

ALTER TABLE participants 
ADD COLUMN great_puffs BOOLEAN DEFAULT FALSE COMMENT 'Whether participant has been marked as having great puffs';