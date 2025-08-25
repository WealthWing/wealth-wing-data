from src.database.connect import DBSession
from sqlalchemy import select, or_
from src.model.models import Category, Transaction

UNCATEGORIZED_CATEGORY_ID = "1d49a1bb-95ed-4848-9d67-7670cd111f39"


async def get_category_id_from_row(
    title: str, category: str, organization_id: str, db: DBSession
):

    transaction_result = await db.execute(
        select(Transaction).where(
            Transaction.title.ilike(f"%{title}%"),
            or_(Transaction.user.has(organization_id=organization_id)),
        )
    )
    transaction = transaction_result.scalars().first()
    if transaction:
        return transaction.category_id

    if not category or not category.strip():
        return UNCATEGORIZED_CATEGORY_ID

    categories = await db.execute(
        select(Category).where(
            Category.title == category.strip(),
            or_(
                Category.organization_id == None,
                Category.organization_id == organization_id,
            ),
        )
    )
    category = categories.scalar_one_or_none()

    return category.uuid if category else UNCATEGORIZED_CATEGORY_ID
