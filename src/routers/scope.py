from fastapi import APIRouter, HTTPException
from src.schemas.scope import ScopeCreate, ScopeUpdate, ScopeResponse, ScopeRequest
from src.model.models import Scope
from src.database.connect import session
from sqlalchemy import select
from sqlalchemy.orm import joinedload


scope_router = APIRouter()


@scope_router.post("/create", status_code=201, response_model=ScopeResponse)
async def create_scope(
    scope_data: ScopeCreate,
    db: session,
):
    try:
        scope = scope_data.model_dump(exclude_unset=False)
        new_scope = Scope(**scope)

        db.add(new_scope)
        db.commit()
        db.refresh(new_scope)
        return new_scope
    except Exception as e:
        db.rollback()
        raise Exception(f"error message: {str(e)}")


@scope_router.get("/all", status_code=200, response_model=list[ScopeResponse])
async def get_scopes(scope_request: ScopeRequest, db: session):

    try:
        stmt = (
            select(Scope)
            .options(joinedload(Scope.expenses))
            .filter(Scope.project_id == scope_request.project_id)
            .order_by(Scope.created_at.desc())
        )

        scopes = db.execute(stmt).scalars().unique().all()

        if not scopes:
            raise HTTPException(status_code=404, detail="No scopes found")

        return scopes

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scopes: {e}")


@scope_router.put("/update/{scope_id}", status_code=200, response_model=ScopeResponse)
async def update_scope(update_data: ScopeUpdate, scope_id: str, db: session):
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
async def delete_scope(scope_id: str, db: session):
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
