from collections.abc import AsyncGenerator
from dotenv import load_dotenv
from sqlalchemy import NullPool, create_engine
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
import contextlib
import boto3
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from typing import Annotated, Any, AsyncIterator
from fastapi import Depends
from logging import getLogger
import os
import json
import urllib

load_dotenv()
logger = getLogger(__name__)

sql_url = os.getenv("SQLALCHEMY_DATABASE_URL")
secret_arn = os.getenv("SECRET_ARN")
region = os.getenv("AWS_REGION")


Base = declarative_base()

class DatabaseSessionManager:
    def __init__(self, host: str, engine_kwargs: dict[str, Any] = {}):
        db_url = self._update_db_url_with_secret(host, secret_arn) if secret_arn else host
        self._engine = create_async_engine(db_url, **engine_kwargs)
        self._sessionmaker = async_sessionmaker(autocommit=False, bind=self._engine)

    async def close(self):
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self._engine.dispose()

        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    def _update_db_url_with_secret(self, db_url: str, secret_arn: str) -> str:
        try:
            client = boto3.client("secretsmanager", region_name=region)

            response = client.get_secret_value(SecretId=secret_arn)
            secret_data = json.loads(response["SecretString"])
            username = secret_data.get("username")
            password = urllib.parse.quote(secret_data.get("password"))
            
            if not username or not password:
                raise ValueError(
                    "Secrets Manager response is missing username or password."
                )

            db_url = db_url.replace("{admin:pass}", f"{username}:{password}")
            logger.debug("Database URL updated with credentials from Secrets Manager.")
            return db_url
        except Exception as e:
            raise ValueError(f"Failed to update database URL: {e}")



sessionmanager = DatabaseSessionManager(sql_url, {"echo": True})


async def get_db():
    async with sessionmanager.session() as session:
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]
