# app/api/endpoints/dashboard.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import date, datetime, timedelta
from app.dependencies import get_current_user
from app import database, models
from typing import Optional

router = APIRouter()

# Score tier thresholds (same as sync.py)
SCORE_HIGH_THRESHOLD = 70
SCORE_MEDIUM_THRESHOLD = 40

@router.get("/metrics")
def get_dashboard_metrics(
    user=Depends(get_current_user),
    db: Session = Depends(database.get_db),
    start_date: date = Query(None),
    end_date: date = Query(None)
):
    """
    Dashboard metrics API
    - Optional start_date & end_date query params for filtering
    - Counts shortlisted & final separately for Articles & PaidArticles
    - Shows all articles to all users (admin and non-admin have same view)
    """

    # Build base filters - show all articles to everyone
    article_query = db.query(models.Article)
    paid_query = db.query(models.PaidArticle)

    if start_date:
        article_query = article_query.filter(models.Article.date >= start_date)
        paid_query = paid_query.filter(models.PaidArticle.saved_at >= start_date)

    if end_date:
        article_query = article_query.filter(models.Article.date <= end_date)
        paid_query = paid_query.filter(models.PaidArticle.saved_at <= end_date)

    # Counts
    total_articles = article_query.count()
    total_paid_articles = paid_query.count()

    shortlisted = article_query.filter(models.Article.status == "shortlisted").count()
    shortlisted_paid = paid_query.filter(models.PaidArticle.status == "shortlisted").count()

    final = article_query.filter(models.Article.status == "final").count()
    final_paid = paid_query.filter(models.PaidArticle.status == "final").count()

    # Latest articles
    latest_articles = (
        article_query.order_by(models.Article.date.desc()).limit(5).all()
    )
    latest_paid = (
        paid_query.order_by(models.PaidArticle.saved_at.desc()).limit(5).all()
    )

    def extract_url(obj):
        return (
            getattr(obj, "link", None)
            or getattr(obj, "url", None)
            or getattr(obj, "source_url", None)
            or (obj.meta_data.get("link") if getattr(obj, "meta_data", None) and isinstance(obj.meta_data, dict) else None)
            or ""
        )

    return {
        "total_articles": total_articles,
        "total_paid_articles": total_paid_articles,
        "shortlisted": shortlisted + shortlisted_paid,
        "final": final + final_paid,
        "latest_articles": [
            {
                "title": a.title,
                "source": a.source.name if a.source else "",
                "date": str(a.date) if hasattr(a, "date") else "",
                "status": a.status,
                "url": extract_url(a)
            }
            for a in latest_articles
        ],
        "latest_paid": [
            {
                "title": p.title,
                "source": p.source,
                "date": str(p.saved_at),
                "score": p.score,
                "status": p.status,
                "url": extract_url(p)
            }
            for p in latest_paid
        ]
    }


