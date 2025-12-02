-- Migration: Add system_config table for admin settings
-- Created: 2025-12-02
-- Description: Stores key-value configuration for system-wide settings

-- Create system_config table
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on key column for fast lookups
CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(key);

-- Insert default backup configuration
INSERT INTO system_config (key, value, description)
VALUES (
    'backup_config',
    '{"enabled": true, "scheduleType": "daily", "scheduleTime": "02:00", "retentionDays": 30, "maxBackupsPerDevice": 10, "compressBackups": true, "notifyOnFailure": true}',
    'Automatic backup configuration'
)
ON CONFLICT (key) DO NOTHING;

-- Insert default system settings
INSERT INTO system_config (key, value, description)
VALUES (
    'system_settings',
    '{"platformName": "Network Audit Platform", "smtpEnabled": false, "smtpServer": "", "smtpPort": 587, "smtpUsername": "", "smtpPassword": "", "defaultSessionTimeout": 3600, "enableAuditLogs": true, "maxFailedLogins": 5}',
    'General system settings'
)
ON CONFLICT (key) DO NOTHING;

-- Insert default notification settings
INSERT INTO system_config (key, value, description)
VALUES (
    'notification_settings',
    '{"emailEnabled": true, "emailRecipients": [], "notifyOnBackupFailure": true, "notifyOnLicenseExpiry": true, "notifyOnQuotaExceeded": true, "notifyOnAuditFailure": true}',
    'Email notification settings'
)
ON CONFLICT (key) DO NOTHING;

-- Verification
SELECT 'Migration completed successfully!' as status;
SELECT COUNT(*) as config_count FROM system_config;
