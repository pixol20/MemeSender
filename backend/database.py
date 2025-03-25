from logging import exception
from os import getenv

import psycopg2
from dotenv import load_dotenv

MEMES_IN_INLINE_LIST = 20

load_dotenv()

HOST = getenv("HOST")
DBNAME = getenv("DBNAME")
USER = getenv("DBUSER")
PASSWORD = getenv("PASSWORD")
PORT = getenv("PORT")

try:
    conn = psycopg2.connect(host=HOST, dbname=DBNAME, user=USER,
                        password=PASSWORD, port=PORT)
except BaseException as e:
    print(str(e))
    print("I am unable to connect to the database")


def search_for_meme_inline_by_query(query: str):
    with conn.cursor() as curs:
        try:
            curs.execute("SELECT name, telegram_media_id, media_type FROM public.memes WHERE name = %s OR %s = ANY(tags);",
                         (query,query))
            conn.commit()
            return curs.fetchmany(MEMES_IN_INLINE_LIST)
        except (Exception, psycopg2.DatabaseError) as error:
            conn.rollback()
            print("error: " + str(error))

def add_database_entry(user_id: int, telegram_media_id: int, name: str, tags: list[str], media_type: str,
                       duration=0, is_public=False) -> bool:
    with conn.cursor() as curs:
        try:
            curs.execute("""INSERT INTO public.memes(telegram_uploader_id, telegram_media_id, duration, name, tags, media_type, is_public)
	VALUES (%s, %s, %s, %s, %s, %s, %s);""", (user_id, telegram_media_id, duration, name, tags, media_type, is_public))
            conn.commit()
            return True
        except BaseException as e:
            print("error: " + str(e))
            if conn is not None:
                conn.rollback()
                return False
            return False