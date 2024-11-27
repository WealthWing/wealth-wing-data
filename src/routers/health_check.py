from fastapi import APIRouter
import logging
from fastapi import   HTTPException
from sqlalchemy import text
from src.database.connect import db_session

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/ping")
async def ping():
    logger.info("Ping endpoint called")
    return {"message": "healthy"}


@router.get("/test_db_connection")
def test_db_connection(db: db_session):
    try:
        result = db.execute(text("SELECT NOW()")).first()
        logger.info("test_db_connection endpoint called")
        return {"message": "Database connection successful!", "time": result[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

    
  