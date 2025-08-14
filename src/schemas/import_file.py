from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID 

class ImportFileBase(BaseModel):
    account_id: UUID
    file_name: str
    file_type: str
    file_size: int
    
    
class ImportFileCreate(ImportFileBase):
    """Schema for creating a new import file."""
    pass    

class ImportFileResponse(ImportFileBase):
    """Schema for the response of an import file."""
    uuid: UUID
    file_url: Optional[str] = None
    file_type: str
    file_size: int
    status: str  
    uploaded_at: datetime
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
        orm_mode = True
        
class ImportCompleteRequest(BaseModel):
    import_job_id: UUID
    
    
    
            