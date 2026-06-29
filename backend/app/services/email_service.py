import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
REPORT_EMAILS = [e.strip() for e in os.getenv("REPORT_EMAILS", "").split(",") if e.strip()]


def is_email_configured() -> bool:
    return bool(SMTP_USER and SMTP_PASSWORD and REPORT_EMAILS)


def send_daily_report(articles: List[dict], report_type: str = "morning") -> bool:
    if not is_email_configured():
        logger.warning("Email not configured, skipping daily report")
        return False

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M IST")
    report_title = "Morning" if report_type == "morning" else "Evening"
    date_str = datetime.now().strftime("%Y-%m-%d")

    subject = f"[GenAI Research] {report_title} Digest - {date_str} ({len(articles)} articles)"

    article_rows = ""
    for idx, article in enumerate(articles):
        score = article.get("relevance_score") or article.get("score") or "N/A"
        category = article.get("category") or "Uncategorized"
        summary = article.get("summary") or article.get("description") or "No summary available"
        link = article.get("meta_data", {}).get("link") or article.get("link") or "#"
        title = article.get("title") or "Untitled"
        source_name = article.get("source_name") or ""
        article_date = article.get("date") or ""
        key_insights = article.get("key_insights") or []

        # Format date if present
        date_display = ""
        if article_date:
            try:
                from datetime import datetime
                if isinstance(article_date, str):
                    # Try parsing ISO format
                    dt = datetime.fromisoformat(article_date.replace('Z', '+00:00'))
                else:
                    dt = article_date
                date_display = dt.strftime("%b %d, %Y")
            except:
                date_display = str(article_date)[:10] if article_date else ""

        # Format key insights as bullet points
        insights_html = ""
        if key_insights and len(key_insights) > 0:
            insights_items = "".join([f'<li style="margin-bottom: 4px;">{insight}</li>' for insight in key_insights])
            insights_html = f'''
            <div style="margin-top: 12px; padding: 12px; background: #fffbeb; border-left: 3px solid #f59e0b; border-radius: 4px;">
              <div style="font-weight: 600; color: #b45309; margin-bottom: 6px; font-size: 13px;">Key Insights:</div>
              <ul style="margin: 0; padding-left: 20px; color: #78350f; font-size: 13px;">
                {insights_items}
              </ul>
            </div>
            '''

        article_rows += f"""
        <tr style="border-bottom: 1px solid #eee;">
          <td style="padding: 16px; vertical-align: top;">
            <div style="font-weight: bold; color: #1a73e8; margin-bottom: 8px;">
              {idx + 1}. <a href="{link}" style="color: #1a73e8; text-decoration: none;">{title}</a>
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; font-size: 12px;">
              <span style="background: #e8f0fe; color: #1a73e8; padding: 2px 8px; border-radius: 4px;">Score: {score}</span>
              <span style="background: #f3e8ff; color: #7c3aed; padding: 2px 8px; border-radius: 4px;">{category}</span>
              {f'<span style="background: #fef3c7; color: #d97706; padding: 2px 8px; border-radius: 4px;">{source_name}</span>' if source_name else ''}
              {f'<span style="background: #f0fdf4; color: #166534; padding: 2px 8px; border-radius: 4px;">{date_display}</span>' if date_display else ''}
            </div>
            <div style="color: #555; font-size: 14px; line-height: 1.6;">
              {summary}
            </div>
            {insights_html}
          </td>
        </tr>
        """

    high_score_count = len([a for a in articles if (a.get("relevance_score") or a.get("score") or 0) >= 8])

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background: #f5f5f5;">
      <div style="max-width: 700px; margin: 0 auto; background: white;">
        <div style="background: linear-gradient(135deg, #1a73e8, #4285f4); color: white; padding: 30px; text-align: center;">
          <h1 style="margin: 0 0 8px 0; font-size: 24px;">GenAI Research {report_title} Digest</h1>
          <p style="margin: 0; opacity: 0.9; font-size: 14px;">Top articles curated for you | {timestamp}</p>
        </div>
        <div style="display: flex; justify-content: center; gap: 30px; padding: 20px; background: #f8fafc; border-bottom: 1px solid #eee;">
          <div style="text-align: center;">
            <div style="font-size: 28px; font-weight: bold; color: #1a73e8;">{len(articles)}</div>
            <div style="font-size: 12px; color: #666; text-transform: uppercase;">Articles</div>
          </div>
          <div style="text-align: center;">
            <div style="font-size: 28px; font-weight: bold; color: #1a73e8;">{high_score_count}</div>
            <div style="font-size: 12px; color: #666; text-transform: uppercase;">High Score (8+)</div>
          </div>
        </div>
        <div style="padding: 0;">
          <table style="width: 100%; border-collapse: collapse;">
            <tbody>
              {article_rows}
            </tbody>
          </table>
        </div>
        <div style="padding: 20px; text-align: center; font-size: 12px; color: #888; background: #f8fafc;">
          <p>This is an automated daily digest from the GenAI Research Tool.</p>
          <p>Articles are ranked by AI relevance scoring.</p>
        </div>
      </div>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = ", ".join(REPORT_EMAILS)
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, REPORT_EMAILS, msg.as_string())

        logger.info(f"Daily report sent to {REPORT_EMAILS} with {len(articles)} articles")
        return True

    except Exception as e:
        logger.error(f"Failed to send daily report: {e}")
        return False


