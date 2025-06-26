from fastapi import APIRouter, Depends
from src.schemas.user import UserResponse, UserCreateRequest
from src.model.models import User, Organization
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
    user_data: UserCreateRequest,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    new_org = None
    try:
        if user_data.invite_token:
            return UserResponse(
                message="Invite token is not supported in this version."
            )
        elif user_data.invite_token is None:
            household_name = user_data.household_name if user_data.household_name else f"{user_data.email} Household"
            new_org = Organization(name=household_name)
            db.add(new_org)
            await db.commit()  
            await db.refresh(new_org)
            organization_id = new_org.uuid

        user = user_data.model_dump(exclude={"invite_token", "household_name"}, exclude_unset=True)
        add_user = User(uuid=current_user.sub, organization_id=organization_id, **user)

        db.add(add_user)
        await db.commit()
        await db.refresh(add_user)
        return add_user

    except Exception as e:
        await db.rollback()
        if new_org is not None and new_org.uuid is not None:
            await db.delete(new_org)
            await db.commit()
        raise Exception(f"error message: {str(e)}")