from fastapi import APIRouter, Depends
from src.schemas.user import UserResponse, UserCreate
from src.model.models import User
from src.database.connect import DBSession
from typing import List
from src.util.user import get_current_user
from src.util.types import UserPool


user_router = APIRouter()


@user_router.get("/users", response_model=List[UserResponse])
async def get_users(db: DBSession):
    users = db.query(User).all()
    return users


@user_router.post("/create", status_code=201, response_model=UserResponse)
async def create_project(
    project_data: UserCreate,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    try:
        user = project_data.model_dump(exclude_unset=False)
        user["user_id"] = current_user.sub
        new_project = User(**user)

        db.add(new_project)
        await db.commit()
        await db.refresh(new_project)

        return new_project
    except Exception as e:
        db.rollback()
        raise Exception(f"error message: {str(e)}")