def send_run_summary(summary: dict) -> bool:
    """
    Send a diagnostic summary email describing exactly what a morning/evening
    run did: cleanup, sync results, article counts, and whether the digest was
    sent. This is ALWAYS sent (even when 0 articles or on error) and is sent
    BEFORE any self-suspend, so the user always has a record of what happened.
    """
    if not is_email_configured():
        logger.warning("Email not configured, skipping run summary")
        return False

    mode = summary.get("mode", "run")
    mode_label = mode.capitalize()
    day = summary.get("day_of_week", "")
    timestamp = summary.get("timestamp", "")

    # Overall outcome banner
    if summary.get("error"):
        banner_color, banner_text = "#dc3545", "Completed with errors"
    elif summary.get("email_sent"):
        banner_color, banner_text = "#28a745", "Digest sent"
    else:
        banner_color, banner_text = "#d97706", "Ran — no digest sent"

    subject = f"[GenAI Research] {mode_label} Run Summary - {day} ({banner_text})"

    def row(label, value, ok=None):
        if ok is True:
            icon = '<span style="color:#28a745;">&#10004;</span> '
        elif ok is False:
            icon = '<span style="color:#dc3545;">&#10008;</span> '
        else:
            icon = ''
        return f"""
        <tr>
          <td style="padding:10px 14px;border-bottom:1px solid #eee;font-weight:600;color:#333;width:45%;">{label}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #eee;color:#555;">{icon}{value}</td>
        </tr>"""

    rows = ""

    # Cleanup (Monday delete-all / Friday delete-all)
    cleanup = summary.get("cleanup_deleted")
    if cleanup is not None:
        rows += row(summary.get("cleanup_label", "Cleanup (delete all)"),
                    f"{cleanup} articles deleted", ok=True)

    # Sync
    if summary.get("sync_performed"):
        rows += row("Sync run", "Yes", ok=True)
        if summary.get("sync_from_date"):
            rows += row("Picking articles since", summary.get("sync_from_date"))
        rows += row("New articles fetched", summary.get("sync_count", 0))
        sync_errors = summary.get("sync_errors", []) or []
        if sync_errors:
            err_names = ", ".join(
                str(e.get("source_name", "?")) if isinstance(e, dict) else str(e)
                for e in sync_errors[:10]
            )
            rows += row("Sync errors", f"{len(sync_errors)} source(s): {err_names}", ok=False)
        else:
            rows += row("Sync errors", "None", ok=True)
    else:
        rows += row("Sync run", "No (evening run uses morning's articles)")

    # DB / candidate counts
    rows += row("Total articles in DB", summary.get("total_in_db", 0))
    rows += row(summary.get("candidate_label", "Articles matching score filter"),
                summary.get("candidates", 0))
    rows += row("Already emailed (skipped)", summary.get("already_emailed", 0))
    rows += row("Planned to email (new)", summary.get("to_email", 0))

    # Email outcome
    if summary.get("to_email", 0) > 0:
        rows += row("Digest email sent", "Yes" if summary.get("email_sent") else "No",
                    ok=bool(summary.get("email_sent")))
    else:
        rows += row("Digest email sent", "No new articles to send")

    # Self-suspend
    rows += row("Self-suspend after run", "Enabled" if summary.get("self_suspend") else "Disabled")

    # Error (if any)
    if summary.get("error"):
        rows += row("Error", summary.get("error"), ok=False)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:'Segoe UI',Arial,sans-serif;margin:0;padding:0;background:#f5f5f5;">
      <div style="max-width:640px;margin:0 auto;background:#fff;">
        <div style="background:{banner_color};color:#fff;padding:24px;text-align:center;">
          <h2 style="margin:0 0 6px 0;font-size:20px;">{mode_label} Run Summary</h2>
          <p style="margin:0;opacity:0.9;font-size:13px;">{day} &middot; {timestamp}</p>
          <p style="margin:10px 0 0 0;font-weight:bold;font-size:15px;">{banner_text}</p>
        </div>
        <table style="width:100%;border-collapse:collapse;font-size:14px;">
          <tbody>{rows}</tbody>
        </table>
        <div style="padding:16px;text-align:center;font-size:12px;color:#888;background:#f8fafc;">
          <p>Automated run diagnostics from the GenAI Research Tool.</p>
        </div>
      </div>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = ", ".join(REPORT_EMAILS)
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, REPORT_EMAILS, msg.as_string())

        logger.info(f"Run summary sent for {mode} run")
        return True

    except Exception as e:
        logger.error(f"Failed to send run summary: {e}")
        return False


