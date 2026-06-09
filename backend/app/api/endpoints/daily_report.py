from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from app import models, database
from app.dependencies import get_current_user
from app.services import email_service
from app.api.endpoints.sync import sync_all_sources, SyncParams
from datetime import datetime, date, timezone, timedelta
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

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))


def _should_self_suspend() -> bool:
    """Check if self-suspend is enabled (read at runtime, not import time)."""
    value = os.getenv("SELF_SUSPEND_AFTER_REPORT", "false").lower().strip()
    return value == "true"


# Track sent article IDs by date (in-memory - resets on restart)
# Structure: {"2026-06-09": {"morning": {1, 2, 3}, "evening": {4, 5, 6}}}
_sent_articles_by_date = {}


def _get_today_ist() -> str:
    """Get today's date in IST as string."""
    return datetime.now(IST).strftime("%Y-%m-%d")


def _get_sent_ids_today(mode: str) -> set:
    """Get IDs of articles sent today for given mode (morning/evening)."""
    today = _get_today_ist()
    if today not in _sent_articles_by_date:
        _sent_articles_by_date[today] = {"morning": set(), "evening": set()}
    return _sent_articles_by_date[today].get(mode, set())


def _mark_articles_sent(article_ids: list, mode: str):
    """Mark articles as sent for today's mode."""
    today = _get_today_ist()
    if today not in _sent_articles_by_date:
        _sent_articles_by_date[today] = {"morning": set(), "evening": set()}
    _sent_articles_by_date[today][mode].update(article_ids)

    # Clean up old dates (keep only last 7 days)
    cutoff = (datetime.now(IST) - timedelta(days=7)).strftime("%Y-%m-%d")
    for old_date in list(_sent_articles_by_date.keys()):
        if old_date < cutoff:
            del _sent_articles_by_date[old_date]


def _get_report_type() -> str:
    """Determine if this is morning or evening based on current IST time."""
    now = datetime.now(IST)
    return "morning" if now.hour < 12 else "evening"


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

        # Suspend PostgreSQL database
        if RENDER_SERVICE_ID_DB:
            try:
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


def _run_morning_pipeline(db: Session, user: models.User):
    """
    Morning report pipeline:
    1. Run sync with 10 articles per source
    2. Email all articles with score >= 60
    3. Self-suspend if configured
    """
    try:
        logger.info("Starting MORNING report pipeline")

        # Step 1: Run sync
        logger.info("Step 1: Running sync (10 articles per source)...")
        from fastapi import Request
        from unittest.mock import MagicMock

        mock_request = MagicMock(spec=Request)
        mock_request.client = MagicMock()
        mock_request.client.host = "morning-report-cron"

        sync_params = SyncParams(limit=10, from_date="")
        try:
            sync_result = sync_all_sources(sync_params, mock_request, db, user)
            logger.info(f"Sync complete: {sync_result.get('count', 0)} articles fetched")
        except Exception as e:
            logger.error(f"Sync failed: {e}")

        # Step 2: Fetch articles with score >= 60, not yet sent today
        logger.info("Step 2: Fetching articles with score >= 60...")
        sent_ids = _get_sent_ids_today("morning")

        articles = (
            db.query(models.Article)
            .filter(
                models.Article.relevance_score >= 60,
                models.Article.relevance_score.isnot(None)
            )
            .order_by(desc(models.Article.relevance_score))
            .all()
        )

        # Filter out already sent
        unsent_articles = [a for a in articles if a.id not in sent_ids]
        logger.info(f"Found {len(unsent_articles)} unsent articles with score >= 60")

        if not unsent_articles:
            logger.info("No articles to send")
            _do_suspend_if_enabled()
            return

        # Step 3: Convert to dict format for email
        articles_data = _convert_articles_for_email(db, unsent_articles)

        # Step 4: Send email
        logger.info(f"Step 3: Sending morning report with {len(articles_data)} articles...")
        email_sent = email_service.send_daily_report(articles_data, "morning")

        if email_sent:
            logger.info("Email sent successfully")
            _mark_articles_sent([a.id for a in unsent_articles], "morning")
        else:
            logger.error("Failed to send email")

        # Step 5: Self-suspend
        _do_suspend_if_enabled()
        logger.info("Morning report pipeline complete")

    except Exception as e:
        logger.exception(f"Morning report pipeline failed: {e}")


