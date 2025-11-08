# app/api/endpoints/dashboard.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from app.dependencies import get_current_user
from app import database, models

router = APIRouter()

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
    """

    # Build base filters
    article_query = db.query(models.Article).filter_by(user_id=user.id)
    paid_query = db.query(models.PaidArticle).filter_by(user_id=user.id)

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