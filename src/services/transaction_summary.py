from datetime import datetime, time, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import case, func

from src.database.connect import DBSession
from src.model.models import Account, Transaction
from src.schemas.transaction import (
    TransactionSummaryRequest,
    TransactionSummaryResponse,
)
from src.services.cash_flow_history import get_effective_timezone
from src.services.query_service import QueryService
from src.util.types import UserPool


def _calendar_month_count(request: TransactionSummaryRequest) -> int:
    return (
        (request.to_date.year - request.from_date.year) * 12
        + request.to_date.month
        - request.from_date.month
        + 1
    )


async def build_transaction_summary(
    db: DBSession,
    current_user: UserPool,
    query_service: QueryService,
    request: TransactionSummaryRequest,
) -> TransactionSummaryResponse:
    """Aggregate transaction activity for an organization and date range."""
    if not current_user.organization_id:
        raise HTTPException(403, "User does not belong to an organization")

    zone, _ = await get_effective_timezone(db, current_user)
    local_start = datetime.combine(request.from_date, time.min, tzinfo=zone)
    local_end = datetime.combine(
        request.to_date + timedelta(days=1), time.min, tzinfo=zone
    )
    start_utc = local_start.astimezone(timezone.utc)
    end_utc = local_end.astimezone(timezone.utc)

    amount = func.abs(Transaction.amount)
    base = (
        query_service.org_filtered_query(
            model=Transaction,
            current_user=current_user,
        )
        .join(Account, Transaction.account_id == Account.uuid)
        .where(
            Transaction.date >= start_utc,
            Transaction.date < end_utc,
            Transaction.type.in_(("income", "expense", "refund")),
            Account.account_type.in_(request.account_types),
        )
    )
    statement = base.with_only_columns(
        func.coalesce(
            func.sum(case((Transaction.type == "expense", amount), else_=0)), 0
        ).label("gross_expense"),
        func.coalesce(
            func.sum(case((Transaction.type == "refund", amount), else_=0)), 0
        ).label("refunds"),
        func.coalesce(
            func.sum(case((Transaction.type == "income", amount), else_=0)), 0
        ).label("income"),
        func.coalesce(
            func.sum(case((Transaction.type == "expense", 1), else_=0)), 0
        ).label("expense_transaction_count"),
        func.coalesce(
            func.sum(case((Transaction.type == "refund", 1), else_=0)), 0
        ).label("refund_transaction_count"),
        func.coalesce(
            func.sum(case((Transaction.type == "income", 1), else_=0)), 0
        ).label("income_transaction_count"),
    )

    row = (await db.execute(statement)).one()
    gross_expense = int(row.gross_expense or 0)
    refunds = int(row.refunds or 0)
    income = int(row.income or 0)
    expense_transaction_count = int(row.expense_transaction_count or 0)
    refund_transaction_count = int(row.refund_transaction_count or 0)
    income_transaction_count = int(row.income_transaction_count or 0)
    net_spending = gross_expense - refunds
    net_activity = income - net_spending
    month_count = _calendar_month_count(request)

    return TransactionSummaryResponse(
        gross_expense=gross_expense,
        refunds=refunds,
        net_spending=net_spending,
        income=income,
        net_activity=net_activity,
        expense_transaction_count=expense_transaction_count,
        refund_transaction_count=refund_transaction_count,
        income_transaction_count=income_transaction_count,
        average_expense=(
            round(gross_expense / expense_transaction_count, 2)
            if expense_transaction_count
            else 0.0
        ),
        average_monthly_spending=round(net_spending / month_count, 2),
        from_date=request.from_date,
        to_date=request.to_date,
        included_account_types=request.account_types,
    )
