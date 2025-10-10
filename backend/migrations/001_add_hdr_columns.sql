-- Migration: Add HDR bracket tracking columns
-- Date: 2025-10-10
-- Purpose: Enable tracking of exposure brackets and HDR merged results
-- SQLite Version: 3.35.0+ required (using IF NOT EXISTS)

-- Add columns for HDR bracket tracking (idempotent - safe to run multiple times)
ALTER TABLE captures ADD COLUMN IF NOT EXISTS is_bracket BOOLEAN DEFAULT FALSE;
ALTER TABLE captures ADD COLUMN IF NOT EXISTS bracket_index INTEGER;  -- 0, 1, 2 for under/normal/over
ALTER TABLE captures ADD COLUMN IF NOT EXISTS bracket_ev_offset REAL;  -- -2.0, 0.0, +2.0 etc

-- Add columns for HDR results
ALTER TABLE captures ADD COLUMN IF NOT EXISTS is_hdr_result BOOLEAN DEFAULT FALSE;
ALTER TABLE captures ADD COLUMN IF NOT EXISTS hdr_result_id INTEGER REFERENCES captures(id);  -- Points to merged HDR
ALTER TABLE captures ADD COLUMN IF NOT EXISTS source_bracket_ids TEXT;  -- JSON array: [id1, id2, id3]

-- Create indexes for efficient HDR queries (idempotent)
CREATE INDEX IF NOT EXISTS idx_is_bracket ON captures(is_bracket) WHERE is_bracket = TRUE;
CREATE INDEX IF NOT EXISTS idx_is_hdr_result ON captures(is_hdr_result) WHERE is_hdr_result = TRUE;
CREATE INDEX IF NOT EXISTS idx_hdr_result_id ON captures(hdr_result_id);

-- Verify migration
SELECT 'Migration 001_add_hdr_columns.sql applied successfully' AS status;
