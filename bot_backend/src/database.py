from os import getenv
import logging
from psycopg_pool import AsyncConnectionPool
from dotenv import load_dotenv

load_dotenv()

# constants
MEMES_IN_INLINE_LIST = 20
MIN_CONNECTIONS = 2
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
except Exception as e:
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
                await create_cur.execute("""CREATE TABLE IF NOT EXISTS public.users
                                            (
                                                telegram_id bigint,
                                                is_banned boolean DEFAULT FALSE,
                                                saved_collections bigint[] DEFAULT '{}'::bigint[],
                                                PRIMARY KEY (telegram_id)
                                            );""")

                await create_cur.execute("""CREATE TABLE IF NOT EXISTS public.memes
                                            (
                                                id bigserial,
                                                uploader_telegram_id bigint,
                                                duration integer DEFAULT 0,
                                                likes bigint DEFAULT 0,
                                                telegram_media_id text,
                                                title text,
                                                tags text[] DEFAULT '{}'::text[],
                                                media_type media_type,
                                                is_public boolean DEFAULT FALSE,
                                                PRIMARY KEY (id),
                                                CONSTRAINT fkey_users_id FOREIGN KEY (uploader_telegram_id)
                                                    REFERENCES public.users (telegram_id) MATCH SIMPLE
                                                    ON UPDATE NO ACTION
                                                    ON DELETE NO ACTION
                                                    NOT VALID
                                            );
                            """)
                await create_cur.execute("""CREATE TABLE IF NOT EXISTS public.collections
                                            (
                                                id bigserial,
                                                creator_telegram_id bigint,
                                                meme_ids bigint[],
                                                likes bigint DEFAULT 0,
                                                users_ammount bigint DEFAULT 1,
                                                title text,
                                                tags text[],
                                                is_public boolean,
                                                PRIMARY KEY (id),
                                                CONSTRAINT fkey_users_id FOREIGN KEY (creator_telegram_id)
                                                    REFERENCES public.users (telegram_id) MATCH SIMPLE
                                                    ON UPDATE NO ACTION
                                                    ON DELETE NO ACTION
                                                    NOT VALID
                                            );""")

                await create_cur.execute("""CREATE INDEX IF NOT EXISTS pgroonga_memes_tags_index ON memes
                                            USING pgroonga (tags)
                                            WITH (normalizers='NormalizerNFKC150("remove_symbol", true)');""")

                await create_cur.execute("""CREATE INDEX IF NOT EXISTS pgroonga_memes_titles_index ON memes
                                            USING pgroonga (title)
                                            WITH (normalizers='NormalizerNFKC150("remove_symbol", true)');""")

                await create_cur.execute("""CREATE INDEX IF NOT EXISTS pgroonga_collections_tags_index ON collections
                                            USING pgroonga (tags)
                                            WITH (normalizers='NormalizerNFKC150("remove_symbol", true)');""")

                await create_cur.execute("""CREATE INDEX IF NOT EXISTS pgroonga_collections_titles_index ON collections
                                            USING pgroonga (title)
                                            WITH (normalizers='NormalizerNFKC150("remove_symbol", true)');""")


                await create_cur.execute("""SET enable_seqscan = off;""")
                await create_conn.commit()
            except Exception as e:
                logger.error(f"failed to create database tables error: {e}")
                await create_conn.rollback()


async def add_user(user_id):
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("(SELECT 1 FROM public.users WHERE telegram_id = %s LIMIT 1);", (user_id,))
            exists = await cur.fetchone()
            if not exists:
                # Insert the new user
                await cur.execute(
                    "INSERT INTO users (telegram_id, is_banned) VALUES (%s, FALSE);",
                    (user_id, )
                )
            await conn.commit()



async def search_for_meme_inline_by_query(query: str, user_id: int):
    async with pool.connection() as conn:
        try:
            async with conn.cursor() as cur:
                await cur.execute("""SELECT title, telegram_media_id, media_type, 
                                     pgroonga_score(tableoid, ctid) AS score
                                     FROM memes
                                     WHERE (title &@~ pgroonga_condition(
                                                             %s,
                                                             ARRAY[5],
                                                             index_name => 'pgroonga_memes_titles_index',
                                                             fuzzy_max_distance_ratio => 0.34
                                                           )
                                    OR tags &@~ pgroonga_condition(
                                                        %s,
                                                        ARRAY[1],
                                                        index_name => 'pgroonga_memes_tags_index',
                                                        fuzzy_max_distance_ratio => 0.34
                                                      )) 
									 AND (is_public = TRUE OR uploader_telegram_id = %s)
                                     ORDER BY score DESC;""",
                             (query,query,user_id))
                await conn.commit()
                return await cur.fetchmany(MEMES_IN_INLINE_LIST)
        except Exception as error:
            await conn.rollback()
            logger.error(f"Error while searching for meme {error}")

async def add_database_entry(user_id: int,
                       telegram_media_id: str,
                       name: str, tags: list[str],
                       media_type: str,
                       duration=0,
                       is_public=False) -> bool:
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            try:
                await add_user(user_id=user_id)
                await cur.execute("""INSERT INTO public.memes(uploader_telegram_id, telegram_media_id, 
                duration, title, tags, media_type, is_public)
        VALUES (%s, %s, %s, %s, %s, %s, %s);""", (user_id, telegram_media_id, duration, name, tags, media_type, is_public))
                await conn.commit()
                return True
            except Exception as error:
                logging.error(f"Error inserting meme: {error}")
                await conn.rollback()
                return False
