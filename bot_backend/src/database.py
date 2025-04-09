import logging
from dotenv import load_dotenv
from os import getenv
from typing import Optional

from sqlalchemy import select, text, Sequence, ScalarResult, delete, update
from sqlalchemy.orm import close_all_sessions
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
    AsyncSession,
)
from sqlalchemy.exc import IntegrityError
from models import User, Base, Meme
from src.models import MediaType

# Load environment variables
load_dotenv()

# Database configuration from environment variables
HOST = getenv("HOST", "localhost")
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
        await conn.execute(text("""CREATE EXTENSION IF NOT EXISTS pgroonga;"""))
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)



async def add_user_to_database(telegram_id: int) -> bool:
    try:
        async with session_maker() as session:
            async with session.begin():
                get_user_stmt = select(User).where(User.telegram_id == telegram_id)
                db_response = await session.execute(get_user_stmt)
                user_exists = db_response.first()

                if not user_exists:
                    new_user = User(telegram_id = telegram_id)
                    session.add(new_user)
                return True
    except Exception as e:
        logger.error(f"Error while adding user to database: {e}")
        return False



async def add_meme(
        user_id: int,
        telegram_media_id: str,
        name: str,
        tags: list[str],
        media_type: MediaType,
        duration: int,
        is_public: bool,
) -> bool:
    try:
        async with session_maker() as session:
            async with session.begin():
                new_meme = Meme(
                    creator_telegram_id=user_id,
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
            AND (is_public = TRUE OR creator_telegram_id = :user_id)
            ORDER BY pgroonga_score(tableoid, ctid) DESC;
        """)

        result = await session.execute(
            search_query,
            {'query': query, 'OR_query': OR_query, 'user_id': user_id}
        )

        # Fetch all rows as a list of tuples
        memes_list = result.fetchmany(MEMES_IN_INLINE_LIST)
        return memes_list



async def get_all_user_memes(user_telegram_id: int) -> Sequence[Meme]:
    """get all memes created by user"""
    async with session_maker() as session:
        async with session.begin():
            stmt = select(Meme).where(Meme.creator_telegram_id == user_telegram_id).order_by(Meme.id.desc())

            result = await session.execute(stmt)

            memes = result.scalars().all()
            return memes

async def get_meme_by_id_and_check_user(meme_id: int, user_telegram_id: int) -> Optional[Meme]:
    async with session_maker() as session:
        async with session.begin():
            stmt = select(Meme).where(Meme.id == meme_id).where(Meme.creator_telegram_id == user_telegram_id)

            result = await session.execute(stmt)

            meme = result.scalars().first()
            return meme


async def delete_meme_check_and_check_user(meme_id: int, user_telegram_id: int) -> bool:
    try:
        async with session_maker() as session:
            async with session.begin():
                stmt = delete(Meme).where(Meme.id == meme_id).where(Meme.creator_telegram_id == user_telegram_id)

                result = await session.execute(stmt)
    except Exception as e:
        logger.error(f"Error while deleting meme: {e}")
        return False

    return True


async def rename_meme_and_check_user(meme_id: int, user_telegram_id: int, new_name: str) -> bool:
    try:
        async with session_maker() as session:
            async with session.begin():
                stmt = update(Meme).where(Meme.id == meme_id).where(Meme.creator_telegram_id == user_telegram_id).values(title=new_name)
                result = await session.execute(stmt)
    except Exception as e:
        logger.error(f"Error while deleting meme: {e}")
        return False

    return True



async def close_all_connections():
    close_all_sessions()
    await engine.dispose()
