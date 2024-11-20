from fastapi import APIRouter, HTTPException
from src.model.models import Expense
from src.schemas.expense import ExpenseCreate
from src.database.connect import db_session

expense_router = APIRouter()

@expense_router.post("/create", status_code=201)
async def create_expense(expense_data: ExpenseCreate, db: db_session):
    new_expense = Expense(
        amount=expense_data.amount,
        category=expense_data.category,
        description=expense_data.description,
        user_id=expense_data.user_id,
    )
     