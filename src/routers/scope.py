from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from src.schemas.scope import ScopeCreate, ScopeUpdate, ScopeResponse, ScopeRequest
from src.model.models import Scope
from src.database.connect import DBSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from src.model.errors import NotFoundError


scope_router = APIRouter()


@scope_router.post("/create", status_code=201, response_model=ScopeResponse)
async def create_scope(
    scope_data: ScopeCreate,
    db: DBSession,
):
    try:
        scope = scope_data.model_dump(exclude_unset=False)
        new_scope = Scope(**scope)

        db.add(new_scope)
        await db.commit()
        await db.refresh(new_scope)
        
        result = await db.execute(
            select(Scope)
            .options(selectinload(Scope.expenses))
            .filter_by(uuid=new_scope.uuid)
        )
        loaded_scope = result.scalar_one()
        return ScopeResponse.model_validate(loaded_scope)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@scope_router.get(
    "/all/{project_id}", status_code=200, response_model=list[ScopeResponse]
)
async def get_scopes(project_id: str, db: DBSession):

    try:
        stmt = (
            select(Scope)
            .options(joinedload(Scope.expenses))
            .filter(Scope.project_id == project_id)
            .order_by(Scope.created_at.desc())
        )

        scopes = await db.execute(stmt)

        result = scopes.unique().scalars().all()

        if not result:
            return []

        return result
    except NotFoundError as e:
        raise NotFoundError

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scopes: {e}")


@scope_router.put("/update/{scope_id}", status_code=200, response_model=ScopeResponse)
async def update_scope(update_data: ScopeUpdate, scope_id: str, db: DBSession):
    try:
        stmt = select(Scope).where(Scope.uuid == scope_id)
        scope = db.execute(stmt).scalars().first()

        if not scope:
            raise HTTPException(status_code=404, detail="Scope not found")

        scope_dict = update_data.model_dump(exclude_unset=True)

        for key, value in scope_dict.items():
            if getattr(scope, key) != value:
                setattr(scope, key, value)

        db.add(scope)
        db.commit()
        db.refresh(scope)
        return scope

    except Exception as e:
        db.rollback()
        raise Exception(f"error message: {str(e)}")


@scope_router.delete("/delete/{scope_id}", status_code=200)
async def delete_scope(scope_id: str, db: DBSession):
    try:
        stmt = select(Scope).where(Scope.uuid == scope_id)
        scope = db.execute(stmt).scalars().first()

        if not scope:
            raise HTTPException(status_code=404, detail="Scope not found")

        db.delete(scope)
        db.commit()
        return {"message": "Scope deleted successfully"}

    except Exception as e:
        db.rollback()
        raise Exception(f"error message: {str(e)}")
