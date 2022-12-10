"""Coroutines and helper functions relating to creation of a supper jio"""

import logging

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes, ConversationHandler

from supperbot.enums import CallbackType, parse_callback_data
from supperbot.models import SupperJio


async def create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> CallbackType:
    """
    This coroutine is executed when a user decides to create a jio.
    """

    # TODO: Check that the user does not have a supper jio currently being created
    if context.user_data.get("create", False):
        pass

    # User is not currently creating an existing supper jio.
    context.user_data["create"] = True
    message = (
        "You are creating a new supper jio order."
        "Please select the restaurant you are ordering from, "
        "or type out the name of the restaurant.\n\n"
        "The name of the restaurant should not exceed 32 characters."
    )

    reply_markup = ReplyKeyboardMarkup(
        [["McDonalds", "Al Amaan"], ["↩ Cancel"]], resize_keyboard=True
    )

    await update.effective_chat.send_message(message, reply_markup=reply_markup)

    # Callback queries need to be answered,
    # even if no notification to the user is needed.
    await update.callback_query.answer()

    return CallbackType.ADDITIONAL_DETAILS


async def additional_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collection of additional details and description for the supper jio."""

    text = update.message.text

    if text == "↩ Cancel":
        await update.message.reply_text(
            "Supper Jio creation cancelled.", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    if len(text) > 32:
        await update.message.reply_text(
            "Restaurant name is too long. Please try again."
        )
        return

    restaurant = context.user_data["restaurant"] = text

    await update.effective_chat.send_message(
        f"You are creating a supper jio order for restaurant: <b>{restaurant}</b>\n\n"
        "Please type any additional information (eg. Delivery fees, close off timing, "
        "etc)",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML,
    )
    return CallbackType.FINISHED_CREATION


async def finished_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Presents the final jio text after finishing the initialisation process."""

    information = update.message.text
    jio = SupperJio.create(
        update.effective_user.id, context.user_data["restaurant"], information
    )

    msg = await update.effective_chat.send_message(
        text=jio.message, reply_markup=jio.keyboard_markup, parse_mode=ParseMode.HTML
    )
    jio.update(chat_id=msg.chat_id, message_id=msg.message_id)

    context.user_data["create"] = False

    return ConversationHandler.END


async def amend_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO: Prevent amending description too often
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    jio = context.user_data["jio"] = SupperJio.get_jio(jio_id)

    # Try removing the markup
    try:
        await update.effective_message.edit_reply_markup(None)
    except BadRequest as e:
        logging.error(
            f"Unable to edit markup for message {update.effective_message.id}: {e}"
        )

    message = (
        f"Editing description for <b>Order {jio.id}: {jio.restaurant}</b>.\n\n"
        f"Current description:\n{jio.description}"
    )

    msg = await update.effective_chat.send_message(
        text=message,
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                text="↩ Cancel",
                callback_data=CallbackType.CANCEL_AMEND_DESCRIPTION,
            )
        ),
        parse_mode=ParseMode.HTML,
    )
    context.user_data["amend_msg"] = msg

    await query.answer()
    return CallbackType.FINISH_AMEND_DESCRIPTION


async def finish_amend_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    information = update.message.text
    jio: SupperJio = context.user_data.pop("jio")
    jio.update(description=information)

    try:
        # Remove the "cancel" button from the previous message
        await context.user_data["amend_msg"].edit_reply_markup(None)
    except BadRequest as e:
        logging.error(f"Unable to edit amend message for jio {jio}: {e}")
    finally:
        del context.user_data["amend_msg"]

    # Update all messages related to the supper jio
    msg = await update.effective_chat.send_message(
        text=jio.message, reply_markup=jio.keyboard_markup, parse_mode=ParseMode.HTML
    )
    jio.update(chat_id=msg.chat_id, message_id=msg.message_id)
    await jio.update_individual_order_messages(context.bot)
    await jio.update_shared_jio_messages(context.bot)

    return ConversationHandler.END


async def cancel_amend_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jio: SupperJio = context.user_data.pop("jio")

    try:
        # Remove the "cancel" button from the previous message
        await context.user_data["amend_msg"].edit_reply_markup(None)
    except BadRequest as e:
        logging.error(f"Unable to edit amend message for jio {jio}: {e}")
    finally:
        del context.user_data["amend_msg"]

    msg = await update.effective_chat.send_message(
        text=jio.message, reply_markup=jio.keyboard_markup, parse_mode=ParseMode.HTML
    )
    jio.update(chat_id=msg.chat_id, message_id=msg.message_id)

    return ConversationHandler.END
