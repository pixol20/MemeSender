from collections.abc import Sequence
from typing import Final

from dotenv import load_dotenv
from os import getenv

from uuid import uuid4
import traceback

from telegram import (Update,
                      ReplyKeyboardMarkup,
                      ReplyKeyboardRemove,
                      Message)

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    InlineQueryHandler,
    CallbackQueryHandler
)
from models import Meme, MediaType

import logging

import database

from tg_utilities import delete_current_media_message
from tg_utilities.generators import (generate_inline_list,
                                     generate_inline_keyboard_page,
                                     generate_meme_controls,
                                     generate_yes_no_for_meme_deletion)
from src.constants import (MEME_NAME, MEME_PUBLIC, MEDIA_TYPE, TAGS, TELEGRAM_MEDIA_ID, DURATION,
                           MEMES_CONTROL_MESSAGE, LAST_SELECTED_PAGE)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN: Final = getenv("BOT_KEY")
BOT_USERNAME: Final = getenv("BOT_NAME")

MEME, NAME, DECIDE_USE_TAGS_OR_NO, HANDLE_TAGS, DECIDE_PUBLIC_OR_NO = range(5)


MAX_TEXT_LENGTH = 512

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    success = await database.add_user_to_database(user_id)
    if success:
        await update.message.reply_text("Hello World")
    else:
        await update.message.reply_text("It seems that something failed. Please report this to the developer")

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompts user to send meme"""
    await update.message.reply_text("Send your meme")
    return MEME

def reset_current_upload_data(user_data):
    """Resets all current meme upload related data"""
    user_data[TELEGRAM_MEDIA_ID] = None
    user_data[MEME_NAME] = None
    user_data[TAGS] = None
    user_data[MEDIA_TYPE] = None
    user_data[DURATION] = None
    user_data[MEME_PUBLIC] = None

async def handle_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Sends user's meme to the database
    Args:
        update: Update object from python-telegram-bot
        context: Context object from python-telegram-bot
    Returns:
        Whether operation was successful or not
    """
    user_data = context.user_data
    user_id = update.message.from_user.id


    logger.info("User %s uploading meme: %s", update.message.from_user.first_name,
                context.user_data[MEME_NAME])

    await update.message.reply_text("Uploading meme", reply_markup=ReplyKeyboardRemove())
    try:
        is_successful = await database.add_database_entry(user_id=user_id, telegram_media_id=user_data[TELEGRAM_MEDIA_ID],
                                                    name=user_data[MEME_NAME], tags=user_data[TAGS],
                                                    media_type=user_data[MEDIA_TYPE], duration=user_data[DURATION],
                                                    is_public=user_data[MEME_PUBLIC])
    except Exception as e:
        is_successful = False
        logger.error(f"Error while uploading meme: {str(e)}")
        logger.error("Stack Trace:\n" + traceback.format_exc())

    if is_successful:
        await update.message.reply_text("Meme uploaded")
    else:
        await update.message.reply_text("Something failed")

    reset_current_upload_data(user_data)
    return is_successful

async def upload_meme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    media = None
    media_type = None
    duration = 0

    if message.photo:
        media = message.photo[-1]  # Highest resolution
        media_type = MediaType.PHOTO
    elif message.video:
        media = message.video
        media_type = MediaType.VIDEO
        duration = media.duration
    elif message.animation:
        media = message.animation
        media_type = MediaType.GIF
        duration = media.duration
    elif message.voice:
        media = message.voice
        media_type = MediaType.VOICE
        duration = media.duration

    elif message.audio:
        media = message.audio
        media_type = MediaType.AUDIO
        duration = media.duration

    if media:
        context.user_data[MEDIA_TYPE] = media_type
        context.user_data[TELEGRAM_MEDIA_ID] = media.file_id
        context.user_data[DURATION] = duration


    await update.message.reply_text("Name your meme")
    return NAME

