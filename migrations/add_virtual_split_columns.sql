-- Migration: Add virtual splitting columns to sessions table
-- This migration adds support for virtual splitting by storing offsets instead of creating physical files

ALTER TABLE sessions 
ADD COLUMN parent_session_data_path VARCHAR(500) NULL COMMENT 'Path to parent data file for virtual splits',
ADD COLUMN data_start_offset BIGINT NULL COMMENT 'Start row index for pandas slicing',
ADD COLUMN data_end_offset BIGINT NULL COMMENT 'End row index for pandas slicing';