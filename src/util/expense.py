from fastapi import HTTPException
from src.model.models import Expense
from sqlalchemy.orm import Session
from src.schemas.expense import ExpenseCreate


def create_expense_in_db(expense_data: ExpenseCreate, db: Session, user_id: str) -> Expense:
    expense_dict = expense_data.model_dump(exclude_unset=False)
    expense_dict["user_id"] = user_id
    expense = Expense(**expense_dict)
    
    try:
        db.add(expense)
        db.commit()
        db.refresh(expense)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create expense: {e}")
    
    return expense