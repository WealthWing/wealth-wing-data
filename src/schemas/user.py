from decimal import Decimal
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID

from src.model.models import UserRole

class SubscriptionsAllResponse(BaseModel):
    uuid: UUID
    name: str
    cost: Optional[Decimal] = None
    class Config:
        from_orm = True   

class UserResponse(BaseModel):
    uuid: UUID
    email: str
    role: UserRole
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    subscriptions: Optional[List[SubscriptionsAllResponse]] = None
    

    class Config:
        from_attributes = True
        
class UserCreate(BaseModel):
    email: str = Field(description="The email of the user")
    role: UserRole = Field(description="The role of the user")       