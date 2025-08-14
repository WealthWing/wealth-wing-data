from typing import Optional
from pydantic import BaseModel, Field
from src.model.models import AccountTypeEnum
from datetime import datetime
from uuid import UUID

class AccountBase(BaseModel):
    account_name: str = Field(..., description="Name of the account (e.g., My Checking Account, Visa Platinum Card)")
    account_type: AccountTypeEnum = Field(..., description="Type of the account (e.g., Checking, Savings, Credit Card, Investment)")
    institution: str = Field(..., description="Name of the financial institution (e.g., Chase, Bank of America")
    last_four: str = Field(..., description="Last four digits of the account number")

    class Config:
        from_attributes = True
        
class AccountCreate(AccountBase):
    """Schema for creating a new account."""
    pass

class AccountUpdate(BaseModel):
    """Schema for updating an existing account."""
    account_name: Optional[str] = Field(None, description="Name of the account (e.g., My Checking Account, Visa Platinum Card)")
    account_type: Optional[AccountTypeEnum] = Field(None, description="Type of the account (e.g., Checking, Savings, Credit Card, Investment)")
    institution: Optional[str] = Field(None, description="Name of the financial institution (e.g., Chase, Bank of America")
    last_four: Optional[str] = Field(None, description="Last four digits of the account number")

    class Config:
        from_attributes = True
        
class AccountResponse(AccountBase):
    """Schema for the response of an account."""
    uuid: UUID = Field(..., description="Unique identifier for the account")
    created_at: datetime = Field(None, description="Timestamp when the account was created")
    updated_at: datetime = Field(None, description="Timestamp when the account was last updated")

    class Config:
        from_attributes = True
        orm_mode = True             
        
class AccountOptionResponse(BaseModel):
    """Schema for account options response."""
    value: UUID = Field(..., description="Unique identifier for the account")
    label: str = Field(..., description="Name of the account (e.g., My Checking Account, Visa Platinum Card)")

    class Config:
        from_attributes = True
        orm_mode = True     