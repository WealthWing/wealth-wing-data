from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID 

class ImportFileBase(BaseModel):
    account_id: UUID
    file_name: str
    
    
class ImportFileCreate(ImportFileBase):
    """Schema for creating a new import file."""
    pass    

class ImportFileResponse(ImportFileBase):
    """Schema for the response of an import file."""
    uuid: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True     