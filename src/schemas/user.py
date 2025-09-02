from decimal import Decimal
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID
from enum import IntFlag, auto, Enum
from src.model.models import UserRole


class SubscriptionsAllResponse(BaseModel):
    uuid: UUID
    name: str
    amount: int

    class Config:
        from_orm = True


class UserResponse(BaseModel):
    uuid: UUID
    email: str
    role: UserRole
    organization_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreateRequest(BaseModel):
    email: str = Field(description="The email of the user")
    role: UserRole = Field(description="The role of the user")
    household_name: Optional[str] = Field(
        default=None,
        description="The name of the household/organization this user belongs to",
    )
    invite_token: Optional[str] = Field(
        default=None,
        description="If present, this user is joining via invite and should be linked to the inviter's organization/household",
    )


class Perm(IntFlag):
    NONE = 0
    READ = auto()
    WRITE = auto()
    DELETE = auto()
    SHARE = auto()
    MANAGE_USERS = auto()
    MANAGE_ORG = auto()
    ALL = READ | WRITE | DELETE | SHARE | MANAGE_USERS | MANAGE_ORG


ROLE_PERMISSIONS = {
    UserRole.SuperAdmin: Perm.ALL,
    UserRole.User_Admin: Perm.READ
    | Perm.WRITE
    | Perm.DELETE
    | Perm.SHARE
    | Perm.MANAGE_USERS,
    UserRole.User: Perm.READ | Perm.WRITE | Perm.SHARE,
    UserRole.User_Viewer: Perm.READ,
}
