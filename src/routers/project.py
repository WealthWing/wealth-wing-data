from fastapi import APIRouter, Depends, HTTPException, Request
from src.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from src.util.types import UserPool
from src.model.models import Project
from src.database.connect import session
from src.util.user import get_current_user


project_router = APIRouter()

@project_router.put("/create", status_code=201, response_model=ProjectResponse)
async def create_project(project_data: ProjectCreate, db: session, current_user: UserPool = Depends(get_current_user)):
    try:
        new_project = Project(project_name=project_data.project_name, user_id=current_user.sub)
        
        return {"message": "Project created successfully!"} 
    except Exception as e:
        db.rollback()
        raise Exception(f"error message: {str(e)}")
            
    