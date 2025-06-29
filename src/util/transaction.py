from fastapi import HTTPException
from src.model.models import Transaction
from sqlalchemy.orm import Session
from src.schemas.transaction import TransactionCreate
import hashlib
from src.database.connect import DBSession


async def create_transaction_in_db(transaction_data: TransactionCreate, db: DBSession, user_id: str) -> Transaction:    
    try:
        transaction_dict = transaction_data.model_dump(exclude_unset=False)
        transaction_dict["user_id"] = user_id
        transaction = Transaction(**transaction_dict)
        
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create transaction: {e}")
    
    return transaction

