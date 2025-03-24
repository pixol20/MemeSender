from typing import Final

from dotenv import load_dotenv
from os import getenv



from telegram import (Update,
                      ReplyKeyboardMarkup,
                      ReplyKeyboardRemove)

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import logging
import database

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN: Final = getenv("BOT_KEY")
BOT_USERNAME: Final = getenv("BOT_NAME")

MEME, NAME, DECIDE_USE_TAGS_OR_NO, HANDLE_TAGS = range(4)

# user_data keys
MEME_NAME = "meme_name"
MEDIA_TYPE = "meme_type"
TELEGRAM_MEDIA_ID = "telegram_media_id"
LENGTH = "length"
TAGS = "tags"


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello World")

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompts user to send meme"""
    await update.message.reply_text("Send your meme")
    return MEME

def reset_current_upload_data(user_data):
    user_data[TELEGRAM_MEDIA_ID] = None
    user_data[MEME_NAME] = None
    user_data[TAGS] = None
    user_data[MEDIA_TYPE] = None
    user_data[LENGTH] = None

async def handle_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_data = context.user_data
    user_id = update.message.from_user.id

    length = 0
    if user_data[MEDIA_TYPE] == "video":
        length = user_data.get(LENGTH, 0)

    is_successful = database.add_database_entry(user_id=user_id, telegram_media_id=user_data[TELEGRAM_MEDIA_ID],
                                name=user_data[MEME_NAME], tags=user_data[TAGS],
                                media_type=user_data[MEDIA_TYPE], length=length,
                                is_public=True)

    if is_successful:
        await update.message.reply_text("Meme uploaded")
    else:
        await update.message.reply_text("Something failed")

    reset_current_upload_data(user_data)
    return is_successful

async def meme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        context.user_data[MEDIA_TYPE] = "image"
        context.user_data[TELEGRAM_MEDIA_ID] = photo_file.file_id

    elif update.message.video:
        video_file = await update.message.video.get_file()
        context.user_data[MEDIA_TYPE] = "video"
        context.user_data[TELEGRAM_MEDIA_ID] = video_file.file_id
        context.user_data[LENGTH] = update.message.video.duration

    await update.message.reply_text("Name your meme")
    return NAME

async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user

    context.user_data[MEME_NAME] = update.message.text

    reply_keyboard = [["Yes✅","No❌"]]
    await update.message.reply_text(
        "Do you want to add tags that help to search it later?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Add tags?"
        ),
    )
    return DECIDE_USE_TAGS_OR_NO



async def decide_use_tags_or_no(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    user_data[TAGS] = []

    if update.message.text == "Yes✅":
        await update.message.reply_text("Input tags one per message, /finish_tags to finish",
                                        reply_markup=ReplyKeyboardRemove())
        return HANDLE_TAGS
    else:
        user_id = update.message.from_user.id

        await update.message.reply_text("Uploading meme")
        logger.info("User %s uploading meme: %s", update.message.from_user.first_name, user_data[MEME_NAME])

        await handle_upload(update, context)

        return ConversationHandler.END


async def handle_tags(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text
    processed_user_input = user_input.strip().lower()
    context.user_data[TAGS].append(processed_user_input)
    await update.message.reply_text("✅")
    return HANDLE_TAGS


async def finish_tags(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tags = context.user_data.get("tags", [])

    await update.message.reply_text(f"Tags collected: {', '.join(tags)}")
    await update.message.reply_text("Uploading meme")

    logger.info("User %s uploading meme: %s", update.message.from_user.first_name,
                context.user_data[MEME_NAME])

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
    user = update.message.from_user

    logger.info("User %s canceled the upload.", user.first_name)

    await update.message.reply_text(
        "Wrong command. Meme upload canceled", reply_markup=ReplyKeyboardRemove()
    )

    reset_current_upload_data(context.user_data)

    return ConversationHandler.END

if __name__ == "__main__":
    logger.info("building")
    app = Application.builder().token(BOT_TOKEN).build()

    logger.info("adding commands")
    app.add_handler(CommandHandler('start', start_command),group=1)
    conv_handler = ConversationHandler(entry_points=[CommandHandler("add", add_command)],
                                       states={
                                           MEME: [MessageHandler(filters.PHOTO|filters.VIDEO, meme)],
                                           NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
                                           DECIDE_USE_TAGS_OR_NO: [MessageHandler(filters.Regex("^(Yes✅|No❌)$"),
                                                                                  decide_use_tags_or_no)],
                                           HANDLE_TAGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tags),
                                                         CommandHandler("finish_tags", finish_tags)]
                                       },
                                       fallbacks=[CommandHandler("cancel", cancel),
                                                  MessageHandler(filters.COMMAND, command_in_wrong_place)]
    )
    app.add_handler(conv_handler, group=0)
    logger.info("polling")
    app.run_polling(allowed_updates=Update.ALL_TYPES)