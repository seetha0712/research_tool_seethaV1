from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
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
        max_overflow=10
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

logger.info(f"Database engine created for: {DATABASE_URL.split('@')[0] if '@' in DATABASE_URL else 'SQLite'}")

def init_db(max_retries=5, retry_delay=3):
    """Initialize database with retry logic for cold starts."""
    from app import models  # import models here, NOT at top

    for attempt in range(max_retries):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database initialized successfully")
            return
        except OperationalError as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection failed (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Database connection failed after {max_retries} attempts")
                raise

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()