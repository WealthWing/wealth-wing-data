from fastapi import APIRouter, Depends
from src.schemas.user import UserResponse, UserCreate
from src.model.models import User
from src.database.connect import DBSession
from typing import List
from src.util.user import get_current_user
from src.util.types import UserPool
from sqlalchemy import select

user_router = APIRouter()


@user_router.get("/users", response_model=List[UserResponse])
async def get_users(db: DBSession):
    stmt = select(User)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    if not users:
        return []
    return users


@user_router.post("/create", status_code=201)
async def create_project(
    user_data: UserCreate,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    try:
        user = user_data.model_dump(exclude_unset=False)
        user["uuid"] = current_user.sub
        add_user = User(**user)

        db.add(add_user)
        await db.commit()
        await db.refresh(add_user)

        return add_user
    except Exception as e:
        db.rollback()
        raise Exception(f"error message: {str(e)}")