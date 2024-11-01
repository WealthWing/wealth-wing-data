from fastapi import Request, HTTPException
from .types import UserPool

""" current authenticated user from user pool """
async def get_current_user(request: Request):
    u = request.state.user
    if not u:
        raise HTTPException(status_code=401, detail="Not authenticated")

    email = u.get("email")
    sub = u.get("sub")

    if not email or not sub:
        raise HTTPException(status_code=400, detail="Invalid user data")

    return UserPool(email=email, sub=sub)
