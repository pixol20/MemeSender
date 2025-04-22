from itertools import count

from sqlalchemy import func, select, text
from database import get_session
from models import Meme, UserLikedMemes
from sqlalchemy.ext.asyncio import AsyncSession


async def get_top_memes(session: AsyncSession, memes_amount = 20):
    stmt = select(Meme, func.count(UserLikedMemes.id).label("total_likes")).join(UserLikedMemes).where(Meme.is_public == True).order_by("total_likes DESC")
    result = await session.execute(stmt)
