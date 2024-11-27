from typing import Optional
from uuid import UUID 
from pydantic import BaseModel
from datetime import datetime


class ExpenseBase(BaseModel):
    category_id: UUID
    title: str
    amount: int
    description: Optional[str] = None
    date: Optional[datetime] = None
    currency: Optional[str] = None
    
class ExpenseCreate(ExpenseBase):
    pass

class ExpenseResponse(ExpenseBase):
    uuid: UUID
    user_id: UUID
    class Config:
        from_attributes = True

class ExpenseUpdate(BaseModel):
    category_id: Optional[UUID] = None
    title: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[int] = None
    date: Optional[datetime] = None
    currency: Optional[str] = None
    
    class Config:
        from_attributes = True    
    
    
