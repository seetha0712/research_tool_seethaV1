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


def _should_self_suspend() -> bool:
    """Check if self-suspend is enabled (read at runtime, not import time)."""
    value = os.getenv("SELF_SUSPEND_AFTER_REPORT", "false").lower().strip()
    return value == "true"

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
        # Suspend web service
        if RENDER_SERVICE_ID_APP:
            try:
                resp = await client.post(
                    f"https://api.render.com/v1/services/{RENDER_SERVICE_ID_APP}/suspend",
                    headers=headers
                )
                if resp.status_code in (200, 202):
                    logger.info(f"Suspended app service: {RENDER_SERVICE_ID_APP}")
                    email_service.send_notification("stop", "app", True)
                else:
                    logger.error(f"Failed to suspend app: {resp.status_code} - {resp.text}")
                    email_service.send_notification("stop", "app", False, resp.text)
            except Exception as e:
                logger.error(f"Error suspending app: {e}")
                email_service.send_notification("stop", "app", False, str(e))

        # Suspend PostgreSQL database (uses different API endpoint)
        if RENDER_SERVICE_ID_DB:
            try:
                # PostgreSQL uses /v1/postgres/{id}/suspend, not /v1/services/
                resp = await client.post(
                    f"https://api.render.com/v1/postgres/{RENDER_SERVICE_ID_DB}/suspend",
                    headers=headers
                )
                if resp.status_code in (200, 202):
                    logger.info(f"Suspended database: {RENDER_SERVICE_ID_DB}")
                    email_service.send_notification("stop", "database", True)
                else:
                    logger.error(f"Failed to suspend database: {resp.status_code} - {resp.text}")
                    email_service.send_notification("stop", "database", False, resp.text)
            except Exception as e:
                logger.error(f"Error suspending database: {e}")
                email_service.send_notification("stop", "database", False, str(e))


def _run_report_pipeline(db: Session, user: models.User, article_count: int = 15, sync_limit: int = 25, is_test: bool = False):
    """The actual report pipeline - runs as background task."""
    global _sent_article_ids

    try:
        report_label = "TEST " if is_test else ""
        logger.info(f"Starting {report_label}daily report pipeline (articles: {article_count}, sync_limit: {sync_limit})")

        # Step 1: Run sync
        logger.info("Step 1: Running sync...")
        from fastapi import Request
        from unittest.mock import MagicMock

        # Create a mock request for the sync function
        mock_request = MagicMock(spec=Request)
        mock_request.client = MagicMock()
        mock_request.client.host = "daily-report-cron"

        sync_params = SyncParams(limit=sync_limit, from_date="")
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
            .limit(sync_limit)
            .all()
        )

        # Step 3: Filter out already-sent articles
        unsent_articles = []
        for article in articles:
            if article.id not in _sent_article_ids:
                unsent_articles.append(article)

        top_articles = unsent_articles[:article_count]
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
        should_suspend = _should_self_suspend()
        logger.info(f"SELF_SUSPEND_AFTER_REPORT={os.getenv('SELF_SUSPEND_AFTER_REPORT', 'not set')} -> should_suspend={should_suspend}")
        if should_suspend:
            logger.info("Step 4: Self-suspending services...")
            import asyncio
            asyncio.run(_suspend_render_services())
        else:
            logger.info("Self-suspend disabled, leaving services running")

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
    background_tasks.add_task(_run_report_pipeline, db, current_user, article_count=15, sync_limit=25, is_test=False)

    return {
        "status": "accepted",
        "message": "Daily report generation started",
        "report_type": _get_report_type(),
        "article_count": 15
    }


@router.post("/daily-report/test-run", status_code=202)
def run_test_report(
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
    x_report_secret: str = Header(None)
):
    """
    Trigger a TEST daily report pipeline with only 5 articles.

    Same as /daily-report/run but with reduced article count for testing.
    Returns 202 Accepted immediately - the work happens in background.
    """
    # Verify secret if configured
    if DAILY_REPORT_SECRET and x_report_secret != DAILY_REPORT_SECRET:
        raise HTTPException(status_code=401, detail="Invalid report secret")

    # Check admin
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admin users can trigger daily report")

    # Add to background tasks with test parameters
    background_tasks.add_task(_run_report_pipeline, db, current_user, article_count=5, sync_limit=10, is_test=True)

    return {
        "status": "accepted",
        "message": "TEST daily report generation started",
        "report_type": _get_report_type(),
        "article_count": 5,
        "test": True
    }


@router.get("/daily-report/status")
def get_report_status(current_user: models.User = Depends(get_current_user)):
    """Get the current status of daily report configuration."""
    return {
        "email_configured": email_service.is_email_configured(),
        "report_emails": email_service.REPORT_EMAILS,
        "self_suspend_enabled": _should_self_suspend(),
        "self_suspend_raw_value": os.getenv("SELF_SUSPEND_AFTER_REPORT", "not set"),
        "render_api_configured": bool(RENDER_API_KEY),
        "sent_article_count": len(_sent_article_ids)
    }
