from fastapi import Request, HTTPException
from sqlalchemy import select

from src.database.connect import DBSession
from src.model.models import User
from .types import UserPool

""" current authenticated user from user pool """
async def get_current_user(request: Request, db: DBSession) -> UserPool:
    u = request.state.user
    if not u:
        raise HTTPException(status_code=401, detail="Not authenticated")

    email = u.get("email")
    sub = u.get("sub")
    

    if not email or not sub:
        raise HTTPException(status_code=400, detail="Invalid user data")
    
    stmt = (
        select(User)
        .where(User.uuid == sub)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    return UserPool(email=user.email, sub=user.uuid, orrganization_id=user.organization_id if user else None)
