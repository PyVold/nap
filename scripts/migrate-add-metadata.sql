#!/bin/bash
# ============================================================================
# Database Migration Script - Add missing columns
# Run with: docker exec -it nap_database_1 psql -U nap_user -d nap_db -f /tmp/migrate.sql
# Or: cat scripts/migrate-add-metadata.sql | docker exec -i nap_database_1 psql -U nap_user -d nap_db
# ============================================================================

-- Add metadata column to devices table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'metadata'
    ) THEN
        ALTER TABLE devices ADD COLUMN metadata JSONB;
        RAISE NOTICE 'Added metadata column to devices table';
    ELSE
        RAISE NOTICE 'metadata column already exists';
    END IF;
END $$;

-- Add backoff tracking columns if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'consecutive_failures'
    ) THEN
        ALTER TABLE devices ADD COLUMN consecutive_failures INTEGER DEFAULT 0;
        RAISE NOTICE 'Added consecutive_failures column';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'last_check_attempt'
    ) THEN
        ALTER TABLE devices ADD COLUMN last_check_attempt TIMESTAMP;
        RAISE NOTICE 'Added last_check_attempt column';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'next_check_due'
    ) THEN
        ALTER TABLE devices ADD COLUMN next_check_due TIMESTAMP;
        RAISE NOTICE 'Added next_check_due column';
    END IF;
END $$;

-- Verify columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'devices'
ORDER BY ordinal_position;
