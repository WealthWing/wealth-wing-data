from typing import Optional
from uuid import UUID 
from pydantic import BaseModel
from datetime import datetime


class ExpenseBase(BaseModel):
    user_id: UUID
    category_id: UUID
    title: str
    amount: int
    description: Optional[str]
    date: Optional[datetime]
    currency: Optional[str]
    
class ExpenseCreate(ExpenseBase):
    pass

class ExpenseUpdate(BaseModel):
    category_id: Optional[UUID]
    title: Optional[str]
    description: Optional[str]
    amount: Optional[int]
    date: Optional[datetime]
    currency: Optional[str]
    
    class Config:
        from_attributes = True    
    
    
