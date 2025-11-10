# Database Migrations

This directory contains database migration scripts for the GenAI Research Tool.

## Migration 001: Admin & Audit Features

Adds:
- `is_admin` column to `users` table
- `audit_logs` table for tracking user actions
- Indexes for performance

### Option 1: Python Migration Script (Recommended)

**Advantages:**
- Interactive - prompts you to set an admin user
- Safe - checks if changes already exist
- Shows current state and next steps

**Usage:**
```bash
# From project root
python backend/migrate_admin_and_audit.py
```

**Requirements:**
- Python 3.11+
- `.env` file with `DATABASE_URL` set
- `sqlalchemy` and `python-dotenv` installed

### Option 2: SQL Script (Direct Database)

**Advantages:**
- No dependencies required
- Can run directly in any PostgreSQL client
- Fastest option

**Usage:**

#### Via psql:
```bash
psql $DATABASE_URL -f backend/migrations/001_add_admin_and_audit.sql
```

#### Via Database Client (pgAdmin, DBeaver, etc.):
1. Open `backend/migrations/001_add_admin_and_audit.sql`
2. Copy the entire contents
3. Run in your database client's query window

#### Via Render Dashboard:
1. Go to your Render PostgreSQL dashboard
2. Click "Connect" → "External Connection"
3. Open a PostgreSQL client with those credentials
4. Run the SQL script

### Setting Your Admin User

After running the migration, set yourself as admin:

**Python script:**
```bash
python backend/migrate_admin_and_audit.py
# It will prompt you for a username
```

**SQL:**
```sql
UPDATE users SET is_admin = TRUE WHERE username = 'your_username';
```

**Verify:**
```sql
SELECT id, username, is_admin FROM users;
```

## What If I Already Ran Part of This?

Both scripts are **idempotent** - safe to run multiple times:
- They check if columns/tables exist before creating
- Won't error if things are already in place
- Will skip existing items and only add what's missing

So if you got the error:
```
ERROR: column "is_admin" of relation "users" already exists
```

Just run the Python migration script - it will:
1. ✓ Skip the is_admin column (already exists)
2. → Create the audit_logs table (if missing)
3. → Set your admin user (if you want)

## Verification

After running the migration, verify it worked:

```sql
-- Check users table
\d users

-- Check audit_logs table
\d audit_logs

-- See admin users
SELECT id, username, is_admin FROM users WHERE is_admin = TRUE;
```

## Troubleshooting

### "relation does not exist" errors
- Make sure you're connected to the correct database
- Check that your `DATABASE_URL` is correct

### "permission denied" errors
- Ensure your database user has CREATE/ALTER permissions
- Contact your database admin if using a managed database

### No admin users after migration
```sql
-- Set yourself as admin
UPDATE users SET is_admin = TRUE WHERE username = 'your_username';
```

## Next Steps

After successful migration:

1. **Restart your backend server** (Render will auto-restart)
2. **Login** with your admin user
3. **Test new features:**
   - ✓ Sync Now button (admin only)
   - ✓ "Turn On/Off All Sources" buttons
   - ✓ "Audit Logs" tab in Admin section
   - ✓ Email sharing in Deck Builder

## Future Migrations

Add new migration files as:
- `002_migration_name.sql`
- `003_another_migration.sql`

Always include:
- IF NOT EXISTS checks
- Rollback plan
- Verification queries
