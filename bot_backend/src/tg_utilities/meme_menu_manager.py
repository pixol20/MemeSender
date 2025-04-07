from src.models import MediaType, Meme
from src.constants import MEME_MEDIA_MESSAGE, MEMES_CONTROL_MESSAGE


from telegram.ext import (
    ContextTypes,
)

from telegram import Message, InlineKeyboardMarkup
from typing import Optional


async def send_media_message_from_meme(context: ContextTypes.DEFAULT_TYPE,
                                       meme: Meme, chat_id: int,
                                       reply_markup: Optional[InlineKeyboardMarkup] = None ) -> Message:
    replied_media = None
    meme_media_type = meme.media_type
    if meme_media_type.value == MediaType.PHOTO.value:
        replied_media = await context.bot.sendPhoto(photo=meme.telegram_media_id,
                                                    chat_id=chat_id,
                                                    reply_markup=reply_markup)
    elif meme_media_type.value  == MediaType.VIDEO.value:
        replied_media = await context.bot.sendVideo(video=meme.telegram_media_id,
                                                    chat_id=chat_id,
                                                    reply_markup=reply_markup)
    elif meme_media_type.value  == MediaType.GIF.value:
        replied_media = await context.bot.sendAnimation(animation=meme.telegram_media_id,
                                                        chat_id=chat_id,
                                                        reply_markup=reply_markup)
    elif meme_media_type.value  == MediaType.VOICE.value:
        replied_media = await context.bot.sendVoice(voice=meme.telegram_media_id,
                                                    chat_id=chat_id,
                                                    reply_markup=reply_markup)

    context.user_data[MEME_MEDIA_MESSAGE] = replied_media

    return replied_media


async def delete_current_media_message(
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Delete the current media message if it exists in the user data."""
    message = context.user_data.get(MEME_MEDIA_MESSAGE)
    if isinstance(message, Message):
        await message.delete()
        context.user_data[MEME_MEDIA_MESSAGE] = None


async def create_or_alter_control_message(
    context: ContextTypes.DEFAULT_TYPE,
    new_text: str,
    chat_id: int,
    reply_markup: Optional[InlineKeyboardMarkup] = None
) -> Optional[Message]:
    """Edit the control message text if it exists in the user data."""
    message = context.user_data.get(MEMES_CONTROL_MESSAGE)
    if isinstance(message, Message):
        message = await message.edit_text(text=new_text, reply_markup=reply_markup)
    else:
        message = await context.bot.sendMessage(chat_id=chat_id, text=new_text, reply_markup=reply_markup)

    context.user_data[MEMES_CONTROL_MESSAGE] = message
    return message

async def delete_menu(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    message = context.user_data.get(MEMES_CONTROL_MESSAGE)

    if isinstance(message, Message):
        await message.delete()

    context.user_data[MEMES_CONTROL_MESSAGE] = None

async def update_meme_menu(context: ContextTypes.DEFAULT_TYPE,
                           new_text: str,
                           chat_id: int,
                           reply_markup: Optional[InlineKeyboardMarkup] = None,
                           delete_media=False) -> Optional[Message]:

    msg = await create_or_alter_control_message(context=context, new_text=new_text, reply_markup=reply_markup, chat_id=chat_id)

    if delete_media:
        await delete_current_media_message(context=context)

    return msg