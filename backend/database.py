from os import getenv
import logging
from psycopg_pool import AsyncConnectionPool
from dotenv import load_dotenv

load_dotenv()

# constants
MEMES_IN_INLINE_LIST = 20
MIN_CONNECTIONS = 1
MAX_CONNECTIONS = 20

HOST = getenv("HOST")
DBNAME = getenv("DBNAME")
USER = getenv("DBUSER")
PASSWORD = getenv("PASSWORD")
PORT = getenv("PORT")

CONNECTION_STRING = f"host = {HOST} port = {PORT} dbname = {DBNAME} user = {USER} password = {PASSWORD}"

logger = logging.getLogger("psycopg.pool")
logger.setLevel(logging.INFO)

pool = None

# create connection pool
try:
    pool = AsyncConnectionPool(conninfo=CONNECTION_STRING, min_size=MIN_CONNECTIONS, max_size=MAX_CONNECTIONS, open=False)
except BaseException as e:
    logging.error(str(e))
    logger.warning("I am unable to connect to the database")

async def open_pool():
    await pool.open()
    await pool.wait()
    logger.info("pool ready")

async def close_all_connections():
    await pool.close()


async def init_database():
    await open_pool()

    # Create database tables
    async with pool.connection() as create_conn:
        async with create_conn.cursor() as create_cur:
            try:
                await create_cur.execute("""CREATE EXTENSION IF NOT EXISTS pgroonga;""")
                await create_cur.execute("""CREATE INDEX IF NOT EXISTS pgroonga_memes_tags_index ON memes USING pgroonga (tags)""")
                await create_cur.execute("""CREATE INDEX IF NOT EXISTS pgroonga_memes_name_index ON memes USING pgroonga (name)""")
                await create_cur.execute("""SET enable_seqscan = off;""")
                await create_cur.execute("""
                                DO
                                $$
                                BEGIN
                                    IF NOT EXISTS (
                                        SELECT 1
                                        FROM pg_type typ
                                        JOIN pg_namespace nsp ON nsp.oid = typ.typnamespace
                                        WHERE nsp.nspname = current_schema()
                                          AND typ.typname = 'media_type'
                                    ) THEN
                                        CREATE TYPE public.media_type AS ENUM ('audio', 'gif', 'photo', 'video', 'voice');
                                    END IF;
                                END;
                                $$
                                LANGUAGE plpgsql;
                """)

                await create_cur.execute("""CREATE TABLE IF NOT EXISTS public.memes
                            (
                                id bigserial,
                                telegram_uploader_id bigint,
                                duration integer,
                                telegram_media_id text,
                                name text,
                                tags text[] DEFAULT '{}'::text[],
                                media_type media_type,
                                is_public boolean,
                                PRIMARY KEY (id)
                            );
                            """)
                await create_conn.commit()
            except BaseException as e:
                logger.error(f"failed to create database tables error: {e}")
                await create_conn.rollback()



async def search_for_meme_inline_by_query(query: str):
    async with pool.connection() as conn:
        try:
            async with conn.cursor() as cur:
                await cur.execute("SELECT name, telegram_media_id, media_type FROM public.memes WHERE name = %s OR %s = ANY(tags);",
                             (query,query))
                await conn.commit()
                return await cur.fetchmany(MEMES_IN_INLINE_LIST)
        except Exception as error:
            await conn.rollback()
            logger.error(f"Error while searching for meme {error}")

async def add_database_entry(user_id: int,
                       telegram_media_id: int,
                       name: str, tags: list[str],
                       media_type: str,
                       duration=0,
                       is_public=False) -> bool:
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute("""INSERT INTO public.memes(telegram_uploader_id, telegram_media_id, 
                duration, name, tags, media_type, is_public)
        VALUES (%s, %s, %s, %s, %s, %s, %s);""", (user_id, telegram_media_id, duration, name, tags, media_type, is_public))
                await conn.commit()
                return True
            except BaseException as error:
                logging.error(f"Error inserting meme: {error}")
                await conn.rollback()
                return False

