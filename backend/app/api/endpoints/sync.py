from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app import models, database
from app.dependencies import get_current_user
from app.services import rss_service, pdf_utils, llm_service
from app.services import embedding_service, audit_service
import os
from app.services.api_service import API_SOURCE_HANDLERS
from pydantic import BaseModel
from datetime import datetime
from app.core.config import CATEGORY_OPTIONS

router = APIRouter()

import logging
logger = logging.getLogger(__name__)

class SyncParams(BaseModel):
    limit: int = 10
    from_date: str = ""   # ISO string or blank

@router.post("/")
def sync_all_sources(
    params: SyncParams,
    request: Request,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    # Check if user is admin
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admin users can sync sources")

    limit = params.limit or 10
    from_date = params.from_date
    # Parse date string (ISO format) to datetime
    start_dt = None
    if from_date:
        try:
            start_dt = datetime.fromisoformat(from_date)
        except Exception:
            start_dt = None
    
    sources = db.query(models.Source).filter(models.Source.user_id == user.id, models.Source.active == True).all()
    synced = []

    for src in sources:
        try:
            if src.type == "rss":
                # Check if source has any articles - if not, reset last_synced to fetch all
                article_count = db.query(models.Article).filter(models.Article.source_id == src.id).count()
                if article_count == 0:
                    # No articles for this source, reset to fetch all
                    last_synced = start_dt if start_dt else None
                else:
                    last_synced = start_dt if start_dt else src.last_synced
                logger.info(f"last synced date is:{last_synced} (article_count={article_count})")
                items = rss_service.fetch_rss_items(src.url, last_synced=last_synced,limit=limit)
                for item in items:
                    # Deduplication: by GUID or link/title
                    exists = db.query(models.Article).filter_by(source_id=src.id, title=item['title']).first()
                    if exists:
                        continue
                    # Use best available summary (do not paraphrase at this stage)
                    summary = item['summary'] or item['title']

                    # 2 Key insights from summary/title
                    try:
                        key_insights = llm_service.key_insights(summary)
                    except Exception as e:
                        logger.error(f"[LLM Error] Key Insights for '{item['title']}': {e}")
                        key_insights = []
                    
                    # --- NEW: Add relevance scoring and category ---
                    try:
                        relevance_score = llm_service.score_article(summary)
                    except Exception as e:
                        print(f"[LLM Error] Scoring RSS article '{item['title']}': {e}")
                        relevance_score = 0

                    try:
                        category = llm_service.categorize_article(summary)
                    except Exception as e:
                        print(f"[LLM Error] Categorizing RSS article '{item['title']}': {e}")
                        category = "Tech Corner"

                    # Generate embedding for vector search
                    embedding = None
                    try:
                        embedding = embedding_service.generate_embedding(summary)
                    except Exception as e:
                        logger.warning(f"[Embedding Error] for article '{item['title']}': {e}")

                    article = models.Article(
                        user_id=user.id,
                        source_id=src.id,
                        title=item['title'],
                        summary=summary,
                        key_insights=key_insights,
                        content=item.get('summary', ''),
                        date=item.get('published'),
                        meta_data={"link": item.get('link'), "guid": item.get('guid')},
                        status="new",
                        relevance_score=relevance_score,
                        category=category,
                        embedding=embedding
                    )
                    db.add(article)
                    db.commit()
                    db.refresh(article)
                    synced.append(article.title)
                src.last_synced = datetime.utcnow()
                db.commit()

            elif src.type == "pdf":
                # Only process if not done before
                if not src.file_path:
                    continue
                file_hash = os.path.basename(src.file_path).split("_")[0]
                exists = db.query(models.Article).filter_by(source_id=src.id).first()
                if exists:
                    continue
                try:
                    text = pdf_utils.extract_text(src.file_path)
                except Exception as e:
                    print(f"[PDF Error] Extracting '{src.file_path}': {e}")
                    continue
                try:
                    summary = llm_service.summarize_article(text[:2000])
                except Exception as e:
                    print(f"[LLM Error] Summarizing PDF '{src.name}': {e}")
                    summary = text[:300]

                # Generate embedding
                embedding = None
                try:
                    embedding = embedding_service.generate_embedding(summary)
                except Exception as e:
                    logger.warning(f"[Embedding Error] for PDF '{src.name}': {e}")

                article = models.Article(
                    user_id=user.id,
                    source_id=src.id,
                    title=src.name,
                    summary=summary,
                    content=text,
                    status="new",
                    embedding=embedding
                )
                db.add(article)
                db.commit()
                db.refresh(article)
                src.last_synced = datetime.utcnow()
                db.commit()
                synced.append(src.name)

            elif src.type == "api":
                try:
                    synced_titles = sync_api_articles(src, db, user)
                    synced.extend(synced_titles)
                except Exception as e:
                    print(f"[API Error] Syncing API source '{src.name}': {e}")

        except Exception as e:
            print(f"[Sync Error] Source '{src.name}' ({src.type}): {e}")
            # You can optionally continue, or raise to fail the sync

    # Log sync action
    audit_service.log_action(
        db=db,
        user=user,
        action="SYNC",
        details={"count": len(synced), "limit": limit, "from_date": from_date},
        request=request
    )

    return {"synced": synced, "count": len(synced)}

def sync_api_articles(source, db, user):
    provider = source.provider or "tavily"
    query = source.query or source.name   # fallback if query is blank

    handler = API_SOURCE_HANDLERS.get(provider)
    if not handler:
        raise Exception(f"No handler registered for API provider: {provider}")

    try:
        articles = handler(query)
    except Exception as e:
        print(f"[API Handler Error] Calling provider '{provider}': {e}")
        return []

    synced_titles = []
    for item in articles:
        exists = db.query(models.Article).filter_by(source_id=source.id, title=item['title']).first()
        if exists:
            continue
        try:
            summary = llm_service.summarize_article(item.get('summary') or item.get('title'))
        except Exception as e:
            print(f"[LLM Error] Summarizing API article '{item['title']}': {e}")
            summary = item.get('summary') or item.get('title')

        # Generate embedding
        embedding = None
        try:
            embedding = embedding_service.generate_embedding(summary)
        except Exception as e:
            logger.warning(f"[Embedding Error] for API article '{item['title']}': {e}")

        article = models.Article(
            user_id=user.id,
            source_id=source.id,
            title=item['title'],
            summary=summary,
            content=item.get('content', ''),
            date=item.get('published'),
            meta_data=item.get('meta_data', {}),
            status="new",
            embedding=embedding
        )
        db.add(article)
        db.commit()
        db.refresh(article)
        synced_titles.append(article.title)
    source.last_synced = datetime.utcnow()
    db.commit()
    return synced_titles