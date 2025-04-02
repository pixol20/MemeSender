import logging
from dotenv import load_dotenv
from os import getenv
from typing import AsyncGenerator, Optional

from sqlalchemy import select, text
from sqlalchemy.orm import close_all_sessions
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
    AsyncSession,
)
from sqlalchemy.exc import IntegrityError
from models import User, Base, Meme

# Load environment variables
load_dotenv()

# Database configuration from environment variables
HOST = getenv("HOST")
DBNAME = getenv("DBNAME")
USER = getenv("DBUSER")
PASSWORD = getenv("PASSWORD")
PORT = getenv("PORT")
MEMES_IN_INLINE_LIST = 20


logger = logging.getLogger(__name__)

# Global variables for engine and session maker
engine: Optional[AsyncEngine] = None
session_maker: Optional[async_sessionmaker[AsyncSession]] = None


async def init_database() -> None:
    """
    Initialize the asynchronous engine and create all tables.
    """
    global engine, session_maker

    db_url = f"postgresql+psycopg://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}"
    engine = create_async_engine(db_url)
    if not engine:
        logger.error("Failed to create engine")
        return

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("""CREATE EXTENSION IF NOT EXISTS pgroonga;"""))

        await conn.execute(text("""CREATE INDEX IF NOT EXISTS pgroonga_memes_tags_index ON memes
                                            USING pgroonga (tags)
                                            WITH (normalizers='NormalizerNFKC150("remove_symbol", true)');"""))

        await conn.execute(text("""CREATE INDEX IF NOT EXISTS pgroonga_memes_titles_index ON memes
                                            USING pgroonga (title)
                                            WITH (normalizers='NormalizerNFKC150("remove_symbol", true)');"""))

        await conn.execute(text("""CREATE INDEX IF NOT EXISTS pgroonga_collections_tags_index ON collections
                                            USING pgroonga (tags)
                                            WITH (normalizers='NormalizerNFKC150("remove_symbol", true)');"""))

        await conn.execute(text("""CREATE INDEX IF NOT EXISTS pgroonga_collections_titles_index ON collections
                                            USING pgroonga (title)
                                            WITH (normalizers='NormalizerNFKC150("remove_symbol", true)');"""))
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)



async def get_user(user_id: int, session: AsyncSession) -> Optional[User]:
    """
    Retrieve a user by telegram_id.
    """
    stmt = select(User).where(User.telegram_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _add_or_get_user(user_id: int, session: AsyncSession) -> Optional[User]:
    """
    Retrieve the user with the given user_id. If not found, create and return a new user.
    """
    if user_id is None:
        logger.error("User ID cannot be None")
        return None

    new_user = User(telegram_id=user_id)
    session.add(new_user)
    try:
        await session.commit()
        return new_user
    except IntegrityError:
        await session.rollback()  # Rollback the failed transaction
        # If insertion fails, retrieve the user
        return await get_user(user_id, session)


async def add_database_entry(
        user_id: int,
        telegram_media_id: str,
        name: str,
        tags: list[str],
        media_type: str,
        duration: int,
        is_public: bool,
) -> bool:
    try:
        async with session_maker() as session:
            async with session.begin():
                user = await _add_or_get_user(user_id=user_id, session=session)
                if not user:
                    logger.error("Invalid user")
                    return False

                new_meme = Meme(
                    uploader_telegram_id=user_id,
                    telegram_media_id=telegram_media_id,
                    duration=duration,
                    title=name,
                    tags=tags,
                    media_type=media_type,
                    is_public=is_public,
                )
                session.add(new_meme)
        return True

    except Exception as e:
        logger.error(f"Error while adding meme to database: {e}")
        return False


async def generate_OR_query(query: str) -> str:
    return " OR ".join(query.split())


async def search_for_meme_inline_by_query(query: str, user_id: int):
    async with session_maker() as session:
        OR_query = await generate_OR_query(query)

        search_query = text("""
            SELECT title, telegram_media_id, media_type
            FROM memes
            WHERE (
                title &@ pgroonga_condition(
                    :query,
                    ARRAY[5],
                    index_name => 'pgroonga_memes_titles_index',
                    fuzzy_max_distance_ratio => 0.34
                )
                OR tags &@ pgroonga_condition(
                    :query,
                    index_name => 'pgroonga_memes_tags_index',
                    fuzzy_max_distance_ratio => 0.34
                )
                OR title &@~ pgroonga_condition(
                    :OR_query,
                    ARRAY[1],
                    index_name => 'pgroonga_memes_titles_index',
                    fuzzy_max_distance_ratio => 0.34
                )
                OR tags &@~ pgroonga_condition(
                    :OR_query,
                    index_name => 'pgroonga_memes_tags_index',
                    fuzzy_max_distance_ratio => 0.34
                )
            )
            AND (is_public = TRUE OR uploader_telegram_id = :user_id)
            ORDER BY pgroonga_score(tableoid, ctid) DESC;
        """)

        result = await session.execute(
            search_query,
            {'query': query, 'OR_query': OR_query, 'user_id': user_id}
        )

        # Fetch all rows as a list of tuples
        memes_list = result.fetchmany(MEMES_IN_INLINE_LIST)
        return memes_list


async def close_all_connections():
    close_all_sessions()
    await engine.dispose()
