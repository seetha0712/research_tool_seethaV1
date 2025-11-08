from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, database
from app.dependencies import get_current_user
from app.services import rss_service, pdf_utils, llm_service, chroma_service
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
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
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
                last_synced = start_dt if start_dt else src.last_synced
                logger.info(f"last synced date is:{last_synced}")
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
                        category=category   
                    )
                    db.add(article)
                    db.commit()
                    db.refresh(article)
                    # Chroma: embed & store
                    try:
                        chroma_service.store_chunks([article.summary], {"article_id": article.id,"user_id": article.user_id})
                    except Exception as e:
                        print(f"[Chroma Error] Storing RSS article '{article.title}': {e}")
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
                article = models.Article(
                    user_id=user.id,
                    source_id=src.id,
                    title=src.name,
                    summary=summary,
                    content=text,
                    status="new"
                )
                db.add(article)
                db.commit()
                db.refresh(article)
                try:
                    chroma_service.store_chunks([text], {"article_id": article.id,"user_id": article.user_id})
                except Exception as e:
                    print(f"[Chroma Error] Storing PDF '{src.name}': {e}")
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
        article = models.Article(
            user_id=user.id,
            source_id=source.id,
            title=item['title'],
            summary=summary,
            content=item.get('content', ''),
            date=item.get('published'),
            meta_data=item.get('meta_data', {}),
            status="new"
        )
        db.add(article)
        db.commit()
        db.refresh(article)
        try:
            chroma_service.store_chunks([article.summary], {"article_id": article.id,"user_id": article.user_id})
        except Exception as e:
            print(f"[Chroma Error] Storing API article '{article.title}': {e}")
        synced_titles.append(article.title)
    source.last_synced = datetime.utcnow()
    db.commit()
    return synced_titles