from typing import Optional, List
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
    type: Optional[str] = "N/A"
    category: Optional[str] = None
    account_name: Optional[str] = None


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


class TransactionsAllResponse(BaseModel):
    transactions: list[TransactionResponse] = []
    has_more: bool = False
    total_pages: int = 0
    total_count: int = 0

    class Config:
        from_attributes = True
   


class TransactionMonths(BaseModel):
    month: datetime
    income: int
    expense: int
    net: int


class TransactionTotals(BaseModel):
    income: int
    expense: int
    net: int
    average_monthly_spent: float


class TransactionSummaryResponse(BaseModel):
    totals: TransactionTotals
    months: List[TransactionMonths]

    class Config:
        from_attributes = True
   
