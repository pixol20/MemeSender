from typing import Sequence
from uuid import uuid4
from telegram import (InlineQueryResultCachedVideo,
                      InlineQueryResultCachedPhoto,
                      InlineQueryResultCachedGif,
                      InlineQueryResultCachedVoice,
                      InlineQueryResultCachedAudio,
                      InlineQueryResult)

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

