
from uuid import UUID
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, case, select, and_, or_
from sqlalchemy.exc import SQLAlchemyError
from src.schemas.user import Perm
from src.model.param_models import TransactionsParams, TransactionByNameParams
from src.services.params import ParamsService
from src.model.models import Transaction, Account, AccountTypeEnum, Subscription, Category
from src.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    SubscriptionCandidateResponse,
    TransactionSummaryResponse,
    TransactionUpdateSubscriptionRequest,
    TransactionsAllResponse,
    TransactionsAllRequest,
    TransactionUpdateSubscriptionResponse,
    TransactionsByNameResponse,
    TransactionByNameMetaResponse,
    TransactionByNamePeriodResponse,
    TransactionByNameStatsResponse,
    TransactionByNameYearComparisonResponse,
    CashFlowHistoryRequest,
    CashFlowHistoryResponse,
)
from collections import defaultdict
from typing import Optional
from src.database.connect import DBSession
from src.util.types import UserPool
from src.util.user import get_current_user, has_permission
from src.util.transaction import create_transaction_in_db
from src.services.query_service import get_query_service, QueryService
from src.services.subscription_candidate_service import infer_frequency
from src.services.cash_flow_history import get_cash_flow_history

transaction_router = APIRouter()


@transaction_router.get(
    "/cash-flow-history", status_code=200, response_model=CashFlowHistoryResponse
)
async def cash_flow_history(
    db: DBSession,
    request: Annotated[CashFlowHistoryRequest, Query()],
    current_user: UserPool = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
):
    """Return zero-filled cash-flow periods for the authenticated organization.

    The service aggregates income, expenses, and refunds using the configured
    user or organization timezone before returning the periods. The frontend
    should use the response ``timezone`` and timezone-aware period boundaries
    for labels; it should not re-bucket the returned data in browser UTC.

    Args:
        db: Async database session used to load timezone settings and query
            organization-scoped transactions.
        request: Date range, granularity, and optional account, category, or
            project filters.
        current_user: Authenticated user and organization context.
        query_service: Query builder that enforces organization isolation.

    Returns:
        Cash-flow totals and zero-filled periods validated by the response
        model.

    Raises:
        HTTPException: If the user lacks read permission or is not associated
            with an organization.
    """

    if not has_permission(current_user, Perm.READ):
        raise HTTPException(403, "User does not have permission to view transactions")
    return await get_cash_flow_history(db, current_user, query_service, request)


