from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, Request
from src.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from src.util.types import UserPool
from src.model.models import Project
from src.database.connect import DBSession
from src.util.user import get_current_user
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy import Select, and_, desc, or_


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

        return ProjectResponse(
            children=[],
            created_at=new_project.created_at,
            end_date=new_project.end_date,
            parent_id=new_project.parent_id,
            project_name=new_project.project_name,
            start_date=new_project.start_date,
            updated_at=new_project.updated_at,
            uuid=new_project.uuid,
            user_id=new_project.user_id,
        )
    except Exception as e:
        db.rollback()
        raise Exception(f"error message: {str(e)}")


@project_router.get("/all", response_model=List[ProjectResponse])
async def get_projects(
    db: DBSession, current_user: UserPool = Depends(get_current_user)
):
    stmt = (
        select(Project)
        .where(or_(Project.user_id == current_user.sub, Project.children == None))
        .options(selectinload(Project.children))
        .order_by(Project.updated_at.desc())
    )
    result = await db.execute(stmt)
    projects = result.scalars().all()

    return projects


@project_router.get(
    "/detail/{project_id}", status_code=200, response_model=ProjectResponse
)
async def get_project(
    project_id: str, db: DBSession, current_user: UserPool = Depends(get_current_user)
):
    stmt = (
        select(Project)
        .filter_by(uuid=project_id, user_id=current_user.sub)
        .options(selectinload(Project.children))
    )

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
