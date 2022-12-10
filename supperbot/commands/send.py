"""Coroutines and helper functions relating to sharing of a supper jio"""

import logging

from telegram import (
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from sqlalchemy.exc import NoResultFound

from supperbot.enums import parse_callback_data, extract_jio_number
from supperbot.models import SupperJio, Message


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the inline queries from sharing jios."""

    query = update.inline_query.query
    logging.debug("Received an inline query: " + query)

    jio_id = extract_jio_number(query)
    if jio_id is None:
        return

    # Check if the order id is valid
    try:
        jio = SupperJio.get_jio(jio_id)
    except NoResultFound:
        jio = None

    # Check if the user is the owner of the jio
    if jio is None or jio.owner_id != update.effective_user.id:
        await update.inline_query.answer([])
        return

    results = [
        InlineQueryResultArticle(
            id=f"order{jio.id}",
            title=f"Order {jio.id}",
            description=f"Jio for {jio.restaurant}",
            input_message_content=InputTextMessageContent(
                jio.message, parse_mode=ParseMode.HTML
            ),
            reply_markup=jio.shared_message_reply_markup(context.bot),
        )
    ]

    await update.inline_query.answer(results)
    return

    # TODO: Originally, this code allowed for searching if the search string starts with
    #       "order" but not have a number. Possible feature for the future, but not impt

    # # An order id is not provided
    # jios = db.get_user_jios(update.effective_user.id)
    #
    # results = [
    #     InlineQueryResultArticle(
    #         id=f"order{jio.id}",
    #         title=f"Order {jio.id}",
    #         description=f"Jio for {jio.restaurant}",
    #         input_message_content=InputTextMessageContent(
    #             format_jio_message(jio), parse_mode=ParseMode.HTML
    #         ),
    #         reply_markup=InlineKeyboardMarkup.from_button(
    #             InlineKeyboardButton(
    #                 text="➕ Add Order",
    #                 url=create_deep_linked_url(context.bot.username, f"order{jio.id}"),
    #             )
    #         ),
    #     )
    #     for jio in jios
    # ]
    #
    # await update.inline_query.answer(results)
    # return


async def shared_jio(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Updates the database with the new message id after a jio has been shared to a group.
    """

    chosen_result = update.chosen_inline_result
    jio_id = extract_jio_number(chosen_result.result_id)
    msg_id = chosen_result.inline_message_id
    Message.create(jio_id, msg_id)


async def resend_main_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Resend the owner's jio message so that it'll be at the bottom of the chat.
    """

    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    jio = SupperJio.get_jio(jio_id)

    # Try editing the previous main message
    try:
        await update.effective_message.edit_reply_markup(None)
    except BadRequest as e:
        logging.error(f"Unable to edit main message for jio {jio}: {e}")

    await query.answer()

    msg = await update.effective_chat.send_message(
        text=jio.message, reply_markup=jio.keyboard_markup, parse_mode=ParseMode.HTML
    )
    jio.update(chat_id=msg.chat_id, message_id=msg.message_id)
