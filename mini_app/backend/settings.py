from dotenv import load_dotenv
from os import getenv

load_dotenv()

BOT_TOKEN = getenv("BOT_TOKEN")
DATABASE_URL = getenv("DATABASE_URL")

ASYNC_ENGINE_POOL_SIZE = int(getenv("ASYNC_ENGINE_POOL_SIZE", 20))
ASYNC_ENGINE_MAX_OVERFLOW = int(getenv("ASYNC_ENGINE_MAX_OVERFLOW", 50))