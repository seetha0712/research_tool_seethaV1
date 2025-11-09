# Migration Guide: Adding Vector Search with OpenAI Embeddings

This guide will help you enable vector search functionality using OpenAI embeddings and PostgreSQL pgvector.

## What This Migration Does

1. ✅ Installs the `pgvector` extension in your PostgreSQL database
2. ✅ Adds an `embedding` column to the `articles` table (1536 dimensions for OpenAI embeddings)
3. ✅ Creates an index for fast vector similarity searches

## Prerequisites

- PostgreSQL database on Render (you already have this)
- Python environment with access to your database
- `OPENAI_API_KEY` environment variable set in Render

## Steps to Run Migration

### Option 1: Via Render Shell (Recommended)

1. **Go to Render Dashboard**
   - Navigate to https://dashboard.render.com
   - Select your backend service: `research-tool-seethav1`

2. **Open Shell**
   - Click on "Shell" tab in the left sidebar
   - Wait for the shell to connect

3. **Run Migration Script**
   ```bash
   cd backend
   python add_vector_extension.py
   ```

4. **Verify Success**
   You should see:
   ```
   ✅ pgvector extension installed successfully
   ✅ embedding column added successfully
   ✅ Vector index created successfully
   ✅ Migration completed successfully!
   ```

### Option 2: Via Local Connection

If you prefer to run the migration from your local machine:

1. **Get Database URL from Render**
   - Go to your Render dashboard
   - Navigate to your PostgreSQL database
   - Copy the "External Database URL"

2. **Set Environment Variable Locally**
   ```bash
   export DATABASE_URL="your-postgres-url-here"
   ```

3. **Run Migration**
   ```bash
   cd backend
   python add_vector_extension.py
   ```

## After Migration

### Test Vector Search

1. **Add Some Articles**
   - Sync your RSS sources
   - New articles will automatically get embeddings

2. **Try Semantic Search**
   - Go to Articles tab
   - Search for "banking AI applications"
   - You'll get semantically similar results, not just keyword matches!

### How It Works

**Before Migration:**
- Search: "GenAI in banking"
- Results: Only articles with exact keywords "GenAI" or "banking"

**After Migration:**
- Search: "GenAI in banking"
- Results: Articles about AI in finance, machine learning in banks, etc.
- Even if they don't contain the exact keywords!

## Troubleshooting

### Error: "pgvector extension not available"

This means your PostgreSQL version doesn't support pgvector. You need PostgreSQL 11+.

**Solution:**
- Check your PostgreSQL version on Render
- If needed, upgrade to a newer PostgreSQL version

### Error: "permission denied to create extension"

Your database user doesn't have permission to create extensions.

**Solution:**
```sql
-- Run this as a superuser in your PostgreSQL console
GRANT CREATE ON DATABASE your_database_name TO your_user;
```

### Migration Already Run

If you see:
```
ℹ️  embedding column already exists, skipping creation
```

This is normal - the migration has already been run. No action needed!

## Rollback (If Needed)

If you want to remove the embedding functionality:

```sql
-- Connect to your PostgreSQL database
DROP INDEX IF EXISTS articles_embedding_idx;
ALTER TABLE articles DROP COLUMN IF EXISTS embedding;
DROP EXTENSION IF EXISTS vector;
```

## Benefits After Migration

✅ **More Accurate Search**: Semantic understanding vs keyword matching
✅ **Better User Experience**: Find relevant articles even with different wording
✅ **Fast Performance**: Optimized vector index for quick searches
✅ **Cost Effective**: Uses OpenAI's efficient embedding model
✅ **No Local Models**: No need for 90MB+ sentence-transformers

## Questions?

- Check Render logs if migration fails
- Ensure `OPENAI_API_KEY` is set in Render environment variables
- Make sure your PostgreSQL is version 11 or higher