@transaction_router.post("/create", status_code=200, response_model=TransactionResponse)
async def create_transaction(
    transaction_data: TransactionCreate,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    """Create one transaction for the authenticated user.

    Request validation is handled by ``TransactionCreate``. Persistence and
    transaction-specific rules, including amount/date normalization and
    fingerprint-based deduplication, remain in the service layer rather than
    in the router.

    Args:
        transaction_data: Validated transaction fields supplied by the client.
        db: Async database session used to persist the transaction.
        current_user: Authenticated user whose ID owns the new transaction.

    Returns:
        The created transaction serialized as ``TransactionResponse``.

    Raises:
        HTTPException: If the user lacks write permission.
    """
    if not has_permission(current_user, Perm.WRITE):
        raise HTTPException(
            403, "User does not have permission to create organizations"
        )
    return await create_transaction_in_db(transaction_data, db, current_user.sub)


@transaction_router.get("/all", status_code=200, response_model=TransactionsAllResponse)
async def get_transactions(
    db: DBSession,
    transaction_filters: Annotated[TransactionsAllRequest, Query()],
    current_user: UserPool = Depends(get_current_user),
    params: TransactionsParams = Depends(),
    params_service: ParamsService = Depends(ParamsService),
    query_service: QueryService = Depends(get_query_service),
):
    """List organization-scoped transactions with filtering and pagination.

    Filters are combined across dimensions, while IDs and names within the
    same dimension use OR semantics. Date, search, sorting, pagination, and
    count handling are delegated to ``ParamsService``. All database access is
    asynchronous and the query remains organization-scoped through
    ``QueryService``.

    Args:
        db: Async database session used to execute the filtered query.
        transaction_filters: Optional category, account, merchant, amount,
            and transaction-type filters from the query string.
        current_user: Authenticated user and organization context.
        params: Shared date, search, sort, and pagination parameters.
        params_service: Applies shared query-processing behavior.
        query_service: Builds the organization-scoped base query.

    Returns:
        A paginated ``TransactionsAllResponse`` containing transaction
        response models and pagination metadata.

    Raises:
        HTTPException: If the user lacks read permission.
    """
    if not has_permission(current_user, Perm.READ):
        raise HTTPException(403, "User does not have permission to view transactions")
    base_stmt = query_service.org_filtered_query(
        model=Transaction,
        account_attr="account",
        category_attr="category",
        current_user=current_user,
    )

    amount_magnitude = func.abs(Transaction.amount)

    if transaction_filters.minimum_amount_cents is not None:
        base_stmt = base_stmt.where(
            amount_magnitude >= transaction_filters.minimum_amount_cents
        )
    if transaction_filters.maximum_amount_cents is not None:
        base_stmt = base_stmt.where(
            amount_magnitude <= transaction_filters.maximum_amount_cents
        )

    if transaction_filters.account_type:
        base_stmt = base_stmt.join(
            Account, Transaction.account_id == Account.uuid
        ).where(Account.account_type == transaction_filters.account_type)
    else:
        base_stmt = base_stmt.join(Account, Transaction.account_id == Account.uuid)

    # --- New purpose-built filters -----------------------------------------
    filter_conditions = []

    # Category dimension: IDs OR names (case-insensitive exact names)
    category_conditions = []
    if transaction_filters.category_ids:
        category_conditions.append(
            Transaction.category_id.in_(transaction_filters.category_ids)
        )
    if transaction_filters.category_names:
        normalized_cat_names = [
            name.lower() for name in transaction_filters.category_names if name
        ]
        if normalized_cat_names:
            category_conditions.append(
                func.lower(Category.title).in_(normalized_cat_names)
            )
    if category_conditions:
        filter_conditions.append(or_(*category_conditions))
        base_stmt = base_stmt.join(
            Category, Transaction.category_id == Category.uuid
        )

    # Account dimension: IDs OR names (case-insensitive exact names)
    account_conditions = []
    if transaction_filters.account_ids:
        account_conditions.append(
            Transaction.account_id.in_(transaction_filters.account_ids)
        )
    if transaction_filters.account_names:
        normalized_acct_names = [
            name.lower() for name in transaction_filters.account_names if name
        ]
        if normalized_acct_names:
            account_conditions.append(
                func.lower(Account.account_name).in_(normalized_acct_names)
            )
    if account_conditions:
        filter_conditions.append(or_(*account_conditions))

    # Merchant search: case-insensitive partial match on title
    merchant_search = (transaction_filters.merchant_search or "").strip()
    if merchant_search:
        filter_conditions.append(Transaction.title.ilike(f"%{merchant_search}%"))

    # Transaction types: exact membership
    if transaction_filters.transaction_types:
        filter_conditions.append(
            Transaction.type.in_(transaction_filters.transaction_types)
        )

    if filter_conditions:
        base_stmt = base_stmt.where(and_(*filter_conditions))

    # Prevent duplicate rows from relationship joins
    base_stmt = base_stmt.distinct()
    # ------------------------------------------------------------------------

    filtered_stmt = params_service.process_query(
        stmt=base_stmt,
        params=params,
        model=Transaction,
        date_field="date",
        search_fields=["title", "type"],
    )

    transactions = await db.execute(filtered_stmt)
    result = transactions.scalars().all()

    if not result:
        return TransactionsAllResponse(
            transactions=[],
            total_count=0,
            has_more=False,
            total_pages=0,
        )

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
            account_id=t.account_id,
            account_name=(t.account.account_name if t.account else None),
            category=(t.category.title if t.category else None),
            project_id=t.project_id,
            uuid=t.uuid,
            title=t.title,
            amount=t.amount,
            description=t.description,
            date=t.date,
            currency=t.currency,
            type=t.type,
            category_id=t.category_id,
            user_id=t.user_id,
            subscription_candidate=t.subscription_candidate,
            subscription_id=t.subscription_id,
        )
        for t in result
    ]

    return TransactionsAllResponse(
        transactions=transactions,
        total_count=total,
        has_more=has_more,
        total_pages=total_pages,
    )


@transaction_router.get(
    "/summary", status_code=200, response_model=TransactionSummaryResponse
)
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
    if not has_permission(current_user, Perm.READ):
        raise HTTPException(403, "User does not have permission to view transactions")

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


