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

sql_url = os.getenv("DATABASE_URL")


Base = declarative_base()


class DatabaseSessionManager:
    def __init__(self, url: str, engine_kwargs: dict[str, Any] = {}):
        self._engine = create_async_engine(url, **engine_kwargs)
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


sessionmanager = DatabaseSessionManager(sql_url, {"echo": True})


async def get_db():
    async with sessionmanager.session() as session:
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]
