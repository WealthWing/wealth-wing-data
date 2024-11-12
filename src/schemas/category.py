from typing import Optional
from uuid import UUID 
from pydantic import BaseModel
from src.model.models import CategoryTypeEnum

class CategoryBase(BaseModel):
    type: str
    description: str

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    description: Optional[str]

    class Config:
        from_attributes = True    

class CategoryResponse(CategoryBase):
    uuid: UUID
    class Config:
        from_attributes = True