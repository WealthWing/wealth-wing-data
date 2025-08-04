from typing import Optional
from uuid import UUID 
from pydantic import BaseModel


class CategoryBase(BaseModel):
    title: str
    type: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    title: Optional[str] = None 
    description: Optional[str] = None


class CategoryResponse(CategoryBase):
    uuid: UUID
    class Config:
        from_attributes = True