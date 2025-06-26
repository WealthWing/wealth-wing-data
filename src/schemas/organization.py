from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class OrganizationBase(BaseModel):
    name: str

    class Config:
        from_attributes = True


class OrganizationCreate(OrganizationBase):
    name: str


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None

    class Config:
        from_attributes = True


class OrganizationResponse(OrganizationBase):
    uuid: UUID
