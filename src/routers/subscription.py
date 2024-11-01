from fastapi import APIRouter, HTTPException, Depends
from requests import Session
from src.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
)
from src.model.models import Subscription
from src.util.user import get_current_user
from src.model.models import User
from src.util.types import UserPool
from src.database.connect import service
from typing import List

subscription_router = APIRouter()


@subscription_router.post(
    "/create", status_code=201, response_model=SubscriptionResponse
)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    db: service,
    current_user: UserPool = Depends(get_current_user),
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

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


@subscription_router.put(
    "/update/{subscription_id}", status_code=201, response_model=SubscriptionResponse
)
async def update_subscription(
    subscription_data: SubscriptionUpdate,
    subscription_id: str,
    db: service,
    current_user: UserPool = Depends(get_current_user),
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

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


@subscription_router.get(
    "/subscriptions", status_code=201, response_model=List[SubscriptionResponse]
)
async def get_user_subscriptions(
    db: service,
    current_user: UserPool = Depends(get_current_user),
):
    subscriptions = (
        db.query(Subscription).filter(Subscription.user_id == current_user.sub).all()
    )
    return subscriptions
