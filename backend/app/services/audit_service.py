"""
Audit logging service for tracking user actions
"""
import logging
from sqlalchemy.orm import Session
from app import models
from typing import Optional, Dict, Any
from fastapi import Request

logger = logging.getLogger(__name__)


def log_action(
    db: Session,
    user: models.User,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
):
    """
    Log a user action to the audit log.

    Args:
        db: Database session
        user: User performing the action
        action: Action type (e.g., "CREATE", "UPDATE", "DELETE", "SYNC", "LOGIN")
        resource_type: Type of resource (e.g., "Article", "Source", "PaidArticle")
        resource_id: ID of the affected resource
        details: Additional details about the action
        request: FastAPI request object (for IP address)
    """
    try:
        ip_address = None
        if request and hasattr(request, 'client') and request.client:
            ip_address = request.client.host

        audit_entry = models.AuditLog(
            user_id=user.id,
            username=user.username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address
        )

        db.add(audit_entry)
        db.commit()
        logger.info(f"Audit log: {user.username} performed {action} on {resource_type}#{resource_id}")

    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")
        db.rollback()
