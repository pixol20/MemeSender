import database
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()

@asynccontextmanager
async def lifespan(instance: FastAPI):
    await database.init_database()
    yield
    await database.close_all_connections()


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/api/tasks/{tg_id}")
async def test(tg_id: int):
    pass
