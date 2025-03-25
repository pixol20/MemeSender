from os import getenv
import logging
import psycopg2.pool
from dotenv import load_dotenv
import atexit

MEMES_IN_INLINE_LIST = 20
MIN_CONNECTIONS = 1
MAX_CONNECTIONS = 20

load_dotenv()

HOST = getenv("HOST")
DBNAME = getenv("DBNAME")
USER = getenv("DBUSER")
PASSWORD = getenv("PASSWORD")
PORT = getenv("PORT")

try:
    conn_pool = psycopg2.pool.SimpleConnectionPool(minconn=MIN_CONNECTIONS,maxconn=MAX_CONNECTIONS,host=HOST,
                                              dbname=DBNAME, user=USER,
                                              password=PASSWORD, port=PORT)
except BaseException as e:
    logging.warning(str(e))
    logging.warning("I am unable to connect to the database")

def get_connection():
    if conn_pool:
        try:
            return conn_pool.getconn()
        except BaseException as error:
            logging.error(f"Error getting connection from pool: {error}")
    return None


def release_connection(conn):
    if conn_pool and conn:
        try:
            conn_pool.putconn(conn)
        except BaseException as error:
            logging.error(f"Error releasing connection back to pool: {error}")

def close_all_connections():
    if conn_pool:
        conn_pool.closeall()
        logging.log("Closed all connections")
        
atexit.register(close_all_connections)

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
        logging.error(f"Error while searching for meme {error}")
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
            logging.error(f"Error while searching for meme {error}")
            conn.rollback()
            return False
        finally:
            release_connection(conn)