from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, database
from app.dependencies import get_current_user
from app.services import rss_service, pdf_utils, llm_service
from app.services import embedding_service, audit_service
import os
import time
from app.services.api_service import API_SOURCE_HANDLERS
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.core.config import CATEGORY_OPTIONS
from typing import Optional, List

router = APIRouter()

import logging
logger = logging.getLogger(__name__)

# Score tier thresholds
SCORE_HIGH_THRESHOLD = 70
SCORE_MEDIUM_THRESHOLD = 40


class SyncParams(BaseModel):
    limit: int = 10
    from_date: str = ""   # ISO string or blank


def _get_score_tier(score: int) -> str:
    """Classify score into tier: high, medium, or low."""
    if score >= SCORE_HIGH_THRESHOLD:
        return "high"
    elif score >= SCORE_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def _update_source_stats(source_stats: dict, source_id: int, source_name: str, source_type: str,
                         score: int, category: str):
    """Update source statistics with a new article."""
    if source_id not in source_stats:
        source_stats[source_id] = {
            "source_id": source_id,
            "source_name": source_name,
            "source_type": source_type,
            "count": 0,
            "total_score": 0,
            "categories": {}
        }

    stats = source_stats[source_id]
    stats["count"] += 1
    stats["total_score"] += score
    stats["categories"][category] = stats["categories"].get(category, 0) + 1


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

    # Start timing
    start_time = time.time()

    limit = params.limit or 10
    from_date = params.from_date
    # Parse date string (ISO format) to datetime
    start_dt = None
    if from_date:
        try:
            start_dt = datetime.fromisoformat(from_date)
        except Exception:
            start_dt = None

    # Admin users can sync all active sources, non-admin users only their own
    if user.is_admin:
        sources = db.query(models.Source).filter(models.Source.active == True).all()
    else:
        sources = db.query(models.Source).filter(models.Source.user_id == user.id, models.Source.active == True).all()
    synced = []

    # === NEW: Tracking variables ===
    source_stats = {}  # {source_id: {source_name, source_type, count, total_score, categories: {}}}
    categories_breakdown = {}  # {category: count}
    scores_breakdown = {"high": 0, "medium": 0, "low": 0}
    sync_errors = []  # [{source_id, source_name, error}]
    sources_synced_set = set()

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

                sources_synced_set.add(src.id)

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

                    # === Track stats ===
                    _update_source_stats(source_stats, src.id, src.name, src.type, relevance_score, category)
                    categories_breakdown[category] = categories_breakdown.get(category, 0) + 1
                    scores_breakdown[_get_score_tier(relevance_score)] += 1

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

                sources_synced_set.add(src.id)

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

                # Score and categorize PDF
                try:
                    relevance_score = llm_service.score_article(summary)
                except Exception:
                    relevance_score = 0
                try:
                    category = llm_service.categorize_article(summary)
                except Exception:
                    category = "Tech Corner"

                article = models.Article(
                    user_id=user.id,
                    source_id=src.id,
                    title=src.name,
                    summary=summary,
                    content=text,
                    status="new",
                    relevance_score=relevance_score,
                    category=category,
                    embedding=embedding
                )
                db.add(article)
                db.commit()
                db.refresh(article)
                src.last_synced = datetime.utcnow()
                db.commit()
                synced.append(src.name)

                # === Track stats ===
                _update_source_stats(source_stats, src.id, src.name, src.type, relevance_score, category)
                categories_breakdown[category] = categories_breakdown.get(category, 0) + 1
                scores_breakdown[_get_score_tier(relevance_score)] += 1

            elif src.type == "api":
                try:
                    sources_synced_set.add(src.id)
                    synced_articles_data = sync_api_articles_with_stats(src, db, user)
                    synced.extend(synced_articles_data["titles"])

                    # === Track stats from API sync ===
                    for article_data in synced_articles_data["articles"]:
                        _update_source_stats(source_stats, src.id, src.name, src.type,
                                           article_data["score"], article_data["category"])
                        categories_breakdown[article_data["category"]] = categories_breakdown.get(article_data["category"], 0) + 1
                        scores_breakdown[_get_score_tier(article_data["score"])] += 1

                except Exception as e:
                    print(f"[API Error] Syncing API source '{src.name}': {e}")
                    sync_errors.append({
                        "source_id": src.id,
                        "source_name": src.name,
                        "error": str(e)
                    })

        except Exception as e:
            print(f"[Sync Error] Source '{src.name}' ({src.type}): {e}")
            sync_errors.append({
                "source_id": src.id,
                "source_name": src.name,
                "error": str(e)
            })

    # Calculate duration
    duration_seconds = round(time.time() - start_time, 2)

    # Build sources breakdown for storage
    sources_breakdown_list = []
    for source_id, stats in source_stats.items():
        avg_score = round(stats["total_score"] / stats["count"], 1) if stats["count"] > 0 else 0
        sources_breakdown_list.append({
            "source_id": stats["source_id"],
            "source_name": stats["source_name"],
            "source_type": stats["source_type"],
            "count": stats["count"],
            "avg_score": avg_score,
            "categories": stats["categories"]
        })

    # === Save to SyncHistory ===
    sync_history = models.SyncHistory(
        user_id=user.id,
        total_articles_fetched=len(synced),
        total_sources_synced=len(sources_synced_set),
        total_errors=len(sync_errors),
        duration_seconds=duration_seconds,
        sources_breakdown=sources_breakdown_list,
        categories_breakdown=categories_breakdown,
        scores_breakdown=scores_breakdown,
        errors=sync_errors,
        sync_params={"limit": limit, "from_date": from_date}
    )
    db.add(sync_history)
    db.commit()
    db.refresh(sync_history)

    # Log sync action (keep existing audit log)
    audit_service.log_action(
        db=db,
        user=user,
        action="SYNC",
        details={"count": len(synced), "limit": limit, "from_date": from_date, "sync_history_id": sync_history.id},
        request=request
    )

    # === Return enhanced response (backward compatible) ===
    return {
        # Backward compatible fields
        "synced": synced,
        "count": len(synced),
        # New detailed fields
        "sync_id": sync_history.id,
        "total_articles_fetched": len(synced),
        "duration_seconds": duration_seconds,
        "by_source": sources_breakdown_list,
        "by_category": categories_breakdown,
        "by_score_tier": {
            "high (70+)": scores_breakdown["high"],
            "medium (40-69)": scores_breakdown["medium"],
            "low (<40)": scores_breakdown["low"]
        },
        "errors": sync_errors
    }


