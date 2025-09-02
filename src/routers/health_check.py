from fastapi import APIRouter
import logging
from fastapi import HTTPException
from sqlalchemy import text
from src.database.connect import DBSession


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/ping")
async def ping():
    logger.info("Ping endpoint called")
    return {"message": "healthy"}


@router.get("/test_db_connection")
async def test_db_connection(db: DBSession):
    try:
        result = await db.execute(text("SELECT NOW()"))
        row = result.first()
        return {"message": "DB connection successful!", "time": row[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
