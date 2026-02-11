from fastapi import APIRouter, HTTPException, Depends
from src.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionSummaryResponse,
    SubscriptionsAllResponse,
)
from src.schemas.transaction import TransactionsAllResponse, TransactionResponse
from src.model.models import Subscription, Transaction
from src.model.param_models import TransactionsParams
from src.util.user import get_current_user, has_permission
from src.util.types import UserPool
from src.schemas.user import Perm
from src.database.connect import DBSession
from src.services.params import ParamsService
from src.services.query_service import get_query_service, QueryService
from typing import List
from sqlalchemy.orm import joinedload
from sqlalchemy.future import select
from sqlalchemy import func
from src.services.subscription_candidate_service import calculate_next_billing_date


subscription_router = APIRouter()

""" Create a new subscription """


@subscription_router.post(
    "/create", status_code=200, response_model=SubscriptionResponse
)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    subscription_dict = subscription_data.model_dump(exclude_unset=False)
    subscription_dict["user_id"] = current_user.sub
    subscription = Subscription(**subscription_dict)
    try:
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to create subscription: {str(e)}"
        )
    return subscription


""" Update a subscription """


@subscription_router.put(
    "/update/{subscription_id}", status_code=200, response_model=SubscriptionResponse
)
async def update_subscription(
    subscription_data: SubscriptionUpdate,
    subscription_id: str,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    stmt = select(Subscription).where(
        Subscription.uuid == subscription_id, Subscription.user_id == current_user.sub
    )
    result = await db.execute(stmt)
    subscription_model = result.scalars().first()
    if not subscription_model:
        raise HTTPException(status_code=404, detail="Subscription not found")
    try:
        subscription_dict = subscription_data.model_dump(exclude_unset=True)
        for key, value in subscription_dict.items():
            if getattr(subscription_model, key) != value:
                setattr(subscription_model, key, value)
        db.add(subscription_model)
        await db.commit()
        await db.refresh(subscription_model)
        return subscription_model
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create store: {e}")


""" Get all subscriptions """

@subscription_router.get(
    "/all", status_code=200, response_model=List[SubscriptionsAllResponse]
)
async def get_user_subscriptions(
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    try:
        stmt = select(Subscription).where(Subscription.user_id == current_user.sub)
        result = await db.execute(stmt)
        subscriptions = result.scalars().all()
        return subscriptions
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve subscriptions: {e}"
        )


""" Get a single subscription """

@subscription_router.get(
    "/detail/{subscription_id}", status_code=200, response_model=SubscriptionResponse
)
async def get_subscription(
    subscription_id: str,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    stmt = (
        select(Subscription)
        .options(joinedload(Subscription.user))
        .where(
            Subscription.uuid == subscription_id
            and Subscription.user_id == current_user.sub
        )
    )
    result = await db.execute(stmt)
    subscription = result.scalars().first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return subscription


""" Get all transactions for a subscription """


@subscription_router.get(
    "/{subscription_id}/transactions",
    status_code=200,
    response_model=TransactionsAllResponse,
)
async def get_subscription_transactions(
    subscription_id: str,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
    params: TransactionsParams = Depends(),
    params_service: ParamsService = Depends(ParamsService),
    query_service: QueryService = Depends(get_query_service),
):
    if not has_permission(current_user, Perm.READ):
        raise HTTPException(403, "User does not have permission to view transactions")

    # Verify subscription exists and belongs to user
    sub_stmt = select(Subscription).where(
        Subscription.uuid == subscription_id,
        Subscription.user_id == current_user.sub,
    )
    sub_result = await db.execute(sub_stmt)
    subscription = sub_result.scalars().first()

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    # Build org-filtered query with subscription_id filter
    base_stmt = query_service.org_filtered_query(
        model=Transaction,
        account_attr="account",
        category_attr="category",
        current_user=current_user,
    ).where(Transaction.subscription_id == subscription_id)

    # Apply standard filtering and pagination
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

    # Count total matching records (without pagination)
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

    transaction_list = [
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

    return TransactionsAllResponse(
        transactions=transaction_list,
        total_count=total,
        has_more=has_more,
        total_pages=total_pages,
    )


@subscription_router.delete("/delete/{subscription_id}", status_code=204)
async def delete_subscription(
    subscription_id: str,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    stmt = (
        select(Subscription)
        .where(Subscription.uuid == subscription_id)
        .where(Subscription.user_id == current_user.sub)
    )
    result = await db.execute(stmt)
    subscription = result.scalars().first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    try:
        await db.delete(subscription)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to delete subscription: {e}"
        )
    return "Subscription deleted successfully"


@subscription_router.get("/summary", status_code=200, response_model=SubscriptionSummaryResponse)
async def get_subscription_summary(
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
):
    base_stmt = query_service.org_filtered_query(
        model=Subscription, current_user=current_user
    )
    result = await db.execute(base_stmt)
    subscriptions = result.scalars().all()

    monthly_subscriptions = sum(
        sub.amount for sub in subscriptions if sub.billing_frequency == "monthly"
    )
    yearly_subscriptions_to_monthly = (
        sum(sub.amount for sub in subscriptions if sub.billing_frequency == "yearly") / 12
    )
    weakly_subscriptions_to_monthly = (
        sum(sub.amount for sub in subscriptions if sub.billing_frequency == "weekly") * 4.33
    )
    quarterly_subscriptions_to_monthly = (
        sum(sub.amount for sub in subscriptions if sub.billing_frequency == "quarterly") / 3
    )

    total_monthly_cost_cents = (
        monthly_subscriptions
        + yearly_subscriptions_to_monthly
        + weakly_subscriptions_to_monthly
        + quarterly_subscriptions_to_monthly
    )
    subscription_count = len(subscriptions)
    total_active_subscriptions = sum(1 for sub in subscriptions if sub.status == "active")
    total_inactive_subscriptions = sum(1 for sub in subscriptions if sub.status == "inactive")
    total_paused_subscriptions = sum(1 for sub in subscriptions if sub.status == "paused")
    

    return {
        "total_monthly_cost_cents": round(total_monthly_cost_cents),
        "total_subscriptions_count": subscription_count,
        "total_active_subscriptions_count": total_active_subscriptions,
        "total_inactive_subscriptions_count": total_inactive_subscriptions,
        "total_paused_subscriptions_count": total_paused_subscriptions,
    }
