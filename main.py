import logging
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from src.middleware.auth import AuthMiddleware
from src.routers import health_check
from src.routers.subscription import subscription_router
from src.routers.user import user_router
from src.routers.categories import category_router
from src.routers.transaction import transaction_router
from src.routers.account import account_router
from src.routers.project import project_router
from src.routers.import_file import import_router
from dotenv import load_dotenv
import os


load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI()


# Add routers
app.include_router(health_check.router, prefix="/health", tags=["health"])
app.include_router(subscription_router, prefix="/subscription", tags=["subscription"])
app.include_router(user_router, prefix="/user", tags=["user"])
app.include_router(category_router, prefix="/category", tags=["category"])
app.include_router(transaction_router, prefix="/transaction", tags=["transaction"])
app.include_router(project_router, prefix="/project", tags=["project"])
app.include_router(account_router, prefix="/account", tags=["account"])
app.include_router(import_router, prefix="/import", tags=["import"])

# Add middleware
app.add_middleware(AuthMiddleware)

backend_url = os.getenv("BE_URL")
frontend_url = os.getenv("FE_URL")


origins = [
    "https://localhost:3000",
    "http://localhost:3000",
    "https://localhost:3001",
    "http://localhost:3001",
    backend_url,
    frontend_url,
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
