# backend/app/api/endpoints/auth.py

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User
from app.core.security import get_password_hash, verify_password, create_access_token
from pydantic import BaseModel
from app.services import audit_service

import logging
logger = logging.getLogger(__name__)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

@router.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    user_obj = User(username=user.username, hashed_password=get_password_hash(user.password))
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return {"message": "User registered"}

@router.post("/login")
def login(user: UserLogin, request: Request, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Log successful login
    audit_service.log_action(
        db=db,
        user=db_user,
        action="LOGIN",
        details={"success": True},
        request=request
    )

    token = create_access_token(data={"sub": db_user.username, "user_id": db_user.id, "is_admin": db_user.is_admin})
    return {"access_token": token, "token_type": "bearer", "is_admin": db_user.is_admin}