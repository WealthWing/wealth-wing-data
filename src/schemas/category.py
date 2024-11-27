from typing import Optional
from uuid import UUID 
from pydantic import BaseModel
from src.model.models import CategoryTypeEnum

class CategoryBase(BaseModel):
    title: str
    type: CategoryTypeEnum
    description: str

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class CategoryResponse(CategoryBase):
    uuid: UUID
    class Config:
        from_attributes = True