def _run_evening_pipeline(db: Session, user: models.User):
    """
    Evening report pipeline:
    1. NO sync (uses articles from morning scan)
    2. Email remaining articles with score < 60
    3. Self-suspend if configured
    """
    try:
        logger.info("Starting EVENING report pipeline (no sync)")

        # Step 1: Fetch articles with score < 60, not yet sent today
        logger.info("Step 1: Fetching articles with score < 60...")
        morning_sent = _get_sent_ids_today("morning")
        evening_sent = _get_sent_ids_today("evening")
        all_sent = morning_sent.union(evening_sent)

        articles = (
            db.query(models.Article)
            .filter(
                models.Article.relevance_score < 60,
                models.Article.relevance_score.isnot(None)
            )
            .order_by(desc(models.Article.relevance_score))
            .all()
        )

        # Filter out already sent (in either morning or evening)
        unsent_articles = [a for a in articles if a.id not in all_sent]
        logger.info(f"Found {len(unsent_articles)} unsent articles with score < 60")

        if not unsent_articles:
            logger.info("No articles to send")
            _do_suspend_if_enabled()
            return

        # Step 2: Convert to dict format for email
        articles_data = _convert_articles_for_email(db, unsent_articles)

        # Step 3: Send email
        logger.info(f"Step 2: Sending evening report with {len(articles_data)} articles...")
        email_sent = email_service.send_daily_report(articles_data, "evening")

        if email_sent:
            logger.info("Email sent successfully")
            _mark_articles_sent([a.id for a in unsent_articles], "evening")
        else:
            logger.error("Failed to send email")

        # Step 4: Self-suspend
        _do_suspend_if_enabled()
        logger.info("Evening report pipeline complete")

    except Exception as e:
        logger.exception(f"Evening report pipeline failed: {e}")


def _run_test_pipeline(db: Session, user: models.User):
    """Test report pipeline: sync 5 articles, send top 5."""
    try:
        logger.info("Starting TEST report pipeline")

        # Step 1: Run sync with small limit
        logger.info("Step 1: Running sync (5 articles per source)...")
        from fastapi import Request
        from unittest.mock import MagicMock

        mock_request = MagicMock(spec=Request)
        mock_request.client = MagicMock()
        mock_request.client.host = "test-report-cron"

        sync_params = SyncParams(limit=5, from_date="")
        try:
            sync_result = sync_all_sources(sync_params, mock_request, db, user)
            logger.info(f"Sync complete: {sync_result.get('count', 0)} articles fetched")
        except Exception as e:
            logger.error(f"Sync failed: {e}")

        # Step 2: Fetch top 5 articles
        logger.info("Step 2: Fetching top 5 articles...")
        articles = (
            db.query(models.Article)
            .filter(models.Article.relevance_score.isnot(None))
            .order_by(desc(models.Article.relevance_score))
            .limit(5)
            .all()
        )

        if not articles:
            logger.info("No articles to send")
            _do_suspend_if_enabled()
            return

        # Step 3: Convert and send
        articles_data = _convert_articles_for_email(db, articles)
        logger.info(f"Step 3: Sending test report with {len(articles_data)} articles...")
        email_sent = email_service.send_daily_report(articles_data, "test")

        if email_sent:
            logger.info("Email sent successfully")
        else:
            logger.error("Failed to send email")

        # Step 4: Self-suspend
        _do_suspend_if_enabled()
        logger.info("Test report pipeline complete")

    except Exception as e:
        logger.exception(f"Test report pipeline failed: {e}")


def _convert_articles_for_email(db: Session, articles: list) -> list:
    """Convert Article models to dict format for email."""
    articles_data = []
    for article in articles:
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
    return articles_data