@transaction_router.get(
    "/subscription-candidates",
    status_code=200,
    response_model=list[SubscriptionCandidateResponse],
)
async def get_subscription_candidates(
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
    account_type: Optional[AccountTypeEnum] = None,
    limit: int = 100,
):
    if not has_permission(current_user, Perm.READ):
        raise HTTPException(403, "User does not have permission to view transactions")

    try:
        safe_limit = min(max(limit, 1), 500)
        stmt = query_service.org_filtered_query(
            model=Transaction,
            account_attr="account",
            category_attr="category",
            current_user=current_user,
        ).where(Transaction.subscription_candidate.is_(True))

        if account_type:
            stmt = stmt.join(Account, Transaction.account_id == Account.uuid).where(
                Account.account_type == account_type
            )

        stmt = stmt.order_by(Transaction.date.desc()).limit(safe_limit)
        result = (await db.execute(stmt)).scalars().all()
        
        transactions_by_title = defaultdict(list)
        for t in result:
            transactions_by_title[t.title].append(t.date)
        
        seen_titles = set()
        unique_transactions = []
        for t in result:
            if t.title not in seen_titles:
                seen_titles.add(t.title)
                unique_transactions.append(t)

        return [
            SubscriptionCandidateResponse(
                account_name=(t.account.account_name if t.account else None),
                account_id=t.account_id,
                category=(t.category.title if t.category else None),
                project_id=t.project_id,
                uuid=t.uuid,
                title=t.title,
                amount=t.amount,
                description=t.description,
                date=t.date,
                currency=t.currency,
                type=t.type,
                category_id=t.category_id,
                frequency=infer_frequency(transactions_by_title[t.title]) if t.title in transactions_by_title else "unknown",
                user_id=t.user_id,
                subscription_candidate=t.subscription_candidate,
                subscription_id=t.subscription_id,
            )
            for t in unique_transactions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve subscription candidates: {str(e)}")


@transaction_router.get(
    "/by-name", status_code=200, response_model=TransactionsByNameResponse
)
async def get_transactions_by_name(
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
    params: TransactionByNameParams = Depends(),
    params_service: ParamsService = Depends(ParamsService),
    query_service: QueryService = Depends(get_query_service),
    account_type: Optional[AccountTypeEnum] = None,
):
    """
    Get all transactions matching a specific title/merchant name within a date range.
    Returns spending statistics and year-over-year comparison.
    """
    if not has_permission(current_user, Perm.READ):
        raise HTTPException(403, "User does not have permission to view transactions")

    title = (params.title or "").strip()
    if not title:
        raise HTTPException(422, "title query parameter is required")

    try:
        # --- Main query: transactions matching title in date range ---
        base_stmt = query_service.org_filtered_query(
            model=Transaction,
            account_attr="account",
            category_attr="category",
            current_user=current_user,
        )

        if account_type:
            base_stmt = base_stmt.join(
                Account, Transaction.account_id == Account.uuid
            ).where(Account.account_type == account_type)

        title_stmt = base_stmt.where(func.lower(Transaction.title) == title.lower())

        filtered_stmt = params_service.process_query(
            stmt=title_stmt,
            params=params,
            model=Transaction,
            date_field="date",
            search_fields=["title", "type"],
        )

        result = (await db.execute(filtered_stmt)).scalars().all()

        if not result:
            return TransactionsByNameResponse(
                meta=TransactionByNameMetaResponse(
                    title=title,
                    period=TransactionByNamePeriodResponse(
                        from_date=params.from_date,
                        to_date=params.to_date,
                    ),
                    total_transactions=0,
                ),
                stats=TransactionByNameStatsResponse(
                    total_spent=0.0,
                    average_per_month=0.0,
                    max_single_charge=0.0,
                    min_single_charge=0.0,
                    last_transaction_date=None,
                    first_transaction_date=None,
                ),
                year_comparison=None,
                transactions=[],
            )

        # --- Build transaction response list ---
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
                subscription_candidate=t.subscription_candidate,
                subscription_id=t.subscription_id,
            )
            for t in result
        ]

        # --- Calculate statistics (amounts converted from cents to dollars) ---
        amounts_dollars = [abs(t.amount) / 100.0 for t in result]
        total_spent = sum(amounts_dollars)
        dates = [t.date for t in result if t.date]

        # Calculate months in the selected range for average
        if params.from_date and params.to_date:
            month_diff = (
                (params.to_date.year - params.from_date.year) * 12
                + params.to_date.month
                - params.from_date.month
            )
            num_months = max(month_diff, 1)
        elif dates:
            min_d = min(dates)
            max_d = max(dates)
            month_diff = (
                (max_d.year - min_d.year) * 12 + max_d.month - min_d.month
            )
            num_months = max(month_diff, 1)
        else:
            num_months = 1

        average_per_month = round(total_spent / num_months, 2)

        stats = TransactionByNameStatsResponse(
            total_spent=round(total_spent, 2),
            average_per_month=average_per_month,
            max_single_charge=round(max(amounts_dollars), 2) if amounts_dollars else 0.0,
            min_single_charge=round(min(amounts_dollars), 2) if amounts_dollars else 0.0,
            last_transaction_date=max(dates) if dates else None,
            first_transaction_date=min(dates) if dates else None,
        )

        meta = TransactionByNameMetaResponse(
            title=result[0].title,
            period=TransactionByNamePeriodResponse(
                from_date=params.from_date,
                to_date=params.to_date,
            ),
            total_transactions=len(result),
        )

        # --- Year-over-year comparison ---
        year_comparison = None
        if params.include_year_comparison and params.from_date and params.to_date:
            prev_from = params.from_date.replace(year=params.from_date.year - 1)
            prev_to = params.to_date.replace(year=params.to_date.year - 1)

            prev_base = query_service.org_filtered_query(
                model=Transaction,
                current_user=current_user,
            )

            if account_type:
                prev_base = prev_base.join(
                    Account, Transaction.account_id == Account.uuid
                ).where(Account.account_type == account_type)

            prev_stmt = prev_base.where(
                func.lower(Transaction.title) == title.lower(),
                Transaction.date >= prev_from,
                Transaction.date <= prev_to,
            )

            prev_result = (await db.execute(prev_stmt)).scalars().all()
            prev_total = sum(abs(t.amount) / 100.0 for t in prev_result)

            current_total = total_spent
            difference = round(current_total - prev_total, 2)
            percentage_change = (
                round((difference / prev_total) * 100, 1) if prev_total > 0 else 0.0
            )

            year_comparison = TransactionByNameYearComparisonResponse(
                current_year_total=round(current_total, 2),
                previous_year_total=round(prev_total, 2),
                difference=difference,
                percentage_change=percentage_change,
            )

        return TransactionsByNameResponse(
            meta=meta,
            stats=stats,
            year_comparison=year_comparison,
            transactions=transactions,
        )

    except HTTPException:
        raise
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(500, "Database error while retrieving transactions")
    except Exception:
        await db.rollback()
        raise HTTPException(500, "Failed to retrieve transactions by name")


