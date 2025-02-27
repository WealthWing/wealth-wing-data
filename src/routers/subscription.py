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
from typing import Annotated, List
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession


subscription_router = APIRouter()

""" Create a new subscription """

@subscription_router.post(
    "/create", status_code=200, response_model=SubscriptionResponse
)
async def create_subscription(
    subscription_data: SubscriptionCreate,
     db:DBSession,
    current_user: UserPool = Depends(get_current_user),
):

    subscription_dict = subscription_data.model_dump(exclude_unset=False)
    subscription_dict["user_id"] = current_user.sub
    subscription = Subscription(**subscription_dict)

    try:
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create store: {e}")

    return subscription


""" Update a subscription """


@subscription_router.put(
    "/update/{subscription_id}", status_code=200, response_model=SubscriptionResponse
)
async def update_subscription(
    subscription_data: SubscriptionUpdate,
    subscription_id: str,
     db:DBSession,
    current_user: UserPool = Depends(get_current_user),
):

    subscription_model = (
        db.query(Subscription)
        .filter(Subscription.uuid == subscription_id)
        .filter(Subscription.user_id == current_user.sub)
        .first()
    )

    if not subscription_model:
        raise HTTPException(status_code=404, detail="Subscription not found")

    try:
        # remove unused fields exclude_unset=True
        subscription_dict = subscription_data.model_dump(exclude_unset=True)

        for key, value in subscription_dict.items():
            if getattr(subscription_model, key) != value:
                setattr(subscription_model, key, value)

        db.add(subscription_model)
        db.commit()
        db.refresh(subscription_model)
        return subscription_model
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create store: {e}")


""" Get all subscriptions """


@subscription_router.get(
    "/summary", status_code=200, response_model=List[SubscriptionsAllResponse]
)
async def get_user_subscriptions(
     db:DBSession,
    current_user: UserPool = Depends(get_current_user),
):

    subscriptions = (
        db.query(Subscription.uuid, Subscription.name, Subscription.amount)
        .filter(Subscription.user_id == current_user.sub)
        .all()
    )

    return subscriptions


""" Get a single subscription """


@subscription_router.get(
    "/detail/{subscription_id}", status_code=200, response_model=SubscriptionResponse
)
async def get_subscription(
    subscription_id: str,
     db:DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    # load join table joinedload(Subscription.user)
    subscription = (
        db.query(Subscription).options(joinedload(Subscription.user))
        .filter(Subscription.uuid == subscription_id)
        .filter(Subscription.user_id == current_user.sub)
        .first()
    )

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return subscription


@subscription_router.delete("/delete/{subscription_id}", status_code=204)
async def delete_subscription(
    subscription_id: str,
     db:DBSession,
    current_user: UserPool = Depends(get_current_user),
):

    subscription = (
        db.query(Subscription)
        .filter(Subscription.uuid == subscription_id)
        .filter(Subscription.user_id == current_user.sub)
        .first()
    )

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    try:
               
        db.delete(subscription)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to delete subscription: {e}"
        )

    return "Subscription deleted successfully"
