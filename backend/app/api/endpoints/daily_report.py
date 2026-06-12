from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app import models, database
from app.dependencies import get_current_user
from app.services import email_service
from app.api.endpoints.sync import sync_all_sources, SyncParams
from datetime import datetime, timezone, timedelta
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


def _get_today_ist() -> str:
    """Get today's date in IST as string."""
    return datetime.now(IST).strftime("%Y-%m-%d")


def _get_day_of_week_ist() -> int:
    """Get current day of week in IST (0=Monday, 6=Sunday)."""
    return datetime.now(IST).weekday()


def _is_monday() -> bool:
    """Check if today is Monday in IST."""
    return _get_day_of_week_ist() == 0


def _is_friday() -> bool:
    """Check if today is Friday in IST."""
    return _get_day_of_week_ist() == 4


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


def _cleanup_old_articles(db: Session):
    """
    Delete all articles to start fresh for a new week.
    Called at the start of Monday morning run.
    """
    try:
        count = db.query(models.Article).delete()
        db.commit()
        logger.info(f"Weekly cleanup: Deleted {count} articles for fresh start")
        return count
    except Exception as e:
        logger.error(f"Failed to cleanup articles: {e}")
        db.rollback()
        return 0


def _mark_articles_emailed(db: Session, article_ids: list):
    """Mark articles as emailed in database."""
    if not article_ids:
        return
    try:
        now = datetime.utcnow()
        db.query(models.Article).filter(
            models.Article.id.in_(article_ids)
        ).update({"emailed_at": now}, synchronize_session=False)
        db.commit()
        logger.info(f"Marked {len(article_ids)} articles as emailed")
    except Exception as e:
        logger.error(f"Failed to mark articles as emailed: {e}")
        db.rollback()


def _run_morning_pipeline(db: Session, user: models.User):
    """
    Morning report pipeline (Mon/Wed/Fri 8 AM IST):
    1. If Monday: Delete all articles for fresh week
    2. Run sync with 10 articles per source
    3. Email articles with score >= 60 that haven't been emailed
    4. Mark emailed articles in database
    5. Self-suspend if configured
    """
    summary = {
        "mode": "morning",
        "day_of_week": datetime.now(IST).strftime("%A"),
        "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
        "cleanup_deleted": None,
        "cleanup_label": "Monday cleanup (delete all)",
        "candidate_label": "Articles with score >= 60 (unsent)",
        "sync_performed": False,
        "sync_count": 0,
        "sync_errors": [],
        "total_in_db": 0,
        "candidates": 0,
        "already_emailed": 0,
        "to_email": 0,
        "email_sent": False,
        "self_suspend": _should_self_suspend(),
        "error": None,
    }
    try:
        logger.info("Starting MORNING report pipeline")

        # Step 1: Monday cleanup - delete all articles for fresh week
        if _is_monday():
            logger.info("Step 0: Monday cleanup - deleting all articles for fresh week")
            summary["cleanup_deleted"] = _cleanup_old_articles(db)
            logger.info(f"Deleted {summary['cleanup_deleted']} articles")

        # Step 2: Run sync
        logger.info("Step 1: Running sync (10 articles per source)...")
        from fastapi import Request
        from unittest.mock import MagicMock

        mock_request = MagicMock(spec=Request)
        mock_request.client = MagicMock()
        mock_request.client.host = "morning-report-cron"

        sync_params = SyncParams(limit=10, from_date="")
        try:
            sync_result = sync_all_sources(sync_params, mock_request, db, user)
            summary["sync_performed"] = True
            summary["sync_count"] = sync_result.get("count", 0)
            summary["sync_errors"] = sync_result.get("errors", []) or []
            logger.info(f"Sync complete: {summary['sync_count']} articles fetched")
        except Exception as e:
            summary["sync_errors"] = [{"source_name": "SYNC FAILED", "error": str(e)}]
            logger.error(f"Sync failed: {e}")

        # Step 3: Fetch articles with score >= 60, not yet emailed
        logger.info("Step 2: Fetching articles with score >= 60 (not yet emailed)...")
        summary["total_in_db"] = db.query(models.Article).count()
        summary["already_emailed"] = (
            db.query(models.Article)
            .filter(models.Article.relevance_score >= 60,
                    models.Article.emailed_at.isnot(None))
            .count()
        )
        articles = (
            db.query(models.Article)
            .filter(
                models.Article.relevance_score >= 60,
                models.Article.relevance_score.isnot(None),
                models.Article.emailed_at.is_(None)  # Not yet emailed
            )
            .order_by(desc(models.Article.relevance_score))
            .all()
        )
        summary["candidates"] = len(articles)
        summary["to_email"] = len(articles)
        logger.info(f"Found {len(articles)} articles with score >= 60 to email")

        if articles:
            # Step 4: Convert to dict format and send email
            articles_data = _convert_articles_for_email(db, articles)
            logger.info(f"Step 3: Sending morning report with {len(articles_data)} articles...")
            email_sent = email_service.send_daily_report(articles_data, "morning")
            summary["email_sent"] = email_sent

            if email_sent:
                logger.info("Email sent successfully")
                _mark_articles_emailed(db, [a.id for a in articles])
            else:
                logger.error("Failed to send email")
        else:
            logger.info("No articles to send")

        logger.info("Morning report pipeline complete")

    except Exception as e:
        summary["error"] = str(e)
        logger.exception(f"Morning report pipeline failed: {e}")
    finally:
        # ALWAYS send the run summary before any self-suspend, so there is a
        # record of what happened even after services shut down.
        try:
            email_service.send_run_summary(summary)
        except Exception as e:
            logger.error(f"Failed to send run summary: {e}")
        _do_suspend_if_enabled()


