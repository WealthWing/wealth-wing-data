from fastapi import APIRouter, Depends
from sqlalchemy import func, case, select
from src.model.param_models import TransactionsParams
from src.services.params import ParamsService
from src.model.models import Transaction, Account, AccountTypeEnum
from src.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionSummaryResponse,
    TransactionsAllResponse,
)
from src.database.connect import DBSession
from src.util.types import UserPool
from src.util.user import get_current_user
from src.util.transaction import create_transaction_in_db
from src.services.query_service import get_query_service, QueryService

transaction_router = APIRouter()


@transaction_router.post("/create", status_code=200, response_model=TransactionResponse)
async def create_transaction(
    transaction_data: TransactionCreate,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    return await create_transaction_in_db(transaction_data, db, current_user.sub)


@transaction_router.get("/all", status_code=200, response_model=TransactionsAllResponse)
async def get_transactions(
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
    params: TransactionsParams = Depends(),
    params_service: ParamsService = Depends(ParamsService),
    query_service: QueryService = Depends(get_query_service),
):
    base_stmt = query_service.org_filtered_query(
        model=Transaction,
        account_attr="account",
        category_attr="category",
        current_user=current_user,
    )

    filtered_stmt = params_service.process_query(
        stmt=base_stmt,
        params=params,
        model=Transaction,
        search_fields=["title", "type"],
    )

    transactions = await db.execute(filtered_stmt)
    result = transactions.scalars().all()

    if not result:
        return []

    countable = filtered_stmt.limit(None).offset(None).order_by(None)
    count_subq = countable.with_only_columns(Transaction.uuid).subquery()
    total = (
        await db.execute(select(func.count()).select_from(count_subq))
    ).scalar_one()

    page = getattr(params, "page", None)
    page_size = getattr(params, "page_size", None)
    if page and page_size:
        total_pages = (total + page_size - 1) // page_size
        has_more = (page * page_size) < total
    else:
        total_pages = None
        has_more = None

    transactions = [
        TransactionResponse(
            account_name=(t.account.account_name if t.account else None),
            category=(t.category.title if t.category else None),
            uuid=t.uuid,
            title=t.title,
            amount=t.amount,
            description=t.description,
            date=t.date,
            currency=t.currency,
            type=t.type,
            category_id=t.category_id,
            user_id=t.user_id,
        )
        for t in result
    ]

    return TransactionsAllResponse(
        transactions=transactions,
        total_count=total,
        has_more=has_more,
        total_pages=total_pages,
    )


@transaction_router.get("/summary", status_code=200, response_model=TransactionSummaryResponse)
async def get_transaction_summary(
    db: DBSession,
    params: TransactionsParams = Depends(),
    current_user: UserPool = Depends(get_current_user),
    params_service: ParamsService = Depends(ParamsService),
    query_service: QueryService = Depends(get_query_service),
):
    """
    Endpoint to retrieve a summary of transactions for the current user.

    This endpoint returns both overall totals and monthly breakdowns of income and expenses
    for transactions filtered by the provided parameters. Only transactions associated with
    checking accounts are considered.

    Args:
        db (DBSession): Database session dependency.
        params (TransactionsParams): Query parameters for filtering transactions.
        current_user (UserPool): The currently authenticated user.
        params_service (ParamsService): Service for processing query parameters.
        query_service (QueryService): Service for building filtered queries.

    Returns:
        dict: A dictionary containing:
            - "totals": Overall totals for money in, money out, and net amount.
            - "months": List of monthly summaries, each with month, income, expense, and net.

    Raises:
        HTTPException: If authentication fails or database errors occur.
    """

    base_stmt = query_service.org_filtered_query(
        model=Transaction, current_user=current_user
    )

    filtered_stmt = params_service.process_query(
        stmt=base_stmt,
        params=params,
        model=Transaction,
        date_field="date",
        search_fields=["title", "type"],
    )
   
    subq = (
        filtered_stmt.join(Account, Transaction.account_id == Account.uuid)
        .where(Account.account_type == AccountTypeEnum.CHECKING)
        .with_only_columns(
            Transaction.date,
            Transaction.type,
            Transaction.amount,
        )
        .subquery()
    )

    # ------- Totals (In / Out) -------
    totals_stmt = select(
        func.coalesce(
            func.sum(case((subq.c.type == "income", subq.c.amount), else_=0)), 0
        ).label("total_in"),
        func.coalesce(
            func.sum(case((subq.c.type == "expense", subq.c.amount), else_=0)), 0
        ).label("total_out"),
    )

    # ------- Monthly buckets -------
    month_col = func.date_trunc("month", subq.c.date).label("month")
    months_stmt = (
        select(
            month_col,
            func.coalesce(
                func.sum(case((subq.c.type == "income", subq.c.amount), else_=0)), 0
            ).label("income"),
            func.coalesce(
                func.sum(case((subq.c.type == "expense", subq.c.amount), else_=0)), 0
            ).label("expense"),
        )
        .group_by(month_col)
        .order_by(month_col)
    )

    totals_res = await db.execute(totals_stmt)
    months_res = await db.execute(months_stmt)

    totals = totals_res.one()
    total_in = int(totals.total_in or 0)
    total_out = int(totals.total_out or 0)

    months = []
    for m, income, expense in months_res.all():
        income = int(income or 0)
        expense = int(expense or 0)

        months.append(
            {
                "month": (m.date() if hasattr(m, "date") else m),
                "income": income,
                "expense": expense,
                "net": income - abs(expense),
            }
        )

    return {
        "totals": {
            "income": total_in,
            "expense": total_out,
            "net": total_in - abs(total_out),
            "average_monthly_spent": total_out // len(months) if months else 0,
        },
        "months": months,
    }
