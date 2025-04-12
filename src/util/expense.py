from fastapi import HTTPException
from src.model.models import Expense
from sqlalchemy.orm import Session
from src.schemas.expense import ExpenseCreate

from src.database.connect import DBSession


async def create_expense_in_db(expense_data: ExpenseCreate, db: DBSession, user_id: str) -> Expense:    
    try:
        expense_dict = expense_data.model_dump(exclude_unset=False)
        expense_dict["user_id"] = user_id
        expense = Expense(**expense_dict)
        
        db.add(expense)
        await db.commit()
        await db.refresh(expense)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create expense: {e}")
    
    return expense