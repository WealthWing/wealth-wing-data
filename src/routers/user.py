from fastapi import APIRouter
from src.schemas.user import UserResponse
from src.model.models import User
from src.database.connect import db_session
from typing import List

user_router = APIRouter()

@user_router.get("/users", response_model=List[UserResponse])
async def get_users(db: db_session):
    users = db.query(User).all()
    return users