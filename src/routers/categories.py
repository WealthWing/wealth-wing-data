import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from src.database.connect import DBSession
from src.model.models import Category, Transaction
from src.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategorySpendingResponse,
    CategoryUpdate,
)
from src.schemas.user import Perm
from src.model.param_models import CategorySpendingParams
from src.services.params import ParamsService
from src.services.query_service import QueryService, get_query_service
from src.util.types import UserPool
from src.util.user import get_current_user, has_permission

category_router = APIRouter()
logger = logging.getLogger(__name__)

# TODO - add permissions and user association to categories


@category_router.post("/create", status_code=201, response_model=CategoryResponse)
async def create_category(category_data: CategoryCreate, db: DBSession):
    new_category = Category(
        type=category_data.type,
        description=category_data.description,
        title=category_data.title,
    )
    try:
        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create category: {e}")
    return new_category


@category_router.get(
    "/categories", status_code=200, response_model=List[CategoryResponse]
)
async def get_categories(db: DBSession):

    try:
        stmt = select(Category)

        result = await db.execute(stmt)
        categories = result.scalars().all()

        if not categories:
            raise HTTPException(status_code=404, detail="No categories found")

        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {e}")


@category_router.put(
    "/update/{category_id}", status_code=200, response_model=CategoryResponse
)
async def update_category(
    category_data: CategoryUpdate,
    category_id: str,
    db: DBSession,
):
    category_stmt = select(Category).filter(Category.uuid == category_id)
    category_result = await db.execute(category_stmt)
    category_model = category_result.scalars().first()

    if not category_model:
        raise HTTPException(status_code=404, detail="Category not found")

    try:
        category_dict = category_data.model_dump(exclude_unset=True)

        for key, value in category_dict.items():
            if getattr(category_model, key) != value:
                setattr(category_model, key, value)

        db.add(category_model)
        await db.commit()
        await db.refresh(category_model)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update category: {e}")

    return category_model


@category_router.post(
    "/spending_by_category",
    status_code=200,
    response_model=list[CategorySpendingResponse],
)
async def get_spending_by_category(
    db: DBSession,
    params: CategorySpendingParams = Depends(),
    current_user: UserPool = Depends(get_current_user),
    params_service: ParamsService = Depends(ParamsService),
    query_service: QueryService = Depends(get_query_service),
):
    if not has_permission(current_user, Perm.READ):
        raise HTTPException(
            status_code=403,
            detail="User does not have permission to view category spending",
        )
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=403,
            detail="User must belong to an organization to view category spending",
        )

    try:
        expense_total = func.coalesce(func.sum(Transaction.amount), 0)
        stmt = query_service.org_filtered_query(
            model=Transaction,
            current_user=current_user,
        ).join(Category, Transaction.category_id == Category.uuid)

        stmt = params_service.apply_date_filter(
            stmt, Transaction, params.from_date, params.to_date, "date"
        ).where(Transaction.type == "expense")

        stmt = (
            stmt.with_only_columns(
                Category.uuid.label("category_id"),
                Category.title.label("category"),
                expense_total.label("expense"),
            )
            .group_by(Category.uuid, Category.title)
            .order_by(func.abs(expense_total).desc(), Category.title.asc())
        )

        result = await db.execute(stmt)
        return [
            CategorySpendingResponse(
                category_id=row.category_id,
                category=row.category,
                expense=int(row.expense or 0),
            )
            for row in result.all()
        ]
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Failed to retrieve spending by category")
        raise HTTPException(
            status_code=500,
            detail="Database error while retrieving spending by category",
        ) from exc
