from fastapi import Depends, HTTPException, status
#from fastapi.security import OAuth2PasswordBearer
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app import models, database
from app.core.config import SECRET_KEY, ALGORITHM
import logging
logger = logging.getLogger(__name__)
#oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

bearer_scheme = HTTPBearer()

# Use your actual secret key and algorithm!
#SECRET_KEY = "your-secret"
#ALGORITHM = "HS256"

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

#def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials   # <-- THIS is the actual JWT string
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user