from typing import Final
# user_data keys
MEME_NAME: Final[str] = "meme_name"
MEDIA_TYPE: Final[str]  = "media_type"
TELEGRAM_MEDIA_ID: Final[str]  = "telegram_media_id"
DURATION: Final[str]  = "duration"
TAGS: Final[str]  = "tags"
MEME_PUBLIC: Final[str]  = "meme_public"
RENAMING_MEME_ID: Final[str] = "renaming_meme_id"

# Message from bot that contains memes created by user.
MEMES_CONTROL_MESSAGE: Final[str]  = "memes_control_message"
MEME_MEDIA_MESSAGE: Final[str]  = "meme_media_message"

LAST_SELECTED_PAGE: Final[str]  = "last_selected_page"

MEMES_PER_PAGE = 10

# callback data
CALLBACK_MEME: Final[str] = "meme:"
CALLBACK_PAGE: Final[str] = "page:"
CALLBACK_RENAME: Final[str] = "rnme:"
CALLBACK_DELETE: Final[str] = "delt:"
CALLBACK_BACK: Final[str] = "back:"
CALLBACK_CONFIRM_DELETE: Final[str] = "cdel:"

