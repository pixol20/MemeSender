from collections.abc import Sequence
from typing import Final

from dotenv import load_dotenv
from os import getenv

from uuid import uuid4


from telegram import (Update,
                      ReplyKeyboardMarkup,
                      ReplyKeyboardRemove,
                      InlineQueryResultCachedVideo,
                      InlineQueryResultCachedPhoto,
                      InlineQueryResultCachedGif,
                      InlineQueryResultCachedVoice,
                      InlineQueryResultCachedAudio,
                      InlineQueryResult)

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    InlineQueryHandler
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

MEME, NAME, DECIDE_USE_TAGS_OR_NO, HANDLE_TAGS, DECIDE_PUBLIC_OR_NO = range(5)

# user_data keys
MEME_NAME = "meme_name"
MEDIA_TYPE = "media_type"
TELEGRAM_MEDIA_ID = "telegram_media_id"
DURATION = "duration"
TAGS = "tags"
MEME_PUBLIC = "meme_public"

MAX_TEXT_LENGTH = 512

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    success = await sqlalchemy_db.add_user_to_database(user_id)
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

    is_successful = await sqlalchemy_db.add_database_entry(user_id=user_id, telegram_media_id=user_data[TELEGRAM_MEDIA_ID],
                                                name=user_data[MEME_NAME], tags=user_data[TAGS],
                                                media_type=user_data[MEDIA_TYPE], duration=user_data[DURATION],
                                                is_public=user_data[MEME_PUBLIC])

    if is_successful:
        await update.message.reply_text("Meme uploaded")
    else:
        await update.message.reply_text("Something failed")

    reset_current_upload_data(user_data)
    return is_successful

async def meme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    media = None
    media_type = None
    duration = 0

    if message.photo:
        # Handle photos
        media = message.photo[-1]  # Highest resolution
        media_type = "photo"
    elif message.video:
        # Handle videos
        media = message.video
        media_type = "video"
        duration = media.duration
    elif message.animation:
        # Handle GIFs
        media = message.animation
        media_type = "gif"
        duration = media.duration
    elif message.voice:
        # Handle voice messages
        media = message.voice
        media_type = "voice"
        duration = media.duration

    elif message.audio:
        # Handle audio messages
        media = message.audio
        media_type = "audio"
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


async def _generate_inline_list(database_data: list[tuple[str, str, str]]) -> Sequence[InlineQueryResult]:
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

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query.query

    user_id = update.inline_query.from_user.id
    if not query:  # empty query should not be handled
        return

    processed_query = query.strip()
    db_response = await sqlalchemy_db.search_for_meme_inline_by_query(processed_query, user_id)
    results = await _generate_inline_list(db_response)

    await update.inline_query.answer(results, cache_time=4)

async def start_db(application: Application):
    await sqlalchemy_db.init_database()

async def stop_db(application: Application):
    await sqlalchemy_db.close_all_connections()

if __name__ == "__main__":
    logger.info("building")
    app = Application.builder().token(BOT_TOKEN).post_init(start_db).post_shutdown(stop_db).build()
    logger.info("adding commands")
    app.add_handler(CommandHandler('start', start_command),group=1)
    conv_handler = ConversationHandler(entry_points=[CommandHandler("add", add_command)],
                                       states={
                                           MEME: [MessageHandler(filters.PHOTO|filters.VIDEO|filters.AUDIO|filters.ANIMATION|filters.VOICE, meme)],
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
    logger.info("polling")
    app.run_polling(allowed_updates=Update.ALL_TYPES)