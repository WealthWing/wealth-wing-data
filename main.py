import logging
from fastapi import FastAPI, Request
from src.model.models import User
from src.schemas.user import UserResponse, UserCreate
from src.middleware.auth import AuthMiddleware
from src.routers import health_check
from src.routers.subscription import subscription_router
from src.routers.user import user_router
from src.routers.categories import category_router
from src.database.connect import db_session
from typing import List

logging.basicConfig(level=logging.INFO)

app = FastAPI()



app.include_router(health_check.router, prefix="/health", tags=["health"])
app.include_router(subscription_router, prefix="/subscription", tags=["subscription"])
app.include_router(user_router, prefix="/user", tags=["user"])
app.include_router(category_router, prefix="/category", tags=["category"])

app.add_middleware(AuthMiddleware)


# @app.get("/tests", response_model=List[TestTableResponse])
# def get_tests(db: service):
#     tests = db.query(TestTable).all()
#     return tests

@app.get("/users", response_model=List[UserResponse])
def get_tests(db: db_session):
    tests = db.query(User).all()
    return tests