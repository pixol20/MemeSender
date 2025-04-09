from typing import Optional, Union


from telegram import Message, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.models import Meme, MediaType

class MemeMenu:
    def __init__(self,
                 text_message: Optional[Message],
                 media_message: Optional[Message] = None):
        self.text_message = text_message
        self.media_message = media_message

    async def switch_state(self, context: ContextTypes.DEFAULT_TYPE,
                           chat_id: Union[int, str],
                           new_text: str,
                           reply_markup: Optional[InlineKeyboardMarkup] = None,
                           new_meme: Optional[Meme] = None,
                           delete_media: bool = False):
        if delete_media:
            await self.delete_media()

        if new_meme:
            await self.delete_media()

            meme_media_type = new_meme.media_type
            if meme_media_type.value == MediaType.PHOTO.value:
                self.media_message = await context.bot.sendPhoto(photo=new_meme.telegram_media_id,
                                                                 chat_id=chat_id)
            elif meme_media_type.value == MediaType.VIDEO.value:
                self.media_message = await context.bot.sendVideo(video=new_meme.telegram_media_id,
                                                                 chat_id=chat_id)
            elif meme_media_type.value == MediaType.GIF.value:
                self.media_message = await context.bot.sendAnimation(animation=new_meme.telegram_media_id,
                                                                     chat_id=chat_id)
            elif meme_media_type.value == MediaType.VOICE.value:
                self.media_message = await context.bot.sendVoice(voice=new_meme.telegram_media_id,
                                                                 chat_id=chat_id)


        if self.text_message:
            await self.text_message.edit_text(text=new_text, reply_markup=reply_markup)


    async def destroy(self):
        await self.delete_text()
        await self.delete_media()


    async def delete_text(self):
        if isinstance(self.text_message, Message):
            await self.text_message.delete()
            self.text_message = None


    async def delete_media(self):
        if isinstance(self.media_message, Message):
            await self.media_message.delete()
            self.media_message = None
