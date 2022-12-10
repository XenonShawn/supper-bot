"""
Coroutines relating to payment of supper jios.
"""
import logging

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from supperbot.enums import parse_callback_data, PaidStatus
from supperbot.models import SupperJio, Order


# TODO: Needs rate limiting
async def ping_unpaid_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    jio = SupperJio.get_jio(jio_id)

    bot = context.bot

    pinged = []
    not_pinged = []

    for order in jio.orders:
        if order.has_paid():
            not_pinged.append(order.user.display_name)
        elif order.food:  # Need to check whether the user has even made an order
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
                await order.send_user_order(context.bot)
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


# TODO: Rate limit
async def declare_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO: Create something where the user has to declare how much they paid?
    # TODO: Check if user even has an order before declaring payment
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    jio = SupperJio.get_jio(jio_id)

    order = Order.create_order(jio_id=jio_id, user_id=update.effective_user.id)
    order.update(paid_status=PaidStatus.PAID)

    # TODO: Need to include try-excepts for all these awaits
    await update.effective_message.edit_reply_markup(None)

    # TODO: This spams the user a lot. Consider another way when improving this
    await order.send_user_order(context.bot)
    await query.answer()

    # Update all consolidated jio order messages, without updating other user's messages
    await jio.update_main_jio_message(context.bot)
    await jio.update_shared_jio_messages(context.bot)


async def undo_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    jio = SupperJio.get_jio(jio_id)

    order = Order.create_order(jio_id=jio_id, user_id=update.effective_user.id)
    order.update(paid_status=PaidStatus.NOT_PAID)

    await update.effective_message.edit_reply_markup(None)

    await order.send_user_order(context.bot)
    await query.answer()

    # Update all consolidated jio order messages, without updating other user's messages
    await jio.update_main_jio_message(context.bot)
    await jio.update_shared_jio_messages(context.bot)
