from fastapi import APIRouter, Depends, UploadFile, File as FastAPIFile, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas, database
from app.dependencies import get_current_user
import hashlib
import os
from datetime import datetime

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

import logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=schemas.FileOut)
async def upload_file(
    uploaded_file: UploadFile = FastAPIFile(...),
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    # Read file contents
    contents = await uploaded_file.read()
    file_hash = hashlib.sha256(contents).hexdigest()

    # Check for duplicates
    existing = db.query(models.File).filter(models.File.hash == file_hash, models.File.user_id == user.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="File already uploaded")

    # Save to disk with unique name (hash as filename)
    saved_filename = f"{file_hash}_{uploaded_file.filename}"
    file_path = os.path.join(UPLOAD_DIR, saved_filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    # Record in DB
    db_file = models.File(
        user_id=user.id,
        filename=saved_filename,
        hash=file_hash,
        upload_date=datetime.utcnow(),
        status="uploaded"
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    # Create the Source
    db_source = models.Source(
        user_id=user.id,
        name=uploaded_file.filename,
        type="pdf",
        file_id=db_file.id,
        active=True,
        created_at=datetime.utcnow(),
    )
    db.add(db_source)
    db.commit()
    db.refresh(db_source)

    return db_file

@router.get("/", response_model=list[schemas.FileOut])
def list_files(
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    return db.query(models.File).filter(models.File.user_id == user.id).all()