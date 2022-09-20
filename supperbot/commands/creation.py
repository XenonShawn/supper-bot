"""Coroutines and helper functions relating to creation and sharing of a supper jio"""
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes, ConversationHandler
from telegram.helpers import create_deep_linked_url

from sqlalchemy.exc import NoResultFound

from supperbot.db import db
from supperbot.enums import CallbackType, parse_callback_data
from supperbot.commands.helper import (
    format_jio_message,
    main_message_keyboard_markup,
    update_consolidated_orders,
)


async def create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> CallbackType:
    """Main command for creating a new jio."""

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

    # TODO: Abstract out the following to a separate method call
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
        "Please type any additional information (eg. Delivery fees, close off timing, etc)",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML,
    )
    return CallbackType.FINISHED_CREATION


async def finished_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Presents the final jio text after finishing the initialisation process."""

    information = update.message.text
    jio = db.create_jio(
        update.effective_user.id, context.user_data["restaurant"], information
    )

    # TODO: The following part is repeated in `resend_main_message`. Maybe refactor?
    message = format_jio_message(jio)
    keyboard = main_message_keyboard_markup(jio, context.bot)

    msg = await update.effective_chat.send_message(
        text=message, reply_markup=keyboard, parse_mode=ParseMode.HTML
    )
    db.update_jio_message_id(jio.id, msg.chat_id, msg.message_id)

    context.user_data["create"] = False

    return ConversationHandler.END


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the inline queries from sharing jios."""

    query = update.inline_query.query
    logging.debug("Received an inline query: " + query)

    if query == "" or not query.startswith("order"):
        await update.inline_query.answer([])
        return

    # TODO: Abstract out this part
    order_id_str = query[5:]

    if order_id_str:
        # An order id is provided

        order_id = int(query[5:])

        # Check if the order id is valid
        try:
            jio = db.get_jio(order_id)
        except NoResultFound:
            jio = None

        if jio is None or jio.owner_id != update.effective_user.id:
            await update.inline_query.answer([])
            return

        # User owns the supper jio
        deep_link = create_deep_linked_url(context.bot.username, f"order{order_id}")

        results = [
            InlineQueryResultArticle(
                id=f"order{jio.id}",
                title=f"Order {jio.id}",
                description=f"Jio for {jio.restaurant}",
                input_message_content=InputTextMessageContent(
                    format_jio_message(jio), parse_mode=ParseMode.HTML
                ),
                reply_markup=InlineKeyboardMarkup.from_button(
                    InlineKeyboardButton(text="➕ Add Order", url=deep_link)
                ),
            )
        ]

        await update.inline_query.answer(results)
        return

    # An order id is not provided
    jios = db.get_user_jios(update.effective_user.id)

    results = [
        InlineQueryResultArticle(
            id=f"order{jio.id}",
            title=f"Order {jio.id}",
            description=f"Jio for {jio.restaurant}",
            input_message_content=InputTextMessageContent(
                format_jio_message(jio), parse_mode=ParseMode.HTML
            ),
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    text="➕ Add Order",
                    url=create_deep_linked_url(context.bot.username, f"order{jio.id}"),
                )
            ),
        )
        for jio in jios
    ]

    await update.inline_query.answer(results)
    return


async def shared_jio(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Updates the database with the new message id after a jio has been shared to a group.
    """

    chosen_result = update.chosen_inline_result

    # TODO: Abstract this part
    jio_id = int(chosen_result.result_id[5:])
    msg_id = chosen_result.inline_message_id

    db.new_msg(jio_id, msg_id)


async def resend_main_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:

    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    jio = db.get_jio(jio_id)

    # Try editing the previous main message
    try:
        await update.effective_message.edit_reply_markup(None)
    except BadRequest as e:
        logging.error(f"Unable to edit main message for jio {jio}: {e}")

    message = format_jio_message(jio)
    keyboard = main_message_keyboard_markup(jio, context.bot)

    await query.answer()

    msg = await update.effective_chat.send_message(
        text=message, reply_markup=keyboard, parse_mode=ParseMode.HTML
    )
    db.update_jio_message_id(jio.id, msg.chat_id, msg.message_id)


async def amend_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    jio = context.user_data["jio"] = db.get_jio(jio_id)

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
    jio = context.user_data["jio"]
    del context.user_data["jio"]

    db.edit_jio_description(jio, information)

    # TODO: Copied from `resend_main_message`. Try and refactor
    # Try editing the previous main message
    try:
        await context.user_data["amend_msg"].edit_reply_markup(None)
        del context.user_data["amend_msg"]
    except BadRequest as e:
        logging.error(f"Unable to edit amend message for jio {jio}: {e}")

    message = format_jio_message(jio)
    keyboard = main_message_keyboard_markup(jio, context.bot)

    msg = await update.effective_chat.send_message(
        text=message, reply_markup=keyboard, parse_mode=ParseMode.HTML
    )
    db.update_jio_message_id(jio.id, msg.chat_id, msg.message_id)

    # TODO: `update_consolidated_orders` tries to edit the host's jio message too.
    #       Maybe consider refactoring? Else will throw error in logs
    await update_consolidated_orders(context.bot, jio.id)

    return ConversationHandler.END


async def cancel_amend_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jio = context.user_data["jio"]
    del context.user_data["jio"]

    # TODO: Copied from `resend_main_message`. Try and refactor
    # Try editing the previous main message
    try:
        await context.user_data["amend_msg"].edit_reply_markup(None)
        del context.user_data["amend_msg"]
    except BadRequest as e:
        logging.error(f"Unable to edit amend message for jio {jio}: {e}")

    message = format_jio_message(jio)
    keyboard = main_message_keyboard_markup(jio, context.bot)

    msg = await update.effective_chat.send_message(
        text=message, reply_markup=keyboard, parse_mode=ParseMode.HTML
    )
    db.update_jio_message_id(jio.id, msg.chat_id, msg.message_id)
    return ConversationHandler.END
