import math
from typing import Sequence
from uuid import uuid4
from telegram import (InlineQueryResultCachedVideo,
                      InlineQueryResultCachedPhoto,
                      InlineQueryResultCachedGif,
                      InlineQueryResultCachedVoice,
                      InlineQueryResultCachedAudio,
                      InlineQueryResult,
                      InlineKeyboardMarkup,
                      InlineKeyboardButton,
                      )

from sqlalchemy import ScalarResult


from src.models import Meme, MediaType
import json

from src.constants import MEMES_PER_PAGE
from src.constants import CALLBACK_MEME, CALLBACK_CONFIRM_DELETE, CALLBACK_PAGE, CALLBACK_DELETE, CALLBACK_RENAME, CALLBACK_BACK


async def generate_inline_list(database_data: list[tuple[str, str, str]]) -> Sequence[InlineQueryResult]:
    """Generate inline entries from database response
       Args:
           database_data: data output from database
       Returns:
           Inline query results that can be sent to client
    """
    if database_data is None:
        return []
    inline_list = []
    for i_meme in database_data:
        if i_meme[2] == "video":
            inline_list.append(InlineQueryResultCachedVideo(
                id=str(uuid4()),
                video_file_id=i_meme[1],
                title=i_meme[0],
            ))
        elif i_meme[2] == "photo":
            inline_list.append(InlineQueryResultCachedPhoto(
                id=str(uuid4()),
                photo_file_id=i_meme[1],
                title=i_meme[0]
            ))
        elif i_meme[2] == "gif":
            inline_list.append(InlineQueryResultCachedGif(
                id=str(uuid4()),
                gif_file_id=i_meme[1],
                title=i_meme[0]
            ))
        elif i_meme[2] == "voice":
            inline_list.append(InlineQueryResultCachedVoice(
                id=str(uuid4()),
                voice_file_id=i_meme[1],
                title=i_meme[0]
            ))
        elif i_meme[2] == "audio":
            inline_list.append(InlineQueryResultCachedAudio(
                id=str(uuid4()),
                audio_file_id=i_meme[1],
            ))
    return inline_list


async def generate_text_for_meme_button(in_meme: Meme):
    emoji_mapping = {
        MediaType.AUDIO.value: "🔊",
        MediaType.GIF.value: "🎞️",
        MediaType.PHOTO.value: "🖼️",
        MediaType.VIDEO.value: "📹",
        MediaType.VOICE.value: "🎤",
    }
    media_type_value = in_meme.media_type.value
    emoji = emoji_mapping.get(media_type_value, "❓")
    return f"{emoji}{in_meme.title}{emoji}"


async def generate_inline_keyboard_page(in_memes: Sequence[Meme], page_number: int) -> InlineKeyboardMarkup:
    keyboard = []

    in_memes_len = len(in_memes)
    start = min(page_number*MEMES_PER_PAGE, in_memes_len)
    end = min(page_number*MEMES_PER_PAGE+MEMES_PER_PAGE, in_memes_len)

    for current_meme in in_memes[start:end]:
        button_text = await generate_text_for_meme_button(current_meme)
        new_button = [InlineKeyboardButton(button_text, callback_data=CALLBACK_MEME+str(current_meme.id))]
        keyboard.append(new_button)

    left_right = []


    if page_number > 0:
        left_right.append(InlineKeyboardButton("⬅️", callback_data=CALLBACK_PAGE+str(max(0, page_number - 1))))

    # Last page is length of memes divided by memes per page and rounded up.
    # I use minus one here because page numbers start from 0
    last_page_number = math.ceil(in_memes_len / MEMES_PER_PAGE)-1

    if page_number < last_page_number:
        left_right.append(InlineKeyboardButton("➡️", callback_data=CALLBACK_PAGE+str(min(last_page_number, page_number + 1))))


    keyboard.append(left_right)
    result = InlineKeyboardMarkup(keyboard)
    return result

async def generate_meme_controls(meme: Meme) -> InlineKeyboardMarkup:
    """Generate controls like delete or rename for chosen meme
       Args:
           meme: selected meme
       Returns:
           InlineKeyboardMarkup for selected meme
    """
    meme_id = meme.id
    delete_button = InlineKeyboardButton("🗑️Delete meme🗑️", callback_data=CALLBACK_DELETE+str(meme_id))
    rename_button = InlineKeyboardButton("✏️Rename meme✏️", callback_data=CALLBACK_RENAME+str(meme_id))
    go_back_button = InlineKeyboardButton("⬅️", callback_data=CALLBACK_BACK)

    keyboard = [[delete_button], [rename_button], [go_back_button]]

    result = InlineKeyboardMarkup(keyboard)

    return result

async def generate_yes_no_for_meme_deletion(meme: Meme):
    meme_id = meme.id

    delete_button = InlineKeyboardButton("delete", callback_data=CALLBACK_CONFIRM_DELETE+str(meme_id))
    not_delete_button = InlineKeyboardButton("not delete", callback_data=CALLBACK_MEME+str(meme_id))
    keyboard = [[delete_button, not_delete_button]]

    result = InlineKeyboardMarkup(keyboard)
    return result