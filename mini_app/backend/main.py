import database
import json
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, RedirectResponse
from utils.helpers import validate_mini_app_data

from sqlalchemy.ext.asyncio import AsyncSession
from database import get_session


load_dotenv()

@asynccontextmanager
async def lifespan(instance: FastAPI):
    await database.init_database()
    yield
    await database.close_all_connections()


app = FastAPI()

@app.middleware("http")
async def data_validation_middleware(request: Request, call_next):
    if request.method in ["POST", "PUT"]:
        body = await request.json()
        initData = body.get("initData")

        if not initData:
            return JSONResponse(status_code=401, content="UNAUTHORIZED")

        is_valid, data = validate_mini_app_data(initData)

        if not is_valid:
            return JSONResponse(status_code=401, content="UNAUTHORIZED")

        user = json.loads(data.get("user"))

        user_id = user.get("id")
        username = user.get("username", "")
        first_name = user.get("first_name", "")

        if not user_id:
            return JSONResponse(status_code=401, content="UNAUTHORIZED")

        body["player_id"] = user_id
        body["username"] = username
        body["first_name"] = first_name

        request._body = json.dumps(body).encode("utf-8")

    response = await call_next(request)
    return response




app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/getpopularmemes")
async def get_popular_memes(session: AsyncSession = Depends(get_session)):
