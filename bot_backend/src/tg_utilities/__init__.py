from src.models import MediaType
from src.constants import MEME_MEDIA_MESSAGE


from telegram.ext import (
    ContextTypes,
)

from telegram import Message
from typing import Optional

async def get_media_type(message: Message) -> Optional[MediaType]:
    media_type = None
    if message.photo:
        media_type = MediaType.PHOTO
    elif message.video:
        media_type = MediaType.VIDEO
    elif message.animation:
        media_type = MediaType.GIF
    elif message.voice:
        media_type = MediaType.VOICE
    elif message.audio:
        media_type = MediaType.AUDIO

    return media_type

async def delete_current_media_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if isinstance(context.user_data.get(MEME_MEDIA_MESSAGE, None), Message):
        await context.bot.deleteMessage(message_id=context.user_data[MEME_MEDIA_MESSAGE].id, chat_id=chat_id)