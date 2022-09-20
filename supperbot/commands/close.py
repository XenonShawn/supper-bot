"""
Coroutines for when the user decides to close a supper jio
"""
from collections import Counter
import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from supperbot.enums import parse_callback_data, join, CallbackType
from supperbot.db import db
from supperbot.commands.ordering import format_and_send_user_orders
from supperbot.commands.helper import update_all_jio_messages, update_main_jio_message


async def close_jio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])

    # TODO: Check if already closed. Possible if original message was duplicated
    db.update_jio_status(jio_id, db.Stage.CLOSED)
    await update_all_jio_messages(context.bot, jio_id)


async def reopen_jio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])

    db.update_jio_status(jio_id, db.Stage.CREATED)
    await update_all_jio_messages(context.bot, jio_id)


async def create_ordering_list(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])

    counter = Counter()
    for order in db.get_list_complete_orders(jio_id):
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
    jio = db.get_jio(jio_id)

    await update_main_jio_message(context.bot, jio)
    await query.answer()


async def ping_unpaid_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])

    bot = context.bot

    # TODO: Ensure a minimum timeframe before allowing to ping again?
    orders = db.get_list_all_orders(jio_id)

    pinged = []
    not_pinged = []

    for order in orders:
        if order.has_paid():
            not_pinged.append(order.user.display_name)
        elif order.food:
            try:
                await bot.edit_message_reply_markup(
                    order.user.chat_id, order.message_id, reply_markup=None
                )
            except BadRequest as e:
                logging.error(
                    f"Unable to edit message {order.message_id} for "
                    f"{order.user.display_name} (Chat id {order.user.chat_id}): {e}"
                )

            try:
                await bot.send_message(
                    order.user.chat_id, "Reminder to pay for your food!"
                )
                await format_and_send_user_orders(
                    order.user_id, order.user.chat_id, jio_id, bot
                )
            except BadRequest as e:
                logging.error(f"Unable to ping user {order.user.display_name}: {e}")
                not_pinged.append(
                    order.user.display_name + "(Error: Unable to send message)"
                )
            else:
                pinged.append(order.user.display_name)

    await query.answer()

    text = "Pinged users:\n"
    text += "\n".join(pinged) or "None"
    text += "\n\nUsers not pinged:\n"
    text += "\n".join(not_pinged) or "None"
    await update.effective_chat.send_message(text)
