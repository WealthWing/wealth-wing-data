from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.schemas.user import UserResponse

class SubscriptionBase(BaseModel):
    user_id: UUID = None
    category_id: Optional[UUID]
    name: str
    cost: Optional[Decimal] = None
    currency: Optional[str] = None
    billing_frequency: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None
    auto_renew: Optional[bool] = True
    status: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    cancellation_date: Optional[datetime] = None
    trial_period: Optional[bool] = False
    trial_end_date: Optional[datetime] = None
    total_amount_spent: Optional[Decimal] = None
    contract_length: Optional[str] = None
    contract_end_date: Optional[datetime] = None
    usage_limits: Optional[str] = None
    support_contact: Optional[str] = None
    website_url: Optional[str] = None
    
    
class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    cost: Optional[Decimal] = None
    currency: Optional[str] = None
    billing_frequency: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None
    auto_renew: Optional[bool] = None
    status: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    cancellation_date: Optional[datetime] = None
    trial_period: Optional[bool] = None
    trial_end_date: Optional[datetime] = None
    total_amount_spent: Optional[Decimal] = None
    contract_length: Optional[str] = None
    contract_end_date: Optional[datetime] = None
    usage_limits: Optional[str] = None
    support_contact: Optional[str] = None
    website_url: Optional[str] = None

    class Config:
        from_attributes = True 
        
        
class SubscriptionInDBBase(SubscriptionBase):
    uuid: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SubscriptionResponse(SubscriptionInDBBase):
    user: UserResponse     

class SubscriptionsAllResponse(BaseModel):
    uuid: UUID
    name: str
    cost: Optional[Decimal] = None
    class Config:
        from_orm = True    
    
 