from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from src.model.models import Expense
from src.schemas.expense import ExpenseCreate, ExpenseResponse
from src.database.connect import DBSession
from src.util.types import UserPool
from src.util.user import get_current_user
from src.util.expense import create_expense_in_db

expense_router = APIRouter()


@expense_router.post("/create", status_code=200, response_model=ExpenseResponse)
async def create_expense(
    expense_data: ExpenseCreate,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    return await create_expense_in_db(expense_data, db, current_user.sub)


@expense_router.get("/all", status_code=200, response_model=List[ExpenseResponse])
async def get_expenses(
    db: DBSession, current_user: UserPool = Depends(get_current_user)
):
    expenses_stmt = select(Expense).filter(Expense.user_id == current_user.sub)

    expenses = await db.execute(expenses_stmt)
    result = expenses.scalars().all()

    if not result:
        raise HTTPException(status_code=404, detail="No expenses found")

    return result
