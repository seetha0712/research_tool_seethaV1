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
        truncated_summary = summary[:300] + "..." if len(summary) > 300 else summary
        link = article.get("meta_data", {}).get("link") or article.get("link") or "#"
        title = article.get("title") or "Untitled"
        source_name = article.get("source_name") or ""

        article_rows += f"""
        <tr style="border-bottom: 1px solid #eee;">
          <td style="padding: 16px; vertical-align: top;">
            <div style="font-weight: bold; color: #1a73e8; margin-bottom: 8px;">
              {idx + 1}. <a href="{link}" style="color: #1a73e8; text-decoration: none;">{title}</a>
            </div>
            <div style="display: flex; gap: 12px; margin-bottom: 8px; font-size: 12px;">
              <span style="background: #e8f0fe; color: #1a73e8; padding: 2px 8px; border-radius: 4px;">Score: {score}</span>
              <span style="background: #f3e8ff; color: #7c3aed; padding: 2px 8px; border-radius: 4px;">{category}</span>
              {f'<span style="background: #fef3c7; color: #d97706; padding: 2px 8px; border-radius: 4px;">{source_name}</span>' if source_name else ''}
            </div>
            <div style="color: #555; font-size: 14px; line-height: 1.5;">
              {truncated_summary}
            </div>
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
