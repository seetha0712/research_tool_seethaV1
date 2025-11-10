-- Migration: Add admin and audit features
-- Safe to run multiple times - uses IF NOT EXISTS checks
--
-- Usage:
--   Run this directly in your PostgreSQL client or via psql:
--   psql $DATABASE_URL -f backend/migrations/001_add_admin_and_audit.sql

-- ============================================
-- 1. Add is_admin column to users table
-- ============================================

-- Check and add is_admin column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'is_admin'
    ) THEN
        ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added is_admin column to users table';
    ELSE
        RAISE NOTICE 'Column is_admin already exists - skipping';
    END IF;
END $$;

-- ============================================
-- 2. Create audit_logs table
-- ============================================

-- Create audit_logs table if it doesn't exist
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    username VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    resource_type VARCHAR,
    resource_id INTEGER,
    details JSON,
    ip_address VARCHAR,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on timestamp if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'audit_logs' AND indexname = 'idx_audit_timestamp'
    ) THEN
        CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
        RAISE NOTICE 'Created index idx_audit_timestamp';
    ELSE
        RAISE NOTICE 'Index idx_audit_timestamp already exists - skipping';
    END IF;
END $$;

-- ============================================
-- 3. Set admin user (OPTIONAL - CUSTOMIZE THIS)
-- ============================================

-- Option A: Set a specific user as admin
-- UPDATE users SET is_admin = TRUE WHERE username = 'seetha1';

-- Option B: Set the first user as admin
-- UPDATE users SET is_admin = TRUE WHERE id = 1;

-- Option C: Interactive - uncomment to see current users and choose
-- SELECT id, username, is_admin FROM users ORDER BY id;

-- ============================================
-- 4. Verify migration
-- ============================================

-- Show current admin users
DO $$
DECLARE
    admin_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO admin_count FROM users WHERE is_admin = TRUE;

    IF admin_count = 0 THEN
        RAISE WARNING 'No admin users found! Remember to set at least one user as admin:';
        RAISE WARNING 'UPDATE users SET is_admin = TRUE WHERE username = ''your_username'';';
    ELSE
        RAISE NOTICE 'Found % admin user(s)', admin_count;
    END IF;
END $$;

-- List all admin users
SELECT
    id,
    username,
    is_admin,
    CASE WHEN is_admin THEN '✓ Admin' ELSE '✗ Regular' END as role
FROM users
ORDER BY is_admin DESC, id;

-- Show table info
SELECT
    'users' as table_name,
    COUNT(*) as total_users,
    SUM(CASE WHEN is_admin THEN 1 ELSE 0 END) as admin_users
FROM users
UNION ALL
SELECT
    'audit_logs' as table_name,
    COUNT(*) as total_records,
    NULL as admin_users
FROM audit_logs;
