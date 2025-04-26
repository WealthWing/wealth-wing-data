from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime


class ProjectBase(BaseModel):
    project_name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    uuid: UUID
    created_at: datetime
    updated_at: datetime
    total_spent: Optional[float] = 0

    class Config:
        from_attributes = True


class ProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    class Config:
        from_attributes = True
