"""
Migration script to add admin and audit features to the database.
Safe to run multiple times - checks for existence before creating.

Run this script:
    python backend/migrate_admin_and_audit.py
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./genai.db")

# Convert postgres:// to postgresql:// for SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def column_exists(inspector, table_name, column_name):
    """Check if a column exists in a table"""
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def table_exists(inspector, table_name):
    """Check if a table exists"""
    return table_name in inspector.get_table_names()

def run_migration():
    """Run the migration safely"""
    print("=" * 60)
    print("Admin & Audit Features Migration")
    print("=" * 60)
    print(f"\nConnecting to database...")
    print(f"Database: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}\n")

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    inspector = inspect(engine)

    with engine.connect() as conn:
        # 1. Add is_admin column to users table
        print("1. Checking users.is_admin column...")
        if column_exists(inspector, 'users', 'is_admin'):
            print("   ✓ users.is_admin already exists - skipping")
        else:
            print("   → Adding users.is_admin column...")
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;"))
                conn.commit()
                print("   ✓ users.is_admin added successfully")
            except Exception as e:
                print(f"   ✗ Error adding is_admin: {e}")
                conn.rollback()

        # 2. Create audit_logs table
        print("\n2. Checking audit_logs table...")
        if table_exists(inspector, 'audit_logs'):
            print("   ✓ audit_logs table already exists - skipping")
        else:
            print("   → Creating audit_logs table...")
            try:
                conn.execute(text("""
                    CREATE TABLE audit_logs (
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
                """))
                conn.commit()
                print("   ✓ audit_logs table created successfully")

                # Create index on timestamp
                print("   → Creating index on timestamp...")
                try:
                    conn.execute(text("CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);"))
                    conn.commit()
                    print("   ✓ Index created successfully")
                except Exception as e:
                    print(f"   ⚠ Warning creating index: {e}")
                    conn.rollback()

            except Exception as e:
                print(f"   ✗ Error creating audit_logs table: {e}")
                conn.rollback()

        # 3. Set admin user (optional)
        print("\n3. Setting admin user...")
        admin_username = input("   Enter username to set as admin (or press Enter to skip): ").strip()

        if admin_username:
            try:
                result = conn.execute(
                    text("UPDATE users SET is_admin = TRUE WHERE username = :username RETURNING id, username;"),
                    {"username": admin_username}
                )
                updated = result.fetchone()

                if updated:
                    conn.commit()
                    print(f"   ✓ User '{updated[1]}' (ID: {updated[0]}) set as admin")
                else:
                    print(f"   ✗ User '{admin_username}' not found")

            except Exception as e:
                print(f"   ✗ Error setting admin user: {e}")
                conn.rollback()
        else:
            print("   ⊙ Skipped setting admin user")

        # 4. Show current admins
        print("\n4. Current admin users:")
        try:
            result = conn.execute(text("SELECT id, username, is_admin FROM users WHERE is_admin = TRUE;"))
            admins = result.fetchall()

            if admins:
                for admin in admins:
                    print(f"   • {admin[1]} (ID: {admin[0]})")
            else:
                print("   ⚠ No admin users found!")
                print("\n   To set an admin manually, run:")
                print("   UPDATE users SET is_admin = TRUE WHERE username = 'your_username';")
        except Exception as e:
            print(f"   ✗ Error listing admins: {e}")

    print("\n" + "=" * 60)
    print("Migration completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Restart your backend server to pick up the changes")
    print("2. Login with an admin user to see the new features:")
    print("   - Admin-only Sync button")
    print("   - Audit Logs tab")
    print("   - Turn On/Off All Sources buttons")
    print("\n")

if __name__ == "__main__":
    try:
        run_migration()
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Migration failed with error:")
        print(f"  {e}")
        sys.exit(1)
