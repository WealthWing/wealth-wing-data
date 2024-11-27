from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from typing import Annotated
from fastapi import Depends
import os



load_dotenv()

sql_url = os.getenv("SQLALCHEMY_DATABASE_URL")

engine = create_engine(sql_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()
        
        
db_session = Annotated[Session, Depends(get_db)]  


