-- Add separate verification columns for puffs and smoking
-- Migration: Add dual verification support

ALTER TABLE sessions 
ADD COLUMN puffs_verified TINYINT(1) DEFAULT 0 COMMENT 'Whether puffs have been verified for this session',
ADD COLUMN smoking_verified TINYINT(1) DEFAULT 0 COMMENT 'Whether smoking has been verified for this session';

-- Copy existing verified status to both new columns for backward compatibility
UPDATE sessions 
SET puffs_verified = verified, smoking_verified = verified 
WHERE verified IS NOT NULL;