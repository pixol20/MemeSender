from typing import Union, Optional
from telegram.ext import ContextTypes
from telegram import Message, InlineKeyboardMarkup

from src.models import Meme
from src.tg_utilities.classes import MemeMenu
from src.constants import MEMES_CONTROL_MESSAGE

async def create_or_update_menu(context: ContextTypes.DEFAULT_TYPE,
                                chat_id: Union[int, str],
                                text: str,
                                reply_markup: Optional[InlineKeyboardMarkup] = None,
                                new_meme: Optional[Meme] = None,
                                destroy_menu: bool = False,
                                delete_media: bool = False):

    old_menu = context.user_data.get(MEMES_CONTROL_MESSAGE)

    if isinstance(old_menu, MemeMenu):
        if destroy_menu:
            await old_menu.destroy()

            # Create message for updater
            menu_message = await context.bot.sendMessage(text=text, chat_id=chat_id, reply_markup=reply_markup)
            context.user_data[MEMES_CONTROL_MESSAGE] = MemeMenu(text_message=menu_message)
        else:
            await old_menu.switch_state(context=context,
                                        chat_id=chat_id,
                                        new_text=text,
                                        new_meme=new_meme,
                                        delete_media=delete_media,
                                        reply_markup=reply_markup)
    else:
        # Create message for updater
        menu_message = await context.bot.sendMessage(text=text, chat_id=chat_id, reply_markup=reply_markup)
        context.user_data[MEMES_CONTROL_MESSAGE] = MemeMenu(text_message=menu_message)