def _do_suspend_if_enabled():
    """Suspend services if configured."""
    should_suspend = _should_self_suspend()
    logger.info(f"SELF_SUSPEND_AFTER_REPORT={os.getenv('SELF_SUSPEND_AFTER_REPORT', 'not set')} -> should_suspend={should_suspend}")
    if should_suspend:
        logger.info("Self-suspending services...")
        import asyncio
        asyncio.run(_suspend_render_services())
    else:
        logger.info("Self-suspend disabled, leaving services running")


# ==================== ENDPOINTS ====================

@router.post("/daily-report/morning-run", status_code=202)
def run_morning_report(
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
    x_report_secret: str = Header(None)
):
    """
    Morning report (8 AM IST Mon/Wed/Fri):
    1. Run sync with 10 articles per source
    2. Email all articles with score >= 60
    3. Self-suspend if configured
    """
    if DAILY_REPORT_SECRET and x_report_secret != DAILY_REPORT_SECRET:
        raise HTTPException(status_code=401, detail="Invalid report secret")

    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admin users can trigger daily report")

    background_tasks.add_task(_run_morning_pipeline, db, current_user)

    return {
        "status": "accepted",
        "mode": "morning",
        "min_score": 60,
        "articles_per_url": 10
    }


@router.post("/daily-report/evening-run", status_code=202)
def run_evening_report(
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
    x_report_secret: str = Header(None)
):
    """
    Evening report (8 PM IST Mon/Wed/Fri):
    1. NO sync (uses articles from morning scan)
    2. Email remaining articles with score < 60
    3. Self-suspend if configured
    """
    if DAILY_REPORT_SECRET and x_report_secret != DAILY_REPORT_SECRET:
        raise HTTPException(status_code=401, detail="Invalid report secret")

    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admin users can trigger daily report")

    background_tasks.add_task(_run_evening_pipeline, db, current_user)

    return {
        "status": "accepted",
        "mode": "evening",
        "max_score": 60,
        "sync": False
    }


@router.post("/daily-report/test-run", status_code=202)
def run_test_report(
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
    x_report_secret: str = Header(None)
):
    """
    Test report (manual trigger only):
    - Syncs 5 articles per source
    - Sends top 5 articles
    """
    if DAILY_REPORT_SECRET and x_report_secret != DAILY_REPORT_SECRET:
        raise HTTPException(status_code=401, detail="Invalid report secret")

    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admin users can trigger daily report")

    background_tasks.add_task(_run_test_pipeline, db, current_user)

    return {
        "status": "accepted",
        "mode": "test",
        "article_count": 5,
        "test": True
    }


@router.get("/daily-report/status")
def get_report_status(current_user: models.User = Depends(get_current_user)):
    """Get the current status of daily report configuration."""
    today = _get_today_ist()
    morning_sent = len(_get_sent_ids_today("morning"))
    evening_sent = len(_get_sent_ids_today("evening"))

    return {
        "email_configured": email_service.is_email_configured(),
        "report_emails": email_service.REPORT_EMAILS,
        "self_suspend_enabled": _should_self_suspend(),
        "self_suspend_raw_value": os.getenv("SELF_SUSPEND_AFTER_REPORT", "not set"),
        "render_api_configured": bool(RENDER_API_KEY),
        "today_ist": today,
        "morning_sent_count": morning_sent,
        "evening_sent_count": evening_sent
    }


# Keep old endpoint for backward compatibility
@router.post("/daily-report/run", status_code=202)
def run_daily_report(
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
    x_report_secret: str = Header(None)
):
    """
    Legacy endpoint - redirects to morning or evening based on time.
    Prefer using /daily-report/morning-run or /daily-report/evening-run.
    """
    if DAILY_REPORT_SECRET and x_report_secret != DAILY_REPORT_SECRET:
        raise HTTPException(status_code=401, detail="Invalid report secret")

    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admin users can trigger daily report")

    report_type = _get_report_type()
    if report_type == "morning":
        background_tasks.add_task(_run_morning_pipeline, db, current_user)
    else:
        background_tasks.add_task(_run_evening_pipeline, db, current_user)

    return {
        "status": "accepted",
        "mode": report_type,
        "message": f"Redirected to {report_type} pipeline"
    }
