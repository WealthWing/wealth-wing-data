from typing import Optional
from uuid import UUID 
from pydantic import BaseModel
from datetime import datetime


class TransactionBase(BaseModel):
    category_id: UUID
    title: str
    amount: int
    description: Optional[str] = None
    date: Optional[datetime] = None
    currency: Optional[str] = None
    
class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    uuid: UUID
    user_id: UUID
    class Config:
        from_attributes = True

class TransactionUpdate(BaseModel):
    category_id: Optional[UUID] = None
    title: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[int] = None
    date: Optional[datetime] = None
    currency: Optional[str] = None
    
    class Config:
        from_attributes = True    
    
    
