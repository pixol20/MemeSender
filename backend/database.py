from os import getenv
import logging
import psycopg2.pool
from dotenv import load_dotenv
import atexit

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


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logging.getLogger("httpx").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


conn_pool = None

# create connection pool
try:
    conn_pool = psycopg2.pool.SimpleConnectionPool(minconn=MIN_CONNECTIONS,maxconn=MAX_CONNECTIONS,host=HOST,
                                              dbname=DBNAME, user=USER,
                                              password=PASSWORD, port=PORT)
except BaseException as e:
    logger.warning(str(e))
    logger.warning("I am unable to connect to the database")

# connection functions

def get_connection():
    if conn_pool:
        try:
            return conn_pool.getconn()
        except BaseException as error:
            logger.error(f"Error getting connection from pool: {error}")
    return None


def release_connection(conn):
    if conn_pool and conn:
        try:
            conn_pool.putconn(conn)
        except BaseException as error:
            logger.error(f"Error releasing connection back to pool: {error}")

def close_all_connections():
    if conn_pool:
        conn_pool.closeall()
        logger.info("closed all connections")
        
atexit.register(close_all_connections)

# Create database tables
create_conn = get_connection()
if create_conn:
    with create_conn.cursor() as cur:
        try:
            cur.execute("""
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

            cur.execute("""CREATE TABLE IF NOT EXISTS public.memes
                        (
                            id bigserial,
                            telegram_uploader_id bigint,
                            duration integer,
                            telegram_media_id text,
                            name text,
                            tags text[],
                            media_type media_type,
                            is_public boolean,
                            PRIMARY KEY (id)
                        );
                        """)
            create_conn.commit()
        except BaseException as e:
            logger.error(f"failed to create database tables error: {e}")
            create_conn.rollback()
        finally:
            release_connection(create_conn)

def search_for_meme_inline_by_query(query: str):
    conn  = get_connection()
    if conn is None:
        return []

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name, telegram_media_id, media_type FROM public.memes WHERE name = %s OR %s = ANY(tags);",
                         (query,query))
            conn.commit()
            return cur.fetchmany(MEMES_IN_INLINE_LIST)
    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        logger.error(f"Error while searching for meme {error}")
    finally:
        release_connection(conn)

def add_database_entry(user_id: int,
                       telegram_media_id: int,
                       name: str, tags: list[str],
                       media_type: str,
                       duration=0,
                       is_public=False) -> bool:
    conn = get_connection()
    if conn is None:
        return False

    with conn.cursor() as cur:
        try:
            cur.execute("""INSERT INTO public.memes(telegram_uploader_id, telegram_media_id, 
            duration, name, tags, media_type, is_public)
	VALUES (%s, %s, %s, %s, %s, %s, %s);""", (user_id, telegram_media_id, duration, name, tags, media_type, is_public))
            conn.commit()
            return True
        except BaseException as error:
            logging.error(f"Error inserting meme: {error}")
            conn.rollback()
            return False
        finally:
            release_connection(conn)