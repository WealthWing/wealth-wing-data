from fastapi import APIRouter, HTTPException
from src.model.models import Expense
from src.database.connect import db_session

expense_router = APIRouter()

@expense_router.post("/create", status_code=201)
async def create_expense(expense_data: ExpenseCreate, db: db_session): 