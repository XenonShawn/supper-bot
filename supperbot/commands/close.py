"""
Coroutines for when the supper host decides to close a supper jio
"""
from collections import Counter

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from supperbot.enums import parse_callback_data, join, CallbackType, Stage
from supperbot.models import SupperJio


# TODO: Rate limit this function
async def close_jio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    jio = SupperJio.get_jio(jio_id)

    if jio.is_closed():
        await query.answer("Jio is already closed.")
        return

    jio.update(status=Stage.CLOSED)
    await jio.update_all_jio_messages(context.bot)
    await query.answer("Jio has been closed!")


# TODO: Rate limit this
async def reopen_jio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    jio = SupperJio.get_jio(jio_id)

    if not jio.is_closed():
        await query.answer("Jio is already opened.")
        return

    jio.update(status=Stage.CREATED)
    await jio.update_all_jio_messages(context.bot)
    await query.answer("Jio has been opened!")


async def create_ordering_list(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    jio = SupperJio.get_jio(jio_id)

    counter = Counter()
    for order in jio.orders:
        # Reduce to lower case so that we can match similar orders

        # TODO: Create a way to combine two different orders together for convenience
        #       eg so can combine "m fries" and "medium fries" together
        counter.update(map(str.lower, order.food_list))

    text = "Orders:\n\n"

    text += "\n".join(f"{k}: {v}" for k, v in counter.items())

    keyboard = InlineKeyboardMarkup.from_button(
        InlineKeyboardButton("Back", callback_data=join(CallbackType.BACK, str(jio_id)))
    )

    await update.effective_message.edit_text(text, reply_markup=keyboard)
    await query.answer()


async def back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    jio = SupperJio.get_jio(jio_id)

    await jio.update_main_jio_message(context.bot)
    await query.answer()