def _run_evening_pipeline(db: Session, user: models.User):
    """
    Evening report pipeline (Mon/Wed/Fri 8 PM IST):
    1. NO sync (uses articles from morning scan)
    2. Email articles with score < 60 that haven't been emailed
    3. Mark emailed articles in database
    4. If Friday: Delete all articles after sending
    5. Self-suspend if configured
    """
    summary = {
        "mode": "evening",
        "day_of_week": datetime.now(IST).strftime("%A"),
        "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
        "cleanup_deleted": None,
        "cleanup_label": "Friday cleanup (delete all)",
        "candidate_label": "Articles with score < 60 (unsent)",
        "sync_performed": False,  # evening never syncs
        "sync_count": 0,
        "sync_errors": [],
        "total_in_db": 0,
        "candidates": 0,
        "already_emailed": 0,
        "to_email": 0,
        "email_sent": False,
        "self_suspend": _should_self_suspend(),
        "error": None,
    }
    try:
        logger.info("Starting EVENING report pipeline (no sync)")

        # Step 1: Fetch articles with score < 60, not yet emailed
        logger.info("Step 1: Fetching articles with score < 60 (not yet emailed)...")
        summary["total_in_db"] = db.query(models.Article).count()
        summary["already_emailed"] = (
            db.query(models.Article)
            .filter(models.Article.relevance_score < 60,
                    models.Article.emailed_at.isnot(None))
            .count()
        )
        articles = (
            db.query(models.Article)
            .filter(
                models.Article.relevance_score < 60,
                models.Article.relevance_score.isnot(None),
                models.Article.emailed_at.is_(None)  # Not yet emailed
            )
            .order_by(desc(models.Article.relevance_score))
            .all()
        )
        summary["candidates"] = len(articles)
        summary["to_email"] = len(articles)
        logger.info(f"Found {len(articles)} articles with score < 60 to email")

        if articles:
            articles_data = _convert_articles_for_email(db, articles)
            logger.info(f"Step 2: Sending evening report with {len(articles_data)} articles...")
            email_sent = email_service.send_daily_report(articles_data, "evening")
            summary["email_sent"] = email_sent

            if email_sent:
                logger.info("Email sent successfully")
                _mark_articles_emailed(db, [a.id for a in articles])
            else:
                logger.error("Failed to send email")
        else:
            logger.info("No articles to send")

        # Friday cleanup - delete all articles after evening report
        if _is_friday():
            logger.info("Friday cleanup: Deleting all articles after evening report")
            summary["cleanup_deleted"] = _cleanup_old_articles(db)

        logger.info("Evening report pipeline complete")

    except Exception as e:
        summary["error"] = str(e)
        logger.exception(f"Evening report pipeline failed: {e}")
    finally:
        # ALWAYS send the run summary before any self-suspend.
        try:
            email_service.send_run_summary(summary)
        except Exception as e:
            logger.error(f"Failed to send run summary: {e}")
        _do_suspend_if_enabled()


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

        # Step 2: Fetch top 5 articles (regardless of emailed status for testing)
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
            "link": (article.meta_data or {}).get("link", ""),
            "key_insights": article.key_insights or [],
            "date": article.date.isoformat() if article.date else ""
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
    - If Monday: Delete all articles for fresh week
    - Run sync with 10 articles per source
    - Email articles with score >= 60 (not yet emailed)
    - Self-suspend if configured
    """
    if DAILY_REPORT_SECRET and x_report_secret != DAILY_REPORT_SECRET:
        raise HTTPException(status_code=401, detail="Invalid report secret")

    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admin users can trigger daily report")

    is_monday = _is_monday()
    background_tasks.add_task(_run_morning_pipeline, db, current_user)

    return {
        "status": "accepted",
        "mode": "morning",
        "min_score": 60,
        "articles_per_url": 10,
        "monday_cleanup": is_monday,
        "day_of_week": datetime.now(IST).strftime("%A")
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
    - NO sync (uses articles from morning scan)
    - Email articles with score < 60 (not yet emailed)
    - If Friday: Delete all articles after sending
    - Self-suspend if configured
    """
    if DAILY_REPORT_SECRET and x_report_secret != DAILY_REPORT_SECRET:
        raise HTTPException(status_code=401, detail="Invalid report secret")

    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admin users can trigger daily report")

    is_friday = _is_friday()
    background_tasks.add_task(_run_evening_pipeline, db, current_user)

    return {
        "status": "accepted",
        "mode": "evening",
        "max_score": 60,
        "sync": False,
        "friday_cleanup": is_friday,
        "day_of_week": datetime.now(IST).strftime("%A")
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
    - Sends top 5 articles (ignores emailed status)
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
def get_report_status(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get the current status of daily report configuration and article counts."""
    today = _get_today_ist()
    day_of_week = datetime.now(IST).strftime("%A")

    # Count articles by emailed status
    total_articles = db.query(models.Article).count()
    emailed_articles = db.query(models.Article).filter(
        models.Article.emailed_at.isnot(None)
    ).count()
    pending_high_score = db.query(models.Article).filter(
        models.Article.relevance_score >= 60,
        models.Article.emailed_at.is_(None)
    ).count()
    pending_low_score = db.query(models.Article).filter(
        models.Article.relevance_score < 60,
        models.Article.emailed_at.is_(None)
    ).count()

    return {
        "email_configured": email_service.is_email_configured(),
        "report_emails": email_service.REPORT_EMAILS,
        "self_suspend_enabled": _should_self_suspend(),
        "self_suspend_raw_value": os.getenv("SELF_SUSPEND_AFTER_REPORT", "not set"),
        "render_api_configured": bool(RENDER_API_KEY),
        "today_ist": today,
        "day_of_week": day_of_week,
        "is_monday": _is_monday(),
        "is_friday": _is_friday(),
        "total_articles": total_articles,
        "emailed_articles": emailed_articles,
        "pending_high_score": pending_high_score,
        "pending_low_score": pending_low_score
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


@router.post("/daily-report/cleanup", status_code=200)
def manual_cleanup(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
    x_report_secret: str = Header(None)
):
    """
    Manual cleanup endpoint - delete all articles.
    Use with caution. Admin only.
    """
    if DAILY_REPORT_SECRET and x_report_secret != DAILY_REPORT_SECRET:
        raise HTTPException(status_code=401, detail="Invalid report secret")

    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admin users can trigger cleanup")

    deleted = _cleanup_old_articles(db)

    return {
        "status": "success",
        "deleted_count": deleted,
        "message": f"Deleted {deleted} articles"
    }
