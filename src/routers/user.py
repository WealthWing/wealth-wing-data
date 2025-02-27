from fastapi import APIRouter, Depends
from src.schemas.user import UserResponse
from src.model.models import User
from src.database.connect import DBSession
from typing import List


user_router = APIRouter()


@user_router.get("/users", response_model=List[UserResponse])
async def get_users(db: DBSession):
    users = db.query(User).all()
    return users
