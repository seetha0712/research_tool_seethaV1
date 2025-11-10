"""
Audit log endpoints - Admin only
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, database
from app.dependencies import get_current_user
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class AuditLogOut(BaseModel):
    id: int
    user_id: int
    username: str
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    details: Optional[dict]
    ip_address: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[AuditLogOut])
def list_audit_logs(
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
    limit: int = 100,
    offset: int = 0,
    action: Optional[str] = None,
    username: Optional[str] = None,
    resource_type: Optional[str] = None
):
    """
    Retrieve audit logs (admin only).
    Supports filtering by action, username, and resource_type.
    """
    # Check if user is admin
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    query = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc())

    # Apply filters
    if action:
        query = query.filter(models.AuditLog.action == action)
    if username:
        query = query.filter(models.AuditLog.username.ilike(f"%{username}%"))
    if resource_type:
        query = query.filter(models.AuditLog.resource_type == resource_type)

    # Paginate
    logs = query.offset(offset).limit(limit).all()
    return logs


@router.get("/stats", response_model=dict)
def get_audit_stats(
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    """
    Get audit log statistics (admin only).
    """
    # Check if user is admin
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    total_logs = db.query(models.AuditLog).count()

    # Count by action type
    from sqlalchemy import func
    actions_count = db.query(
        models.AuditLog.action,
        func.count(models.AuditLog.id).label('count')
    ).group_by(models.AuditLog.action).all()

    # Count by user
    users_count = db.query(
        models.AuditLog.username,
        func.count(models.AuditLog.id).label('count')
    ).group_by(models.AuditLog.username).all()

    return {
        "total_logs": total_logs,
        "actions": {action: count for action, count in actions_count},
        "users": {username: count for username, count in users_count}
    }