@router.get("/source-analytics")
def get_source_analytics(
    user=Depends(get_current_user),
    db: Session = Depends(database.get_db),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze")
):
    """
    Get source effectiveness analytics.
    Shows per-source metrics: total articles, avg score, high score %, top categories.
    Available to all users.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Get all sources
    sources = db.query(models.Source).all()

    source_analytics = []

    for source in sources:
        # Get articles for this source
        articles = db.query(models.Article).filter(models.Article.source_id == source.id).all()

        if not articles:
            # Include source even if no articles
            source_analytics.append({
                "source_id": source.id,
                "source_name": source.name,
                "source_type": source.type,
                "total_articles": 0,
                "avg_score": 0,
                "top_score": 0,
                "high_score_percentage": 0,
                "top_categories": [],
                "last_synced": source.last_synced.isoformat() if source.last_synced else None,
                "articles_last_30_days": 0
            })
            continue

        total_articles = len(articles)
        total_score = sum(a.relevance_score or 0 for a in articles)
        avg_score = round(total_score / total_articles, 1) if total_articles > 0 else 0

        # Top score (highest individual score)
        top_score = max((a.relevance_score or 0) for a in articles)

        # High score percentage
        high_score_count = sum(1 for a in articles if (a.relevance_score or 0) >= SCORE_HIGH_THRESHOLD)
        high_score_pct = round((high_score_count / total_articles) * 100, 1) if total_articles > 0 else 0

        # Top categories
        category_counts = {}
        for a in articles:
            cat = a.category or "Uncategorized"
            category_counts[cat] = category_counts.get(cat, 0) + 1

        top_categories = sorted(
            [{"category": k, "count": v} for k, v in category_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:3]

        # Articles in last N days
        articles_recent = sum(
            1 for a in articles
            if a.date and a.date >= cutoff_date
        )

        source_analytics.append({
            "source_id": source.id,
            "source_name": source.name,
            "source_type": source.type,
            "total_articles": total_articles,
            "avg_score": avg_score,
            "top_score": top_score,
            "high_score_percentage": high_score_pct,
            "top_categories": top_categories,
            "last_synced": source.last_synced.isoformat() if source.last_synced else None,
            "articles_last_30_days": articles_recent
        })

    # Sort by avg_score descending (most effective sources first)
    source_analytics.sort(key=lambda x: x["avg_score"], reverse=True)

    # Overall stats
    all_articles = db.query(models.Article).all()
    total_all = len(all_articles)
    overall_avg_score = round(sum(a.relevance_score or 0 for a in all_articles) / total_all, 1) if total_all > 0 else 0

    total_syncs = db.query(models.SyncHistory).count()

    return {
        "sources": source_analytics,
        "overall_stats": {
            "total_articles": total_all,
            "avg_score": overall_avg_score,
            "total_syncs": total_syncs,
            "total_sources": len(sources),
            "active_sources": sum(1 for s in sources if s.active)
        }
    }


@router.get("/sync-trends")
def get_sync_trends(
    user=Depends(get_current_user),
    db: Session = Depends(database.get_db),
    days: int = Query(30, ge=1, le=365, description="Number of days to show trends for")
):
    """
    Get sync trends over time for charting.
    Returns daily aggregated sync data.
    Available to all users.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Get sync history within date range
    sync_records = db.query(models.SyncHistory).filter(
        models.SyncHistory.sync_timestamp >= cutoff_date
    ).order_by(models.SyncHistory.sync_timestamp.asc()).all()

    # Aggregate by date
    daily_data = {}
    for record in sync_records:
        date_key = record.sync_timestamp.strftime("%Y-%m-%d")
        if date_key not in daily_data:
            daily_data[date_key] = {
                "date": date_key,
                "total_articles": 0,
                "total_syncs": 0,
                "avg_score_sum": 0,
                "score_count": 0,
                "high_count": 0,
                "medium_count": 0,
                "low_count": 0,
                "errors": 0
            }

        day = daily_data[date_key]
        day["total_articles"] += record.total_articles_fetched
        day["total_syncs"] += 1
        day["errors"] += record.total_errors

        # Aggregate scores
        scores = record.scores_breakdown or {}
        day["high_count"] += scores.get("high", 0)
        day["medium_count"] += scores.get("medium", 0)
        day["low_count"] += scores.get("low", 0)

        # For avg score calculation from sources
        for src in (record.sources_breakdown or []):
            if src.get("count", 0) > 0:
                day["avg_score_sum"] += src.get("avg_score", 0) * src.get("count", 0)
                day["score_count"] += src.get("count", 0)

    # Calculate averages and format
    trends = []
    for date_key in sorted(daily_data.keys()):
        day = daily_data[date_key]
        avg_score = round(day["avg_score_sum"] / day["score_count"], 1) if day["score_count"] > 0 else 0
        trends.append({
            "date": day["date"],
            "total_articles": day["total_articles"],
            "total_syncs": day["total_syncs"],
            "avg_score": avg_score,
            "high_count": day["high_count"],
            "medium_count": day["medium_count"],
            "low_count": day["low_count"],
            "errors": day["errors"]
        })

    return {
        "days": days,
        "trends": trends,
        "summary": {
            "total_articles": sum(t["total_articles"] for t in trends),
            "total_syncs": sum(t["total_syncs"] for t in trends),
            "total_errors": sum(t["errors"] for t in trends)
        }
    }