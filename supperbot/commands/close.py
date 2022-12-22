"""
Coroutines for when the supper host decides to close a supper jio
"""
from collections import Counter
from dataclasses import dataclass, field
import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Message
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes, ConversationHandler

from supperbot.checks import delayed_cooldown
from supperbot.commands.send import resend_main_message
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


async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    jio = SupperJio.get_jio(jio_id)

    if BroadcastInformation in context.user_data:
        context.user_data.pop(BroadcastInformation)

    await jio.update_main_jio_message(context.bot)
    await query.answer()
    return ConversationHandler.END


@dataclass
class BroadcastInformation:
    """
    Helper class to consolidate the information required to broadcast a message.
    """

    jio_id: int
    broadcast_request_message: Message
    to_forward: Message = field(default=None)


@delayed_cooldown(2, 60)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])

    text = (
        "Please send a message or an image which you wish to broadcast to all users who"
        "have yet to pay. Note that you can only do this <b>twice a minute</b>."
    )
    keyboard = InlineKeyboardMarkup.from_button(
        InlineKeyboardButton(
            "Back",
            callback_data=join(CallbackType.BACK, str(jio_id)),
        )
    )

    context.user_data[BroadcastInformation] = BroadcastInformation(
        jio_id, update.effective_message
    )

    await update.effective_message.edit_text(
        text, reply_markup=keyboard, parse_mode=ParseMode.HTML
    )
    await query.answer()
    return CallbackType.AWAIT_MESSAGE


async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    broadcast_info: BroadcastInformation = context.user_data[BroadcastInformation]
    try:
        await broadcast_info.broadcast_request_message.edit_reply_markup(None)
    except BadRequest as e:
        logging.error(f"Unable to edit broadcast message: {e}")

    text = (
        "Are you sure this message should be sent to <b>everyone who has yet to pay</b>"
        "? This feature can only be used <b>twice a minute</b>."
    )
    broadcast_info.to_forward = update.effective_message
    jio_str = str(broadcast_info.jio_id)

    keyboard = InlineKeyboardMarkup.from_column(
        [
            InlineKeyboardButton(
                "Yes", callback_data=join(CallbackType.CONFIRM_SEND, jio_str)
            ),
            InlineKeyboardButton(
                "No",
                callback_data=join(CallbackType.BROADCAST_END, jio_str),
            ),
        ]
    )

    await update.effective_message.reply_html(text, reply_markup=keyboard, quote=True)
    return CallbackType.CONFIRM_SEND


async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert broadcast.uses_remaining(update.effective_user.id) > 0

    broadcast.add_cooldown(update.effective_user.id)
    broadcast_info: BroadcastInformation = context.user_data[BroadcastInformation]
    jio = SupperJio.get_jio(broadcast_info.jio_id)

    assert jio.owner_id == update.effective_user.id

    sent = []
    paid = []
    error = []

    for order in jio.orders:
        if order.food:
            if order.has_paid():
                paid.append(order.user.display_name)
                continue

            try:
                await broadcast_info.to_forward.forward(order.user.chat_id)
                sent.append(order.user.display_name)
            except BadRequest as e:
                error.append(order.user.display_name)
                logging.error(f"Unable to forward message for jio {jio.id}: {e}")

    text = (
        "Sent to these people:\n"
        + ("\n".join(sent) or "None")
        + "\n\nThese people have already paid:\n"
        + ("\n".join(paid) or "None")
    )

    if error:
        text += (
            "\n\nUnable to send to these people due to an error, please send "
            "manually:\n " + ("\n".join(error) or "None")
        )

    await update.effective_chat.send_message(text)

    return await end_broadcast(update, context)


async def end_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await resend_main_message(update, context)
    if BroadcastInformation in context.user_data:
        context.user_data.pop(BroadcastInformation)
    return ConversationHandler.END
