import logging
from dotenv import load_dotenv
from os import getenv
from typing import Optional, AsyncGenerator


from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,

    AsyncSession,
)

import settings

load_dotenv("../../.env")

MEMES_IN_INLINE_LIST = 20

logger = logging.getLogger(__name__)


async_engine = create_async_engine(
    settings.DATABASE_URL, pool_size=settings.ASYNC_ENGINE_POOL_SIZE, max_overflow=settings.ASYNC_ENGINE_MAX_OVERFLOW
)
async_session = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)  # noqa

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session.begin() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
