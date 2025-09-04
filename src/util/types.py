from typing import Optional
from pydantic import BaseModel
from uuid import UUID

class UserPool(BaseModel):
    sub: UUID
    email: str
    organization_id: Optional[UUID] = None
    role: Optional[str] = None

    class Config:
        form_attributes = True