import logging
from fastapi import FastAPI, Request
from src.model.models import User
from starlette.middleware.cors import CORSMiddleware
from src.schemas.user import UserResponse, UserCreate
from src.middleware.auth import AuthMiddleware
from src.routers import health_check
from src.routers.subscription import subscription_router
from src.routers.user import user_router
from src.routers.categories import category_router
from src.routers.expense import expense_router
from src.routers.scope import scope_router
from src.routers.project import project_router
from src.database.connect import get_db
from typing import List

logging.basicConfig(level=logging.INFO)

app = FastAPI()


# Add routers
app.include_router(health_check.router, prefix="/health", tags=["health"])
#app.include_router(subscription_router, prefix="/subscription", tags=["subscription"])
#app.include_router(user_router, prefix="/user", tags=["user"])
#app.include_router(category_router, prefix="/category", tags=["category"])
#app.include_router(expense_router, prefix="/expense", tags=["expense"])
#app.include_router(scope_router, prefix="/scope", tags=["scope"])
app.include_router(project_router, prefix="/project", tags=["project"])

# Add middleware
app.add_middleware(AuthMiddleware)



# Add cores

origins = ["https://localhost:3000", "http://localhost:3000","https://localhost:3001", "http://localhost:3001"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#@app.get("/users", response_model=List[UserResponse])
#def get_tests(db: session):
#    tests = db.query(User).all()
#    return tests