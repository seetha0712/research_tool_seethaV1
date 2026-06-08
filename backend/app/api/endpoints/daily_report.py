from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app import models, database
from app.dependencies import get_current_user
from app.services import email_service
from app.api.endpoints.sync import sync_all_sources, SyncParams
from datetime import datetime
import os
import logging
import httpx

logger = logging.getLogger(__name__)

router = APIRouter()

# Environment config
DAILY_REPORT_SECRET = os.getenv("DAILY_REPORT_SECRET", "")
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")
RENDER_SERVICE_ID_APP = os.getenv("RENDER_SERVICE_ID_APP", "")
RENDER_SERVICE_ID_DB = os.getenv("RENDER_SERVICE_ID_DB", "")
SELF_SUSPEND_AFTER_REPORT = os.getenv("SELF_SUSPEND_AFTER_REPORT", "false").lower() == "true"

# Track sent article IDs (in-memory - resets on restart, but good enough for daily reports)
_sent_article_ids = set()


def _get_report_type() -> str:
    """Determine if this is morning or evening based on current IST time."""
    from datetime import timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    return "morning" if now.hour < 12 else "evening"


def _verify_secret(x_report_secret: str = Header(None)) -> bool:
    """Verify the daily report secret if configured."""
    if not DAILY_REPORT_SECRET:
        return True  # No secret configured, allow
    return x_report_secret == DAILY_REPORT_SECRET


async def _suspend_render_services():
    """Suspend Render services after report is done."""
    if not RENDER_API_KEY:
        logger.warning("RENDER_API_KEY not configured, skipping self-suspend")
        return

    headers = {
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient() as client:
        for service_id, name in [(RENDER_SERVICE_ID_APP, "app"), (RENDER_SERVICE_ID_DB, "database")]:
            if not service_id:
                continue
            try:
                resp = await client.post(
                    f"https://api.render.com/v1/services/{service_id}/suspend",
                    headers=headers
                )
                if resp.status_code in (200, 202):
                    logger.info(f"Suspended {name} service: {service_id}")
                    email_service.send_notification("stop", name, True)
                else:
                    logger.error(f"Failed to suspend {name}: {resp.status_code} - {resp.text}")
                    email_service.send_notification("stop", name, False, resp.text)
            except Exception as e:
                logger.error(f"Error suspending {name}: {e}")
                email_service.send_notification("stop", name, False, str(e))


def _run_report_pipeline(db: Session, user: models.User):
    """The actual report pipeline - runs as background task."""
    global _sent_article_ids

    try:
        logger.info("Starting daily report pipeline")

        # Step 1: Run sync
        logger.info("Step 1: Running sync...")
        from fastapi import Request
        from unittest.mock import MagicMock

        # Create a mock request for the sync function
        mock_request = MagicMock(spec=Request)
        mock_request.client = MagicMock()
        mock_request.client.host = "daily-report-cron"

        sync_params = SyncParams(limit=25, from_date="")
        try:
            sync_result = sync_all_sources(sync_params, mock_request, db, user)
            logger.info(f"Sync complete: {sync_result.get('count', 0)} articles fetched")
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            # Continue anyway - we can still report on existing articles

        # Step 2: Fetch top articles by relevance score
        logger.info("Step 2: Fetching top articles...")
        articles = (
            db.query(models.Article)
            .filter(models.Article.relevance_score.isnot(None))
            .order_by(desc(models.Article.relevance_score))
            .limit(25)
            .all()
        )

        # Step 3: Filter out already-sent articles
        unsent_articles = []
        for article in articles:
            if article.id not in _sent_article_ids:
                unsent_articles.append(article)

        top_articles = unsent_articles[:15]
        logger.info(f"Selected {len(top_articles)} unsent articles for report")

        if not top_articles:
            logger.info("No new articles to report")
            return

        # Step 4: Convert to dict format for email
        articles_data = []
        for article in top_articles:
            # Get source name
            source = db.query(models.Source).filter(models.Source.id == article.source_id).first()
            source_name = source.name if source else ""

            articles_data.append({
                "id": article.id,
                "title": article.title,
                "summary": article.summary,
                "relevance_score": article.relevance_score,
                "category": article.category,
                "source_name": source_name,
                "meta_data": article.meta_data or {},
                "link": (article.meta_data or {}).get("link", "")
            })

        # Step 5: Send email
        logger.info("Step 3: Sending daily report email...")
        report_type = _get_report_type()
        email_sent = email_service.send_daily_report(articles_data, report_type)

        if email_sent:
            logger.info("Email sent successfully")
            # Mark articles as sent
            for article in top_articles:
                _sent_article_ids.add(article.id)
            # Keep only last 500 IDs to prevent memory growth
            if len(_sent_article_ids) > 500:
                _sent_article_ids = set(list(_sent_article_ids)[-500:])
        else:
            logger.error("Failed to send email")

        # Step 6: Self-suspend if configured
        if SELF_SUSPEND_AFTER_REPORT:
            logger.info("Step 4: Self-suspending services...")
            import asyncio
            asyncio.run(_suspend_render_services())

        logger.info("Daily report pipeline complete")

    except Exception as e:
        logger.exception(f"Daily report pipeline failed: {e}")


@router.post("/daily-report/run", status_code=202)
def run_daily_report(
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
    x_report_secret: str = Header(None)
):
    """
    Trigger the daily report pipeline.

    This endpoint:
    1. Runs sync to fetch new articles
    2. Selects top 15 unsent articles by relevance score
    3. Sends email report
    4. Optionally suspends Render services (if SELF_SUSPEND_AFTER_REPORT=true)

    Returns 202 Accepted immediately - the work happens in background.
    """
    # Verify secret if configured
    if DAILY_REPORT_SECRET and x_report_secret != DAILY_REPORT_SECRET:
        raise HTTPException(status_code=401, detail="Invalid report secret")

    # Check admin
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admin users can trigger daily report")

    # Add to background tasks
    background_tasks.add_task(_run_report_pipeline, db, current_user)

    return {
        "status": "accepted",
        "message": "Daily report generation started",
        "report_type": _get_report_type()
    }


@router.get("/daily-report/status")
def get_report_status(current_user: models.User = Depends(get_current_user)):
    """Get the current status of daily report configuration."""
    return {
        "email_configured": email_service.is_email_configured(),
        "report_emails": email_service.REPORT_EMAILS,
        "self_suspend_enabled": SELF_SUSPEND_AFTER_REPORT,
        "render_api_configured": bool(RENDER_API_KEY),
        "sent_article_count": len(_sent_article_ids)
    }
