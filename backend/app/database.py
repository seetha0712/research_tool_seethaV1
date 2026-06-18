from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError, ProgrammingError
import os
import logging
import time

logger = logging.getLogger(__name__)

# Get database URL from environment variable, fallback to SQLite for local dev
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./genai.db")

# PostgreSQL URLs from Render use postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine with appropriate settings
if DATABASE_URL.startswith("sqlite"):
    # SQLite-specific settings
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL settings
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,
        max_overflow=10,
        # Bound each connection attempt so the cold-start retry loop below has
        # honest, deterministic timing (each failed attempt fails within ~5s
        # instead of hanging on the OS default TCP timeout).
        connect_args={"connect_timeout": 5},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

logger.info(f"Database engine created for: {DATABASE_URL.split('@')[0] if '@' in DATABASE_URL else 'SQLite'}")

def _run_migrations():
    """
    Run manual migrations for columns that SQLAlchemy create_all won't add to existing tables.
    Safe to run multiple times - uses IF NOT EXISTS or catches errors.
    """
    migrations = [
        # Add emailed_at column to articles table
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS emailed_at TIMESTAMP;",
    ]

    with engine.connect() as conn:
        for migration in migrations:
            try:
                conn.execute(text(migration))
                conn.commit()
                logger.info(f"Migration executed: {migration[:50]}...")
            except ProgrammingError as e:
                # Column might already exist or other expected error
                if "already exists" in str(e).lower():
                    logger.info(f"Migration skipped (already applied): {migration[:50]}...")
                else:
                    logger.warning(f"Migration warning: {e}")
            except Exception as e:
                logger.warning(f"Migration skipped: {e}")


def init_db(max_retries=60, retry_delay=5):
    """
    Initialize database with a patient, flat retry loop for cold starts.

    Render's free-tier PostgreSQL can take up to ~4 minutes to wake up from
    a suspended state. The app's startup must outlast that cold start on its
    FIRST deploy attempt; otherwise it crashes (exit 3), Render restarts the
    instance, and the ~30s restart penalty blows the Vercel cron's health-poll
    budget -> the scheduled report never gets triggered.

    Flat budget: 60 attempts x 5s = ~5 minutes (each attempt itself is bounded
    to ~5s via connect_timeout, so the wall-clock budget is honest).
    """
    from app import models  # import models here, NOT at top

    for attempt in range(1, max_retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables initialized successfully")

            # Run manual migrations for new columns on existing tables
            _run_migrations()
            logger.info("Database migrations complete")
            return
        except OperationalError as e:
            if attempt < max_retries:
                logger.warning(
                    f"Database connection failed (attempt {attempt}/{max_retries}), "
                    f"retrying in {retry_delay}s... (elapsed ~{attempt * retry_delay}s)"
                )
                time.sleep(retry_delay)
            else:
                logger.error(
                    f"Database connection failed after {max_retries} attempts "
                    f"(~{max_retries * retry_delay}s): {e}"
                )
                raise

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()