@transaction_router.get(
    "/{transaction_id}", status_code=200, response_model=TransactionResponse
)
async def get_transaction_by_id(
    transaction_id: str,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
):
    
    if not has_permission(current_user, Perm.READ):
        raise HTTPException(403, "User does not have permission to view transactions")

    base_stmt = query_service.org_filtered_query(
        model=Transaction,
        account_attr="account",
         category_attr="category",
        current_user=current_user,
    )
    
    transaction_stmt = base_stmt.where(Transaction.uuid == transaction_id)
    result = await db.execute(transaction_stmt)
    transaction = result.scalars().first()

    if not transaction:
        raise HTTPException(404, "Transaction not found")

    return TransactionResponse(
        account_id=transaction.account_id,
        account_name=(transaction.account.account_name if transaction.account else None),
        category=(transaction.category.title if transaction.category else None),  
        project_id=transaction.project_id,
        uuid=transaction.uuid,
        title=transaction.title,
        amount=transaction.amount,
        description=transaction.description,
        date=transaction.date,
        currency=transaction.currency,
        type=transaction.type,
        category_id=transaction.category_id,
        user_id=transaction.user_id,
        subscription_candidate=transaction.subscription_candidate,
        subscription_id=transaction.subscription_id,
    )

@transaction_router.post("/update-subscription", status_code=200, response_model=TransactionUpdateSubscriptionResponse)
async def update_transaction_subscription(
    transaction_data: TransactionUpdateSubscriptionRequest,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
):
    if not has_permission(current_user, Perm.WRITE):
        raise HTTPException(403, "User does not have permission to update transactions")

    transaction_name = (transaction_data.transaction_name or "").strip()
    if not transaction_name:
        raise HTTPException(422, "transaction_name must not be empty")

    try:
        subscription_stmt = query_service.org_filtered_query(
            model=Subscription,
            current_user=current_user,
        ).where(Subscription.uuid == transaction_data.subscription_id)
        subscription = (await db.execute(subscription_stmt)).scalars().first()
        if not subscription:
            raise HTTPException(404, "Subscription not found")

        base_stmt = query_service.org_filtered_query(
            model=Transaction,
            current_user=current_user,
        )

        transaction_stmt = base_stmt.where(
            Transaction.title == transaction_name
        )
        transactions = (await db.execute(transaction_stmt)).scalars().all()
        if not transactions:
            raise HTTPException(
                404, "No matching subscription-candidate transactions found"
            )

        for transaction in transactions:
            transaction.subscription_id = transaction_data.subscription_id
            transaction.subscription_candidate = False

        await db.commit()
        return {
            "updated_count": len(transactions),
            "subscription_id": str(transaction_data.subscription_id),
            "transaction_name": transaction_name,
        }
    except HTTPException:
        raise
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(500, "Database error while updating subscription")
    except Exception:
        await db.rollback()
        raise HTTPException(500, "Failed to update transaction subscription")
