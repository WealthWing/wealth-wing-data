from fastapi import HTTPException
from src.database.connect import DBSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from src.model.models import Category, Transaction


async def get_category_id_from_row(
    title: str, category: str, organization_id: str, db: DBSession, type: str = None
):
    """
    Determines the category UUID for a given transaction based on a specific logic:
    1. First, checks for an existing transaction with a similar title within the
       user's organization and returns its category ID if found.
    2. If no matching transaction is found, and no category title is provided,
       it finds or creates a default 'UNCATEGORIZED' category.
    3. If a category title is provided, it finds a matching category that is
       either global or specific to the user's organization.
    
    Args:
        title (str): The title of the transaction.
        category (str): The category title provided by the user (can be empty).
        organization_id (str): The ID of the user's organization.
        db (DBSession): The database session.

    Returns:
        Optional[uuid.UUID]: The UUID of the determined category, or None if no match is found.
    """

    transaction_result = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.user))
        .where(
            Transaction.title.ilike(f"%{title}%"),
            Transaction.user.has(organization_id=organization_id),
        )
    )
    transaction = transaction_result.scalars().first()

    if transaction:
        return transaction.category_id

    # 2. Handle uncategorized
    if not category or not category.strip():
        uncategorized_result = await db.execute(
            select(Category).where(Category.type == "UNCATEGORIZED")
        )
        uncategorized_category = uncategorized_result.scalar_one_or_none()

        if uncategorized_category:
            return uncategorized_category.uuid
        else:
            # Create the default uncategorized category if it doesn't exist
            new_uncategorized = Category(
                type="UNCATEGORIZED",
                title="Uncategorized",
                description="Default uncategorized category",
            )
            try:
                db.add(new_uncategorized)
                await db.commit()
                await db.refresh(new_uncategorized)
                return new_uncategorized.uuid
            except Exception as e:
                await db.rollback()
                raise HTTPException(
                    status_code=500, detail=f"Failed to create uncategorized category: {e}"
                )

    # 3. Find category by title and org
    found_category_result = await db.execute(
        select(Category)
        .where(
            Category.title == category.strip(),
            or_(
                Category.organization_id.is_(None),
                Category.organization_id == organization_id,
            ),
        )
    )
    found_category_result = await db.execute(
        select(Category)
        .where(
            Category.title.ilike(category.strip()),
            Category.organization_id == organization_id,
        )
        .order_by(Category.organization_id.desc()) 
        .limit(1)
    )
    found_category = found_category_result.scalar_one_or_none()

    if found_category is None:
        slugged_title = category.strip().lower().replace(" ", "-")
        new_category = Category(
            title=category.strip(),
            organization_id=organization_id,
            slug=slugged_title,
            type=type or "CUSTOM"
        )
        try:
            db.add(new_category)
            await db.commit()
            await db.refresh(new_category)
            return new_category.uuid
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=500, detail=f"Failed to create new category: {e}"
            )

    return found_category.uuid if found_category else None