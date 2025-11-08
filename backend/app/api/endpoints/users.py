from fastapi import APIRouter

router = APIRouter()
import logging
logger = logging.getLogger(__name__)

@router.get("/")
async def get_users():
    return {"message": "User list placeholder"}