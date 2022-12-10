"""File containing the start and help commands for the bot"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from supperbot.enums import CallbackType
from supperbot.models import User


async def help_command(update: Update, _) -> None:
    """Send a message when the command /help is issued."""
    await update.effective_chat.send_message(text="Use /start to use this bot!")


async def start_group(update: Update, _) -> None:
    """Send a message when the command /start is issued, but not in a DM."""
    await update.effective_chat.send_message(
        text="Please initialize me in direct messages!"
    )


@User.initialize_user
async def start(update: Update, _) -> None:
    message = (
        "Welcome to the Supper Jio bot!\n\n"
        "Just click the buttons below to create a supper jio!"
    )

    reply_markup = InlineKeyboardMarkup.from_column(
        [
            InlineKeyboardButton(
                "🆕 Create Supper Jio", callback_data=CallbackType.CREATE_JIO
            ),
            InlineKeyboardButton(
                "📖 View Your Created Jios", callback_data=CallbackType.VIEW_CREATED_JIOS
            ),
            InlineKeyboardButton(
                "📑 View Joined Jios", callback_data=CallbackType.VIEW_JOINED_JIOS
            ),
            InlineKeyboardButton(
                "🍿 View Favourite Items",
                callback_data=CallbackType.MAIN_MENU_FAVOURITES,
            ),
        ]
    )

    await update.effective_chat.send_message(text=message, reply_markup=reply_markup)
