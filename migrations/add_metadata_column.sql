-- Migration: Add metadata column to devices table
-- Date: 2025-12-03
-- Description: Add JSON column to store protocol and system metadata collected during discovery

-- Add metadata column if it doesn't exist
ALTER TABLE devices ADD COLUMN IF NOT EXISTS metadata JSON;

-- Add comment for documentation
COMMENT ON COLUMN devices.metadata IS 'Protocol and system metadata (BGP, IGP, LDP, MPLS, system info) collected during discovery';