async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    processed_user_input = update.message.text.strip()

    if len(processed_user_input) > MAX_TEXT_LENGTH:
        await update.message.reply_text("❌ the name is too long")
        return NAME

    context.user_data[MEME_NAME] = processed_user_input
    reply_keyboard = [["Yes✅","No❌"]]
    await update.message.reply_text(
        "Do you want to add tags that help to search it later?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Add tags?"
        ),
    )
    return DECIDE_USE_TAGS_OR_NO



async def decide_use_tags_or_no(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """decides whether to use tags or not depending on user input"""
    user_data = context.user_data
    user_data[TAGS] = []

    if update.message.text == "Yes✅":
        await update.message.reply_text("Input tags one per message, /finish_tags to finish",
                                        reply_markup=ReplyKeyboardRemove())
        return HANDLE_TAGS
    else:
        reply_keyboard = [["Yes✅", "No❌"]]
        await update.message.reply_text(
            "Do you want to make this meme public?",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, input_field_placeholder="Make meme public?"
            ),
        )
        return DECIDE_PUBLIC_OR_NO


async def handle_tags(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Retrieves user tags separated by messages"""
    user_input = update.message.text
    processed_user_input = user_input.strip()

    if len(processed_user_input) > MAX_TEXT_LENGTH:
        await update.message.reply_text("❌ the tag is too long")
        return HANDLE_TAGS

    context.user_data[TAGS].append(processed_user_input)
    await update.message.reply_text("✅")
    return HANDLE_TAGS


async def finish_tags(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tags = context.user_data.get("tags", [])

    await update.message.reply_text(f"Tags collected: {', '.join(tags)}")

    reply_keyboard = [["Yes✅", "No❌"]]
    await update.message.reply_text(
        "Do you want to make this meme public?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Add tags?"
        ),
    )
    return DECIDE_PUBLIC_OR_NO

async def decide_public_or_no(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Yes✅":
        await update.message.reply_text("Your meme is public",
                                        reply_markup=ReplyKeyboardRemove())
        context.user_data[MEME_PUBLIC] = True
    else:
        await update.message.reply_text("Your meme is private",
                                        reply_markup=ReplyKeyboardRemove())
        context.user_data[MEME_PUBLIC] = False

    await handle_upload(update, context)

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    logger.info("User %s canceled the upload.", user.first_name)

    await update.message.reply_text(
        "Meme upload canceled", reply_markup=ReplyKeyboardRemove()
    )

    reset_current_upload_data(context.user_data)

    return ConversationHandler.END

async def command_in_wrong_place(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """sends message when user inputs wrong command"""
    user = update.message.from_user

    logger.info("User %s canceled the upload.", user.first_name)

    await update.message.reply_text(
        "Wrong command. Meme upload canceled", reply_markup=ReplyKeyboardRemove()
    )

    reset_current_upload_data(context.user_data)

    return ConversationHandler.END




async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query.query

    user_id = update.inline_query.from_user.id
    if not query:  # empty query should not be handled
        return

    processed_query = query.strip()
    db_response = await database.search_for_meme_inline_by_query(processed_query, user_id)
    results = await generate_inline_list(db_response)

    await update.inline_query.answer(results, cache_time=4)

async def user_get_memes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    memes = await database.get_all_user_memes(user_id)


    keyboard = await generate_inline_keyboard_page(memes, 0)
    context.user_data[LAST_SELECTED_PAGE] = 0
    context.user_data[MEMES_CONTROL_MESSAGE] = await update.message.reply_text("Choose meme:", reply_markup=keyboard)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    query_text = query.data
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    await query.answer()

    if query_text[:5] == "meme:":
        selected_meme = int(query_text[5:])
        meme = await database.get_meme_by_id_and_check_user(selected_meme, user_id)
        if meme:
            await delete_current_media_message(context=context, chat_id=chat_id)

            meme_controls = await generate_meme_controls(meme)

            if meme.media_type == MediaType.PHOTO:
                context.user_data[MEMES_CONTROL_MESSAGE] = await context.bot.sendPhoto(photo=meme.telegram_media_id, chat_id=chat_id, reply_markup=meme_controls)
            elif meme.media_type == MediaType.VIDEO:
                context.user_data[MEMES_CONTROL_MESSAGE] = await context.bot.sendVideo(video=meme.telegram_media_id, chat_id=chat_id, reply_markup=meme_controls)
            elif meme.media_type == MediaType.GIF:
                context.user_data[MEMES_CONTROL_MESSAGE] = await context.bot.sendAnimation(animation=meme.telegram_media_id, chat_id=chat_id, reply_markup=meme_controls)
            elif meme.media_type == MediaType.VOICE:
                context.user_data[MEMES_CONTROL_MESSAGE] = await context.bot.sendVoice(voice=meme.telegram_media_id, chat_id=chat_id, reply_markup=meme_controls)

    elif query_text[:5] == "page:":
        memes = await database.get_all_user_memes(user_id)
        selected_page = int(query_text[5:])
        context.user_data[LAST_SELECTED_PAGE] = selected_page
        keyboard = await generate_inline_keyboard_page(memes, selected_page)
        context.user_data[MEMES_CONTROL_MESSAGE] = await query.edit_message_text("Choose meme:", reply_markup=keyboard)

    elif query_text[:5] == "back":
        memes = await database.get_all_user_memes(user_id)
        selected_page = context.user_data.get(LAST_SELECTED_PAGE, 0)
        keyboard = await generate_inline_keyboard_page(memes, selected_page)

        await delete_current_media_message(context=context, chat_id=chat_id)

        context.user_data[MEMES_CONTROL_MESSAGE] = await context.bot.sendMessage(text="Choose meme:", chat_id=chat_id, reply_markup=keyboard)

    elif query_text[:5] == "delt:":
        meme_id = int(query_text[5:])
        meme = await database.get_meme_by_id_and_check_user(meme_id=meme_id, user_telegram_id=user_id)

        await delete_current_media_message(context=context, chat_id=chat_id)

        buttons = await generate_yes_no_for_meme_deletion(meme)
        meme_title = meme.title
        context.user_data[MEMES_CONTROL_MESSAGE] = await context.bot.sendMessage(text=f"Are you sure you want do delete meme: {meme_title}",
                                                                              reply_markup=buttons,
                                                                              chat_id=chat_id)

    elif query_text[:5] == "cdel:":
        meme_id = int(query_text[5:])
        await delete_current_media_message(context=context, chat_id=chat_id)
        successful = await database.delete_meme_check_and_check_user(meme_id=meme_id, user_telegram_id=user_id)
        if successful:
            await context.bot.sendMessage(text="Meme deleted", chat_id=chat_id)
        else:
            await context.bot.sendMessage(text="Something failed", chat_id=chat_id)






async def start_db(application: Application):
    await database.init_database()

async def stop_db(application: Application):
    await database.close_all_connections()

if __name__ == "__main__":
    logger.info("building")
    app = Application.builder().token(BOT_TOKEN).post_init(start_db).post_shutdown(stop_db).build()
    logger.info("adding commands")
    app.add_handler(CommandHandler('start', start_command),group=1)
    app.add_handler(CommandHandler("memes", user_get_memes), group=1)
    conv_handler = ConversationHandler(entry_points=[CommandHandler("add", add_command)],
                                       states={
                                           MEME: [MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.VOICE, upload_meme)],
                                           NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
                                           DECIDE_USE_TAGS_OR_NO: [MessageHandler(filters.Regex("^(Yes✅|No❌)$"),
                                                                                  decide_use_tags_or_no)],
                                           HANDLE_TAGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tags),
                                                         CommandHandler("finish_tags", finish_tags)],
                                           DECIDE_PUBLIC_OR_NO: [MessageHandler(filters.Regex("^(Yes✅|No❌)$"),
                                                                                  decide_public_or_no)]
                                       },
                                       fallbacks=[CommandHandler("cancel", cancel),
                                                  MessageHandler(filters.COMMAND, command_in_wrong_place)]
    )
    app.add_handler(conv_handler, group=0)

    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(CallbackQueryHandler(button))
    logger.info("polling")
    app.run_polling(allowed_updates=Update.ALL_TYPES)