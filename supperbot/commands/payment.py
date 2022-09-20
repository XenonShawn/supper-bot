"""
This file contains the callbacks relating to the payment functionality of the bot.
"""

from telegram import Update
from telegram.ext import ContextTypes

from supperbot import enums
from supperbot.db import db
from supperbot.commands.ordering import format_and_send_user_orders
from supperbot.commands.helper import update_consolidated_orders


async def declare_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO: Create something where the user has to declare how much they paid?
    # TODO: Check if user even has an order before declaring payment
    query = update.callback_query
    jio_id = int(enums.parse_callback_data(query.data)[1])

    db.update_order_payment(jio_id, update.effective_user.id, db.PaidStatus.PAID)

    # TODO: Need to include try-excepts for all these awaits
    await update.effective_message.edit_reply_markup(None)

    # TODO: This spams the user a lot. Consider another way when improving this
    await format_and_send_user_orders(
        update.effective_user.id, update.effective_chat.id, jio_id, context.bot
    )
    await query.answer()

    await update_consolidated_orders(context.bot, jio_id)


async def undo_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    jio_id = int(enums.parse_callback_data(query.data)[1])

    db.update_order_payment(jio_id, update.effective_user.id, db.PaidStatus.NOT_PAID)

    await update.effective_message.edit_reply_markup(None)

    await format_and_send_user_orders(
        update.effective_user.id, update.effective_chat.id, jio_id, context.bot
    )
    await query.answer()

    await update_consolidated_orders(context.bot, jio_id)
