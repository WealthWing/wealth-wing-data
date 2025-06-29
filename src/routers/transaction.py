from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from src.model.models import Transaction
from src.schemas.transaction import TransactionCreate, TransactionResponse
from src.database.connect import DBSession
from src.util.types import UserPool
from src.util.user import get_current_user
from src.util.transaction import create_transaction_in_db

transaction_router = APIRouter()


@transaction_router.post("/create", status_code=200, response_model=TransactionResponse)
async def create_transaction(
    transaction_data: TransactionCreate,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    return await create_transaction_in_db(transaction_data, db, current_user.sub)


@transaction_router.get("/all", status_code=200, response_model=List[TransactionResponse])
async def get_transactions(
    db: DBSession, current_user: UserPool = Depends(get_current_user)
):
    transactions_stmt = select(Transaction).filter(Transaction.user_id == current_user.sub)

    transactions = await db.execute(transactions_stmt)
    result = transactions.scalars().all()

    if not result:
        raise HTTPException(status_code=404, detail="No transactions found")

    return result