def send_notification(action: str, service_name: str, success: bool, error_message: str = None) -> bool:
    if not is_email_configured():
        logger.warning("Email not configured, skipping notification")
        return False

    from datetime import datetime
    timestamp = datetime.now().isoformat()
    action_past = "started" if action == "start" else "stopped"
    action_verb = "Starting" if action == "start" else "Stopping"

    subject = (
        f"[Research Tool] Service {action_past}: {service_name}"
        if success
        else f"[Research Tool] FAILED to {action} service: {service_name}"
    )

    status_color = "#28a745" if success and action == "start" else "#dc3545"
    status_text = f"Successfully {action_past}" if success else f"Failed to {action}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #1a73e8; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .status {{ display: inline-block; padding: 8px 16px; background-color: {status_color}; color: white; border-radius: 4px; font-weight: bold; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h2>Infrastructure Notification</h2>
        </div>
        <div class="content">
          <p><span class="status">{status_text}</span></p>
          <table style="width: 100%; border-collapse: collapse;">
            <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold; width: 140px;">Action:</td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{action_verb} Service</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Service:</td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{service_name}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Timestamp:</td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{timestamp}</td></tr>
            {f'<tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Error:</td><td style="padding: 8px; border-bottom: 1px solid #ddd; color: #dc3545;">{error_message}</td></tr>' if error_message else ''}
          </table>
        </div>
        <div style="margin-top: 20px; font-size: 12px; color: #666; text-align: center;">
          <p>This is an automated notification from Research Tool.</p>
        </div>
      </div>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = ", ".join(REPORT_EMAILS)
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, REPORT_EMAILS, msg.as_string())

        logger.info(f"Notification sent: {action} {service_name} - {'success' if success else 'failed'}")
        return True

    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return False
