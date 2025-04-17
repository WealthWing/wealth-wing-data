from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, Request
from src.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from src.util.types import UserPool
from src.model.models import Project
from src.database.connect import DBSession
from src.util.user import get_current_user
from sqlalchemy import select


project_router = APIRouter()


@project_router.post("/create", status_code=201, response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    try:
        project = project_data.model_dump(exclude_unset=False)
        project["user_id"] = current_user.sub
        new_project = Project(**project)

        db.add(new_project)
        await db.commit()
        await db.refresh(new_project)

        return new_project
    except Exception as e:
        db.rollback()
        raise Exception(f"error message: {str(e)}")


@project_router.get("/all", status_code=200, response_model=List[ProjectResponse])
async def get_projects(
    db: DBSession, current_user: UserPool = Depends(get_current_user)
):
    stmt = select(Project).where(Project.user_id == current_user.sub)
    result = await db.execute(stmt)
    projects = result.scalars().all()

    if not projects:
        return HTTPException(status_code=404, detail="No projects found")

    return projects


@project_router.get(
    "/detail/{project_id}", status_code=200, response_model=ProjectResponse
)
async def get_projecy(
    project_id: str, db: DBSession, current_user: UserPool = Depends(get_current_user)
):
    stmt = select(Project).filter_by(uuid=project_id, user_id=current_user.sub)

    result = await db.execute(stmt)

    project = result.scalars().first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@project_router.put(
    "/update/{project_id}", status_code=200, response_model=ProjectResponse
)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    try:
        stmt = select(Project).filter_by(uuid=project_id, user_id=current_user.sub)

        project = await db.execute(stmt)

        result = project.scalars().first()

        if not result:
            raise HTTPException(status_code=404, detail="Project not found")

        project_dict = project_data.model_dump(exclude_unset=True)

        for key, value in project_dict.items():
            if getattr(result, key) != value:
                setattr(result, key, value)

        db.add(result)
        await db.commit()
        await db.refresh(result)

        return result
    except Exception as e:
        raise Exception(f"error message: {str(e)}")


@project_router.delete("/delete/{project_id}", status_code=200)
async def delete_project(
    project_id: str,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    try:
        stmt = select(Project).filter_by(uuid=project_id, user_id=current_user.sub)

        project = await db.execute(stmt)
        result = project.scalars().first()

        if not result:
            raise HTTPException(status_code=404, detail="Project not found")

        await db.delete(result)
        await db.commit()

        return {"message": "Project deleted successfully!"}
    except Exception as e:
        raise Exception(f"error message: {str(e)}")
