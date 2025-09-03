from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from src.model.models import ImportJobStatus 

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
    status: ImportJobStatus  
    uploaded_at: datetime
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
       
        
class ImportCompleteRequest(BaseModel):
    import_job_id: UUID


class ImportFileListItem(BaseModel):
    uuid: UUID
    file_name: str
    status: ImportJobStatus
    uploaded_at: datetime
    error_message: Optional[str] = None
    account_id: UUID
    account_name: str
    institution: str

    class Config:
        from_attributes = True
           
    
