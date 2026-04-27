"""
Infrastructure Management API endpoints.
Allows admins to start/stop Render services and view status.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from app.database import SessionLocal
from app.models import User, AuditLog
from app.dependencies import get_current_user
from app.services.render_service import render_service, RenderAPIError
from app.services.email_service import email_service

logger = logging.getLogger(__name__)
router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ServiceActionRequest(BaseModel):
    service_key: str  # 'database' or 'app'


class ServiceActionResponse(BaseModel):
    success: bool
    service_key: str
    service_name: str
    action: str
    message: str
    timestamp: str


class ServiceStatus(BaseModel):
    service_key: str
    name: str
    type: str
    status: str
    suspended: bool
    error: Optional[str] = None


class InfrastructureActivity(BaseModel):
    id: int
    username: str
    action: str
    service_name: str
    timestamp: str
    success: bool


def log_infrastructure_action(
    db: Session,
    user: User,
    action: str,
    service_key: str,
    service_name: str,
    success: bool,
    request: Request,
    error: Optional[str] = None
):
    """Log infrastructure action to audit log."""
    audit_entry = AuditLog(
        user_id=user.id,
        username=user.username,
        action=f"INFRASTRUCTURE_{action.upper()}",
        resource_type="RenderService",
        details={
            "service_key": service_key,
            "service_name": service_name,
            "success": success,
            "error": error
        },
        ip_address=request.client.host if request.client else None
    )
    db.add(audit_entry)
    db.commit()


@router.get("/config")
def get_infrastructure_config(
    current_user: User = Depends(get_current_user)
):
    """Check if infrastructure management is configured."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    return {
        "render_configured": render_service.is_configured(),
        "email_configured": email_service.is_configured(),
        "services": [
            {
                "key": key,
                "name": config["name"],
                "type": config["type"],
                "configured": bool(config.get("id"))
            }
            for key, config in render_service.services.items()
        ]
    }


@router.get("/services")
async def get_services_status(
    current_user: User = Depends(get_current_user)
):
    """Get status of all Render services."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    if not render_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Render API not configured. Please set RENDER_API_KEY and service IDs."
        )

    try:
        statuses = await render_service.get_all_services_status()
        return {
            "services": statuses,
            "timestamp": datetime.utcnow().isoformat()
        }
    except RenderAPIError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))


@router.post("/services/start", response_model=ServiceActionResponse)
async def start_service(
    request_body: ServiceActionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start (resume) a Render service."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    if not render_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Render API not configured"
        )

    service_key = request_body.service_key
    service_config = render_service.services.get(service_key)

    if not service_config:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service_key}")

    service_name = service_config["name"]
    timestamp = datetime.utcnow().isoformat()

    try:
        result = await render_service.resume_service(service_key)

        # Log the action
        log_infrastructure_action(
            db=db,
            user=current_user,
            action="START",
            service_key=service_key,
            service_name=service_name,
            success=True,
            request=request
        )

        # Send email notification
        email_service.send_infrastructure_notification(
            action="start",
            service_name=service_name,
            performed_by=current_user.username,
            success=True
        )

        logger.info(f"Admin {current_user.username} started service: {service_name}")

        return ServiceActionResponse(
            success=True,
            service_key=service_key,
            service_name=service_name,
            action="start",
            message=result["message"],
            timestamp=timestamp
        )

    except RenderAPIError as e:
        # Log the failed action
        log_infrastructure_action(
            db=db,
            user=current_user,
            action="START",
            service_key=service_key,
            service_name=service_name,
            success=False,
            request=request,
            error=str(e)
        )

        # Send failure notification
        email_service.send_infrastructure_notification(
            action="start",
            service_name=service_name,
            performed_by=current_user.username,
            success=False,
            error_message=str(e)
        )

        raise HTTPException(status_code=e.status_code or 500, detail=str(e))


@router.post("/services/stop", response_model=ServiceActionResponse)
async def stop_service(
    request_body: ServiceActionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stop (suspend) a Render service."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    if not render_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Render API not configured"
        )

    service_key = request_body.service_key
    service_config = render_service.services.get(service_key)

    if not service_config:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service_key}")

    service_name = service_config["name"]
    timestamp = datetime.utcnow().isoformat()

    try:
        result = await render_service.suspend_service(service_key)

        # Log the action
        log_infrastructure_action(
            db=db,
            user=current_user,
            action="STOP",
            service_key=service_key,
            service_name=service_name,
            success=True,
            request=request
        )

        # Send email notification
        email_service.send_infrastructure_notification(
            action="stop",
            service_name=service_name,
            performed_by=current_user.username,
            success=True
        )

        logger.info(f"Admin {current_user.username} stopped service: {service_name}")

        return ServiceActionResponse(
            success=True,
            service_key=service_key,
            service_name=service_name,
            action="stop",
            message=result["message"],
            timestamp=timestamp
        )

    except RenderAPIError as e:
        # Log the failed action
        log_infrastructure_action(
            db=db,
            user=current_user,
            action="STOP",
            service_key=service_key,
            service_name=service_name,
            success=False,
            request=request,
            error=str(e)
        )

        # Send failure notification
        email_service.send_infrastructure_notification(
            action="stop",
            service_name=service_name,
            performed_by=current_user.username,
            success=False,
            error_message=str(e)
        )

        raise HTTPException(status_code=e.status_code or 500, detail=str(e))


@router.get("/activity")
def get_infrastructure_activity(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent infrastructure activity from audit logs."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Query audit logs for infrastructure actions
    logs = db.query(AuditLog).filter(
        AuditLog.action.like("INFRASTRUCTURE_%")
    ).order_by(AuditLog.timestamp.desc()).limit(limit).all()

    activities = []
    for log in logs:
        details = log.details or {}
        activities.append({
            "id": log.id,
            "username": log.username,
            "action": log.action.replace("INFRASTRUCTURE_", "").lower(),
            "service_name": details.get("service_name", "Unknown"),
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "success": details.get("success", True),
            "error": details.get("error")
        })

    return {"activities": activities}
