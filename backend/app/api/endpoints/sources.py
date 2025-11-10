from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas, database
from app.dependencies import get_current_user
from typing import List
from pydantic import BaseModel

import logging
logger = logging.getLogger(__name__)

router = APIRouter()

class BulkImportResponse(BaseModel):
    total: int
    created: int
    skipped: int
    errors: int
    details: List[str]

# List all sources for a user
@router.get("/", response_model=list[schemas.SourceOut])
def list_sources(
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    logger.info("List sources for user_id=%s", user.id)
    return db.query(models.Source).filter(models.Source.user_id == user.id).all()

# Create a new source (e.g., RSS, API, etc)
@router.post("/", response_model=schemas.SourceOut)
def create_source(
    source: schemas.SourceCreate,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    # Optional: Check for duplicate (name + type) for this user
    existing = db.query(models.Source).filter_by(
        user_id=user.id, name=source.name, type=source.type
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Source already exists.")

    new_source = models.Source(**source.dict(), user_id=user.id)
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    return new_source

# Update a source (partial update supported via exclude_unset)
@router.put("/{source_id}", response_model=schemas.SourceOut)
def update_source(
    source_id: int,
    source: schemas.SourceUpdate,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    s = db.query(models.Source).filter(
        models.Source.id == source_id,
        models.Source.user_id == user.id
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Source not found")
    for key, value in source.dict(exclude_unset=True).items():
        setattr(s, key, value)
    db.commit()
    db.refresh(s)
    return s

# Delete a source
@router.delete("/{source_id}", response_model=dict)
def delete_source(
    source_id: int,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    s = db.query(models.Source).filter(
        models.Source.id == source_id,
        models.Source.user_id == user.id
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(s)
    db.commit()
    return {"ok": True}

# Toggle (activate/deactivate) a source
@router.patch("/{source_id}/activate", response_model=schemas.SourceOut)
def toggle_source(
    source_id: int,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    s = db.query(models.Source).filter(
        models.Source.id == source_id,
        models.Source.user_id == user.id
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Source not found")
    s.active = not s.active
    db.commit()
    db.refresh(s)
    return s

# Bulk import sources from JSON
@router.post("/bulk_import", response_model=BulkImportResponse)
def bulk_import_sources(
    sources: List[schemas.SourceCreate],
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    """
    Bulk import multiple sources at once.
    Accepts a JSON array of sources with format:
    [{"name": "Source Name", "type": "rss", "url": "https://...", "active": true}]
    """
    total = len(sources)
    created = 0
    skipped = 0
    errors = 0
    details = []

    for source in sources:
        try:
            # Check for duplicate
            existing = db.query(models.Source).filter_by(
                user_id=user.id,
                name=source.name,
                type=source.type
            ).first()

            if existing:
                skipped += 1
                details.append(f"Skipped '{source.name}' - already exists")
                continue

            # Create new source
            new_source = models.Source(**source.dict(), user_id=user.id)
            db.add(new_source)
            db.commit()
            created += 1
            details.append(f"Created '{source.name}'")

        except Exception as e:
            errors += 1
            db.rollback()
            details.append(f"Error creating '{source.name}': {str(e)}")
            logger.error(f"Bulk import error for source '{source.name}': {e}")

    return BulkImportResponse(
        total=total,
        created=created,
        skipped=skipped,
        errors=errors,
        details=details
    )

# Bulk toggle all sources on/off
@router.patch("/bulk_toggle", response_model=dict)
def bulk_toggle_sources(
    active: bool,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    """
    Toggle all sources for the current user to active or inactive.
    """
    sources = db.query(models.Source).filter(models.Source.user_id == user.id).all()
    count = 0
    for source in sources:
        source.active = active
        count += 1

    db.commit()
    return {"ok": True, "count": count, "active": active}

