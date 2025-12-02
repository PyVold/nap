-- Fix admin user to have superuser privileges
-- This ensures the admin user can access all endpoints including user/group management

UPDATE users
SET is_superuser = true
WHERE username = 'admin';

-- Verify the change
SELECT id, username, email, role, is_superuser, is_active
FROM users
WHERE username = 'admin';
