"""
Email Service for sending notifications via SMTP (Gmail).
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime
from app.core.config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
    SMTP_FROM_EMAIL, ADMIN_NOTIFICATION_EMAILS
)

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP."""

    def __init__(self):
        self.host = SMTP_HOST
        self.port = SMTP_PORT
        self.user = SMTP_USER
        self.password = SMTP_PASSWORD
        self.from_email = SMTP_FROM_EMAIL
        self.admin_emails = ADMIN_NOTIFICATION_EMAILS

    def is_configured(self) -> bool:
        """Check if SMTP is properly configured."""
        return bool(self.host and self.user and self.password)

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body_html: str,
        body_text: Optional[str] = None
    ) -> bool:
        """
        Send an email to one or more recipients.

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body_html: HTML body content
            body_text: Plain text body (optional, derived from HTML if not provided)

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("SMTP not configured, skipping email send")
            return False

        if not to_emails:
            logger.warning("No recipients specified for email")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = ", ".join(to_emails)

            # Add plain text part
            if body_text:
                part1 = MIMEText(body_text, "plain")
                msg.attach(part1)

            # Add HTML part
            part2 = MIMEText(body_html, "html")
            msg.attach(part2)

            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.from_email, to_emails, msg.as_string())

            logger.info(f"Email sent successfully to {to_emails}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    def send_infrastructure_notification(
        self,
        action: str,
        service_name: str,
        performed_by: str,
        success: bool,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Send notification to admins about infrastructure action.

        Args:
            action: 'start' or 'stop'
            service_name: Name of the affected service
            performed_by: Username who performed the action
            success: Whether the action was successful
            error_message: Error message if action failed

        Returns:
            True if notification was sent successfully
        """
        if not self.admin_emails:
            logger.warning("No admin emails configured for notifications")
            return False

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        action_past = "started" if action == "start" else "stopped"
        action_verb = "Starting" if action == "start" else "Stopping"

        if success:
            subject = f"[Research Tool] Service {action_past.capitalize()}: {service_name}"
            status_color = "#28a745" if action == "start" else "#dc3545"
            status_text = f"Successfully {action_past}"
        else:
            subject = f"[Research Tool] FAILED to {action} service: {service_name}"
            status_color = "#dc3545"
            status_text = f"Failed to {action}"

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #1a73e8; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .status {{
                    display: inline-block;
                    padding: 8px 16px;
                    background-color: {status_color};
                    color: white;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                .details {{ margin-top: 20px; }}
                .details table {{ width: 100%; border-collapse: collapse; }}
                .details td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
                .details td:first-child {{ font-weight: bold; width: 140px; }}
                .footer {{ margin-top: 20px; font-size: 12px; color: #666; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Infrastructure Notification</h2>
                </div>
                <div class="content">
                    <p><span class="status">{status_text}</span></p>

                    <div class="details">
                        <table>
                            <tr>
                                <td>Action:</td>
                                <td>{action_verb} Service</td>
                            </tr>
                            <tr>
                                <td>Service:</td>
                                <td>{service_name}</td>
                            </tr>
                            <tr>
                                <td>Performed By:</td>
                                <td>{performed_by}</td>
                            </tr>
                            <tr>
                                <td>Timestamp:</td>
                                <td>{timestamp}</td>
                            </tr>
                            {"<tr><td>Error:</td><td style='color: #dc3545;'>" + error_message + "</td></tr>" if error_message else ""}
                        </table>
                    </div>
                </div>
                <div class="footer">
                    <p>This is an automated notification from the GenAI Research Tool.</p>
                </div>
            </div>
        </body>
        </html>
        """

        body_text = f"""
Infrastructure Notification
============================

Status: {status_text}
Action: {action_verb} Service
Service: {service_name}
Performed By: {performed_by}
Timestamp: {timestamp}
{"Error: " + error_message if error_message else ""}

This is an automated notification from the GenAI Research Tool.
        """

        return self.send_email(self.admin_emails, subject, body_html, body_text)


# Singleton instance
email_service = EmailService()
