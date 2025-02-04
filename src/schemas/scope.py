from datetime import datetime
from pydantic import BaseModel
from uuid import UUID 
from typing import Optional, List
from src.schemas.expense import ExpenseResponse


class ScopeBase(BaseModel):
    scope_name: str
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    project_id: UUID
    budget: int = 0
    
class ScopeCreate(ScopeBase):
    pass

class ScopeResponse(ScopeBase):
    uuid: UUID
    created_at: datetime
    updated_at: datetime
    
    expenses: List[ExpenseResponse] = []
    
    class Config:
        from_attributes = True
        
        
class ScopeUpdate(BaseModel):
    scope_name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[int] = None
    
    class Config:
        from_attributes = True         
        
class ScopeRequest(BaseModel):
    project_id: UUID           