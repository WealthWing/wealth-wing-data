from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from sqlalchemy import case, cast, func, literal, select
from sqlalchemy.dialects.postgresql import INTERVAL

from src.database.connect import DBSession
from src.model.models import Organization, Transaction, User
from src.schemas.transaction import (
    CashFlowHistoryRequest,
    CashFlowHistoryResponse,
    CashFlowPeriodResponse,
)
from src.services.query_service import QueryService
from src.util.types import UserPool


def _valid_zone(name: str | None) -> tuple[ZoneInfo, str] | None:
    if not name:
        return None
    try:
        zone = ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None
    return zone, name


async def _effective_timezone(db: DBSession, current_user: UserPool) -> tuple[ZoneInfo, str]:
    user = await db.scalar(select(User).where(User.uuid == current_user.sub))
    organization = None
    if user and user.organization_id:
        organization = await db.scalar(
            select(Organization).where(Organization.uuid == user.organization_id)
        )
    for candidate in (
        _valid_zone(getattr(user, "timezone", None)),
        _valid_zone(getattr(organization, "timezone", None)),
    ):
        if candidate:
            return candidate
    return ZoneInfo("UTC"), "UTC"


def _bucket_end(start: datetime, granularity: str) -> datetime:
    local_date = start.date()
    if granularity == "day":
        next_date = local_date + timedelta(days=1)
        return datetime.combine(next_date, time.min, tzinfo=start.tzinfo)
    if granularity == "week":
        next_date = local_date + timedelta(days=7)
        return datetime.combine(next_date, time.min, tzinfo=start.tzinfo)
    if local_date.month == 12:
        next_date = local_date.replace(year=local_date.year + 1, month=1, day=1)
    else:
        next_date = local_date.replace(month=local_date.month + 1, day=1)
    return datetime.combine(next_date, time.min, tzinfo=start.tzinfo)


async def get_cash_flow_history(
    db: DBSession,
    current_user: UserPool,
    query_service: QueryService,
    request: CashFlowHistoryRequest,
) -> CashFlowHistoryResponse:
    if not current_user.organization_id:
        raise HTTPException(403, "User does not belong to an organization")

    zone, timezone_name = await _effective_timezone(db, current_user)
    local_start = datetime.combine(request.from_date, time.min, tzinfo=zone)
    local_end = datetime.combine(
        request.to_date + timedelta(days=1), time.min, tzinfo=zone
    )
    start_utc = local_start.astimezone(timezone.utc)
    end_utc = local_end.astimezone(timezone.utc)

    base = query_service.org_filtered_query(
        model=Transaction, current_user=current_user
    ).where(
        Transaction.date >= start_utc,
        Transaction.date < end_utc,
        Transaction.type.in_(("income", "expense", "refund")),
    )
    if request.category_ids:
        base = base.where(Transaction.category_id.in_(request.category_ids))
    if request.account_ids:
        base = base.where(Transaction.account_id.in_(request.account_ids))
    if request.project_ids:
        base = base.where(Transaction.project_id.in_(request.project_ids))

    local_date = func.timezone(timezone_name, Transaction.date)
    bucket_start = func.date_trunc(request.granularity, local_date).label("bucket_start")
    amount = func.abs(Transaction.amount)
    aggregates = (
        base.with_only_columns(
            bucket_start,
            func.coalesce(func.sum(case((Transaction.type == "income", amount), else_=0)), 0).label("income"),
            func.coalesce(func.sum(case((Transaction.type == "expense", amount), else_=0)), 0).label("expense"),
            func.coalesce(func.sum(case((Transaction.type == "refund", amount), else_=0)), 0).label("refunds"),
            func.count(Transaction.uuid).label("transaction_count"),
        )
        .group_by(bucket_start)
        .subquery()
    )

    local_from = datetime.combine(request.from_date, time.min)
    local_to = datetime.combine(request.to_date, time.min)
    if request.granularity == "day":
        step = cast(literal("1 day"), INTERVAL)
    elif request.granularity == "week":
        local_from -= timedelta(days=local_from.weekday())
        local_to -= timedelta(days=local_to.weekday())
        step = cast(literal("1 week"), INTERVAL)
    else:
        local_from = local_from.replace(day=1)
        local_to = local_to.replace(day=1)
        step = cast(literal("1 month"), INTERVAL)

    series = (
        func.generate_series(local_from, local_to, step)
        .table_valued("bucket_start")
        .render_derived(name="series")
    )
    statement = (
        select(
            series.c.bucket_start,
            func.coalesce(aggregates.c.income, 0).label("income"),
            func.coalesce(aggregates.c.expense, 0).label("expense"),
            func.coalesce(aggregates.c.refunds, 0).label("refunds"),
            func.coalesce(aggregates.c.transaction_count, 0).label("transaction_count"),
        )
        .select_from(series.outerjoin(aggregates, aggregates.c.bucket_start == series.c.bucket_start))
        .order_by(series.c.bucket_start)
    )
    rows = (await db.execute(statement)).all()
    periods = []
    for row in rows:
        start = row.bucket_start.replace(tzinfo=zone)
        end = _bucket_end(start, request.granularity)
        income, expense, refunds = map(int, (row.income, row.expense, row.refunds))
        periods.append(
            CashFlowPeriodResponse(
                period_start=start,
                period_end=end,
                income=income,
                expense=expense,
                refunds=refunds,
                net=income + refunds - expense,
                transaction_count=int(row.transaction_count),
            )
        )
    return CashFlowHistoryResponse(
        timezone=timezone_name,
        from_date=request.from_date,
        to_date=request.to_date,
        granularity=request.granularity,
        periods=periods,
    )
