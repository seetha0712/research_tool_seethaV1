"""
Database migration script to add pgvector extension and embedding column.
Run this once to enable vector search functionality.
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./genai.db")

# Convert postgres:// to postgresql:// for SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def run_migration():
    """Add pgvector extension and embedding column"""

    # Only run for PostgreSQL
    if not DATABASE_URL.startswith("postgresql://"):
        print("❌ This migration is only for PostgreSQL databases.")
        print(f"Current DATABASE_URL: {DATABASE_URL}")
        print("Vector search requires PostgreSQL with pgvector extension.")
        return

    print(f"🔧 Connecting to database...")
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    with engine.connect() as conn:
        print("📦 Installing pgvector extension...")
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            print("✅ pgvector extension installed successfully")
        except Exception as e:
            print(f"⚠️  Warning installing pgvector extension: {e}")
            print("Make sure your PostgreSQL database supports the pgvector extension.")

        # Check if embedding column already exists
        print("🔍 Checking if embedding column exists...")
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='articles' AND column_name='embedding';
        """))

        if result.fetchone():
            print("ℹ️  embedding column already exists, skipping creation")
        else:
            print("➕ Adding embedding column to articles table...")
            try:
                conn.execute(text("""
                    ALTER TABLE articles
                    ADD COLUMN embedding vector(1536);
                """))
                conn.commit()
                print("✅ embedding column added successfully")
            except Exception as e:
                print(f"❌ Error adding embedding column: {e}")
                return

        # Create index for faster vector similarity searches
        print("📇 Creating vector similarity index...")
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS articles_embedding_idx
                ON articles
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """))
            conn.commit()
            print("✅ Vector index created successfully")
        except Exception as e:
            print(f"⚠️  Warning creating index: {e}")
            print("Index creation may fail if table is empty. This is normal.")

    print("\n✅ Migration completed successfully!")
    print("You can now use vector search with OpenAI embeddings.")

if __name__ == "__main__":
    run_migration()
