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


class CategorySpendingItemResponse(BaseModel):
    category_id: UUID
    category: str
    expense: int
    transaction_count: int


class CategorySpendingResponse(BaseModel):
    spending_by_categories: list[CategorySpendingItemResponse]
    total_spending_by_category: int
    transaction_count: int
