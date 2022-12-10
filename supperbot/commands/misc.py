"""File containing coroutines that do not cleanly fit in other files"""
import logging

from telegram import Update
from telegram.ext import CallbackContext


async def not_implemented_callback(update: Update, _) -> None:
    query = update.callback_query
    await query.answer("This functionality is currently not implemented!")


async def unrecognized_callback(update: Update, _) -> None:
    await not_implemented_callback(update, _)
    logging.error(f"Unexpected callback data received: {update.callback_query.data}")


async def set_commands(context: CallbackContext) -> None:
    await context.bot.set_my_commands(
        [
            ("/start", "Start the bot"),
            ("/favourites", "View your favourite items for each restaurant"),
        ]
    )
    logging.info(f"Started as {context.bot.name}")
