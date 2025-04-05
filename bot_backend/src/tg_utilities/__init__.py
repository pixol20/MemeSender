from src.models import MediaType
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