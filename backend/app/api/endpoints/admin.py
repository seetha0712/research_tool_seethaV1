# backend/app/api/endpoints/admin.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, Source, Article, PaidArticle, File, Note
from app.dependencies import get_current_user
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Admin users list
ADMIN_USERS = ["seetha1"]

class DeleteRequest(BaseModel):
    table: str  # "users", "sources", "articles", "paid_articles", "files", "notes"
    ids: list[int]  # List of IDs to delete

@router.get("/stats")
def get_admin_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get database statistics for admin dashboard"""
    if current_user.username not in ADMIN_USERS:
        raise HTTPException(status_code=403, detail="Admin access required")

    stats = {
        "users": db.query(User).count(),
        "sources": db.query(Source).count(),
        "articles": db.query(Article).count(),
        "paid_articles": db.query(PaidArticle).count(),
        "files": db.query(File).count(),
        "notes": db.query(Note).count(),
    }

    return stats

@router.get("/users")
def get_all_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all users for admin"""
    if current_user.username not in ADMIN_USERS:
        raise HTTPException(status_code=403, detail="Admin access required")

    users = db.query(User).all()
    return [{"id": u.id, "username": u.username} for u in users]

@router.delete("/delete")
def delete_data(
    request: DeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete data from specified table"""
    if current_user.username not in ADMIN_USERS:
        raise HTTPException(status_code=403, detail="Admin access required")

    model_map = {
        "users": User,
        "sources": Source,
        "articles": Article,
        "paid_articles": PaidArticle,
        "files": File,
        "notes": Note,
    }

    if request.table not in model_map:
        raise HTTPException(status_code=400, detail=f"Invalid table: {request.table}")

    model = model_map[request.table]

    try:
        deleted_count = 0
        for item_id in request.ids:
            item = db.query(model).filter(model.id == item_id).first()
            if item:
                db.delete(item)
                deleted_count += 1

        db.commit()
        logger.info(f"Admin {current_user.username} deleted {deleted_count} items from {request.table}")

        return {
            "success": True,
            "deleted_count": deleted_count,
            "table": request.table
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting from {request.table}: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

@router.get("/table/{table_name}")
def get_table_data(
    table_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all data from a specific table"""
    if current_user.username not in ADMIN_USERS:
        raise HTTPException(status_code=403, detail="Admin access required")

    model_map = {
        "users": User,
        "sources": Source,
        "articles": Article,
        "paid_articles": PaidArticle,
        "files": File,
        "notes": Note,
    }

    if table_name not in model_map:
        raise HTTPException(status_code=400, detail=f"Invalid table: {table_name}")

    model = model_map[table_name]
    items = db.query(model).all()

    # Convert to dictionaries
    result = []
    for item in items:
        item_dict = {c.name: getattr(item, c.name) for c in item.__table__.columns}
        result.append(item_dict)

    return result
