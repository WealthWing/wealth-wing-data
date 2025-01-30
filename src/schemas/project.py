from typing import Optional
from uuid import UUID 
from pydantic import BaseModel
from datetime import datetime

class ProjectBase(BaseModel):
   project_name: str

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    uuid: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        
        
class ProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    
    class Config:
        from_attributes = True        