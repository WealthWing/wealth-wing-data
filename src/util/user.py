from fastapi import Request, HTTPException
from sqlalchemy import select

from src.schemas.user import ROLE_PERMISSIONS, Perm
from src.database.connect import DBSession
from src.model.models import User, UserRole
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

    if user:
        return UserPool(email=user.email, sub=user.uuid, organization_id=user.organization_id, role=user.role.name)

    return UserPool(email=email, sub=sub, organization_id=None, role="User_Viewer")


def has_permission(user: UserPool, perm: Perm) -> bool:
    """
    Checks if the given user has the specified permission.

    Args:
        user (UserPool): The user whose permissions are being checked.
        perm (Perm): The permission to check for.

    Returns:
        bool: True if the user has the specified permission, False otherwise.
    """
    role = user.role or UserRole.User_Viewer
    allowed = ROLE_PERMISSIONS.get(role, Perm.READ)
    return (allowed & perm) == perm