def sync_api_articles_with_stats(source, db, user):
    """Sync API articles and return stats for tracking."""
    provider = source.provider or "tavily"
    query = source.query or source.name   # fallback if query is blank

    handler = API_SOURCE_HANDLERS.get(provider)
    if not handler:
        raise Exception(f"No handler registered for API provider: {provider}")

    try:
        articles = handler(query)
    except Exception as e:
        print(f"[API Handler Error] Calling provider '{provider}': {e}")
        return {"titles": [], "articles": []}

    synced_titles = []
    synced_articles_data = []

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

        # Score and categorize
        try:
            relevance_score = llm_service.score_article(summary)
        except Exception:
            relevance_score = 0
        try:
            category = llm_service.categorize_article(summary)
        except Exception:
            category = "Tech Corner"

        article = models.Article(
            user_id=user.id,
            source_id=source.id,
            title=item['title'],
            summary=summary,
            content=item.get('content', ''),
            date=item.get('published'),
            meta_data=item.get('meta_data', {}),
            status="new",
            relevance_score=relevance_score,
            category=category,
            embedding=embedding
        )
        db.add(article)
        db.commit()
        db.refresh(article)
        synced_titles.append(article.title)
        synced_articles_data.append({
            "score": relevance_score,
            "category": category
        })

    source.last_synced = datetime.utcnow()
    db.commit()
    return {"titles": synced_titles, "articles": synced_articles_data}


# Keep the old function for backward compatibility (in case it's imported elsewhere)
def sync_api_articles(source, db, user):
    """Legacy function - calls new function for backward compatibility."""
    result = sync_api_articles_with_stats(source, db, user)
    return result["titles"]


# ==================== Sync History Endpoints ====================

@router.get("/history")
def get_sync_history(
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Get sync history for the current user. Available to all users."""
    # Query sync history (all users can see their own history, admins see all)
    query = db.query(models.SyncHistory)

    if not user.is_admin:
        query = query.filter(models.SyncHistory.user_id == user.id)

    total = query.count()
    history = query.order_by(models.SyncHistory.sync_timestamp.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "history": [
            {
                "id": h.id,
                "user_id": h.user_id,
                "sync_timestamp": h.sync_timestamp,
                "total_articles_fetched": h.total_articles_fetched,
                "total_sources_synced": h.total_sources_synced,
                "total_errors": h.total_errors,
                "duration_seconds": h.duration_seconds,
                "sources_breakdown": h.sources_breakdown,
                "categories_breakdown": h.categories_breakdown,
                "scores_breakdown": h.scores_breakdown,
                "errors": h.errors,
                "sync_params": h.sync_params
            }
            for h in history
        ]
    }


@router.get("/history/{sync_id}")
def get_sync_history_detail(
    sync_id: int,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    """Get detailed sync history for a specific sync run."""
    sync_record = db.query(models.SyncHistory).filter(models.SyncHistory.id == sync_id).first()

    if not sync_record:
        raise HTTPException(status_code=404, detail="Sync history record not found")

    # Check permissions (admin can see all, users can see their own)
    if not user.is_admin and sync_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": sync_record.id,
        "user_id": sync_record.user_id,
        "sync_timestamp": sync_record.sync_timestamp,
        "total_articles_fetched": sync_record.total_articles_fetched,
        "total_sources_synced": sync_record.total_sources_synced,
        "total_errors": sync_record.total_errors,
        "duration_seconds": sync_record.duration_seconds,
        "sources_breakdown": sync_record.sources_breakdown,
        "categories_breakdown": sync_record.categories_breakdown,
        "scores_breakdown": sync_record.scores_breakdown,
        "errors": sync_record.errors,
        "sync_params": sync_record.sync_params
    }


@router.delete("/history/{sync_id}")
def delete_sync_history(
    sync_id: int,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    """Delete a specific sync history record. Admin only."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admin users can delete sync history")

    sync_record = db.query(models.SyncHistory).filter(models.SyncHistory.id == sync_id).first()

    if not sync_record:
        raise HTTPException(status_code=404, detail="Sync history record not found")

    db.delete(sync_record)
    db.commit()

    return {"message": "Sync history record deleted", "id": sync_id}


@router.delete("/history")
def delete_old_sync_history(
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
    days_to_keep: int = Query(360, ge=1, le=3650, description="Delete records older than this many days")
):
    """Delete sync history records older than specified days. Admin only."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admin users can delete sync history")

    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

    deleted_count = db.query(models.SyncHistory).filter(
        models.SyncHistory.sync_timestamp < cutoff_date
    ).delete()

    db.commit()

    return {
        "message": f"Deleted {deleted_count} sync history records older than {days_to_keep} days",
        "deleted_count": deleted_count,
        "cutoff_date": cutoff_date.isoformat()
    }
