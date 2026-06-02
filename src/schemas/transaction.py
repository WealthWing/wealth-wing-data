from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime


class TransactionBase(BaseModel):
    category_id: UUID
    account_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    title: str
    amount: int
    description: Optional[str] = None
    date: Optional[datetime] = None
    currency: Optional[str] = "USD"
    type: Optional[str] = "expense"
    subscription_candidate: bool = False
    subscription_id: Optional[UUID] = None


class TransactionCreate(TransactionBase):
    account_id: UUID


class TransactionResponse(TransactionBase):
    uuid: UUID
    user_id: UUID
    category: Optional[str] = None
    account_name: Optional[str] = None

    class Config:
        from_attributes = True
        
class SubscriptionCandidateResponse(TransactionResponse):
    frequency: Optional[str] = None

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


class SubscriptionCandidateCountResponse(BaseModel):
    count: int


class SubscriptionCandidateItem(BaseModel):
    merchant: str
    amount: float
    frequency: str
    transactions: int


class SubscriptionCandidatesResponse(BaseModel):
    has_subscription_candidates: bool
    candidates: list[SubscriptionCandidateItem] = []

class TransactionUpdateSubscriptionRequest(BaseModel):
    subscription_id: UUID 
    transaction_name: str
    
class TransactionUpdateSubscriptionResponse(BaseModel):
    updated_count: int
    subscription_id: UUID
    transaction_name: str


class TransactionByNamePeriodResponse(BaseModel):
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


class TransactionByNameMetaResponse(BaseModel):
    title: str
    period: TransactionByNamePeriodResponse
    total_transactions: int


class TransactionByNameStatsResponse(BaseModel):
    total_spent: float
    average_per_month: float
    max_single_charge: float
    min_single_charge: float
    last_transaction_date: Optional[datetime] = None
    first_transaction_date: Optional[datetime] = None


class TransactionByNameYearComparisonResponse(BaseModel):
    current_year_total: float
    previous_year_total: float
    difference: float
    percentage_change: float


class TransactionsByNameResponse(BaseModel):
    meta: TransactionByNameMetaResponse
    stats: TransactionByNameStatsResponse
    year_comparison: Optional[TransactionByNameYearComparisonResponse] = None
    transactions: list[TransactionResponse] = []

    class Config:
        from_attributes = True
