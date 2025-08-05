from fastapi import APIRouter, HTTPException, Depends
from src.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionsAllResponse,
)
from src.model.models import Subscription
from src.util.user import get_current_user
from src.util.types import UserPool
from src.database.connect import DBSession
from typing import List
from sqlalchemy.orm import joinedload
from sqlalchemy.future import select


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
        raise HTTPException(status_code=500, detail=f"Failed to create store: {e}")
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
    "/summary", status_code=200, response_model=List[SubscriptionsAllResponse]
)
async def get_user_subscriptions(
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    stmt = select(Subscription.uuid, Subscription.name, Subscription.amount).where(
        Subscription.user_id == current_user.sub
    )
    result = await db.execute(stmt)
    subscriptions = result.all()
    return subscriptions


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
        .where(Subscription.uuid == subscription_id)
        .where(Subscription.user_id == current_user.sub)
    )
    result = await db.execute(stmt)
    subscription = result.scalars().first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription


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
