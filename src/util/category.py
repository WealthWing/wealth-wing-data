from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select

from src.database.connect import DBSession
from src.model.models import Category, Transaction


async def get_category_id_from_row(
    title: str,
    category: str | None,
    organization_id: str | UUID,
    db: DBSession,
    type: str | None = None,
) -> UUID:
    """
    Resolve an organization-owned category for an imported transaction.

    Reuse a similar transaction's category when it belongs to the organization.
    Otherwise, find or create the supplied category, using Uncategorized when
    the supplied name is missing or blank.
    """
    if not organization_id:
        raise HTTPException(
            status_code=403,
            detail="An organization is required to resolve transaction categories",
        )

    transaction_result = await db.execute(
        select(Transaction.category_id)
        .join(Category, Transaction.category_id == Category.uuid)
        .where(
            Transaction.title.ilike(f"%{title}%"),
            Transaction.user.has(organization_id=organization_id),
            Category.organization_id == organization_id,
        )
        .limit(1)
    )
    category_id = transaction_result.scalar_one_or_none()

    if category_id is not None:
        return category_id

    category_title = (category or "").strip()
    is_uncategorized = not category_title
    category_title = category_title or "Uncategorized"

    found_category_result = await db.execute(
        select(Category)
        .where(
            func.lower(Category.title) == category_title.lower(),
            Category.organization_id == organization_id,
        )
        .limit(1)
    )
    found_category = found_category_result.scalar_one_or_none()

    if found_category is not None:
        return found_category.uuid

    new_category = Category(
        title=category_title,
        organization_id=organization_id,
        slug=category_title.lower().replace(" ", "-"),
        type="UNCATEGORIZED" if is_uncategorized else type or "CUSTOM",
        description="Default uncategorized category" if is_uncategorized else None,
    )
    try:
        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)
        return new_category.uuid
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to create category: {exc}"
        ) from exc
