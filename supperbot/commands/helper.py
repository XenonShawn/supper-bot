from __future__ import annotations

import logging

from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.helpers import create_deep_linked_url

from supperbot import enums
from supperbot.enums import CallbackType, join
from supperbot.db import db
from supperbot.db.models import SupperJio, Order


def format_jio_message(jio: SupperJio) -> str:
    """Helper function to format the text for the jio messages."""

    message = (
        f"Supper Jio Order #{jio.id}: <b>{jio.restaurant}</b>\n"
        f"Additional Information: \n{jio.description}\n\n"
        "Current Orders:\n"
    )

    orders = db.get_list_complete_orders(jio.id)

    if not orders:
        # No orders yet
        return message + "None"

    for order in orders:
        temp = f"{order.user.display_name} -- " + "; ".join(order.food_list)

        if order.has_paid():
            temp = "<s>" + temp + "</s> Paid"

        message += temp + "\n"

    if jio.is_closed():
        message += "\n🛑 Jio is closed! 🛑"

    return message


#
# MAIN MESSAGE HELPER FUNCTIONS
#
# Main message being the control panel message sent to the jio host
#


def main_message_keyboard_markup(jio: SupperJio, bot: Bot) -> InlineKeyboardMarkup:
    jio_str = str(jio.id)

    if jio.is_closed():
        return InlineKeyboardMarkup.from_column(
            [
                InlineKeyboardButton(
                    "🔓 Reopen the jio",
                    callback_data=join(CallbackType.REOPEN_JIO, jio_str),
                ),
                InlineKeyboardButton(
                    "✍️Create Ordering List",
                    callback_data=join(CallbackType.CREATE_ORDERING_LIST, jio_str),
                ),
                InlineKeyboardButton(
                    "🔔 Ping Unpaid",
                    callback_data=join(CallbackType.PING_ALL_UNPAID, jio_str),
                ),
                InlineKeyboardButton(
                    "♻ Refresh Message",
                    callback_data=join(CallbackType.RESEND_MAIN_MESSAGE, jio_str),
                ),
            ],
        )

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📢 Share this Jio!", switch_inline_query=f"order{jio_str}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "Add Order",
                    callback_data=join(CallbackType.OWNER_ADD_ORDER, jio_str),
                ),
                InlineKeyboardButton(
                    "🔒 Close the Jio",
                    callback_data=join(CallbackType.CLOSE_JIO, jio_str),
                ),
            ],
            [
                InlineKeyboardButton(
                    "🗒️ Edit Description",
                    callback_data=join(CallbackType.AMEND_DESCRIPTION, jio_str),
                ),
                InlineKeyboardButton(
                    "♻ Refresh Message",
                    callback_data=join(CallbackType.RESEND_MAIN_MESSAGE, jio_str),
                ),
            ],
        ]
    )


async def update_main_jio_message(bot: Bot, jio: SupperJio, text: str = None):
    text = format_jio_message(jio) if text is None else text
    keyboard = main_message_keyboard_markup(jio, bot)

    try:
        await bot.edit_message_text(
            text,
            chat_id=jio.chat_id,
            message_id=jio.message_id,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )
    except BadRequest as e:
        logging.error(f"Unable to edit original jio message for order {jio.id}: {e}")


#
# SHARED MESSAGES HELPER FUNCTIONS
#
# ie Messages sent to group chats to jio people for supper
#


def shared_message_reply_markup(
    bot: Bot, jio: SupperJio
) -> InlineKeyboardMarkup | None:

    if jio.is_closed():
        return None

    return InlineKeyboardMarkup.from_button(
        InlineKeyboardButton(
            text="Add Order",
            url=create_deep_linked_url(bot.bot.username, f"order{jio.id}"),
        )
    )


async def update_shared_jio_message(
    bot: Bot,
    jio: SupperJio,
    message_id: str,
    text: str = None,
    reply_markup: InlineKeyboardMarkup = None,
):
    if text is None:
        text = format_jio_message(jio)

    if reply_markup is None:
        reply_markup = shared_message_reply_markup(bot, jio)

    try:
        await bot.edit_message_text(
            text,
            inline_message_id=message_id,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
    except BadRequest as e:
        # TODO: If fails, then remove the message from storage?
        logging.error(f"Unable to edit message with message_id {message_id}: {e}")


async def update_consolidated_orders(bot: Bot, jio_id: int) -> None:
    """
    Updates all messages that are used to consolidate supper orders,
    ie the one in the host DM and the group shared messages
    """

    jio = db.get_jio(jio_id)
    text = format_jio_message(jio)
    await update_main_jio_message(bot, jio, text)

    # Edit shared jio messages
    messages_to_edit = db.get_msg_id(jio_id)
    reply_markup = shared_message_reply_markup(bot, jio)

    for message_id in messages_to_edit:
        await update_shared_jio_message(bot, jio, message_id, text, reply_markup)


#
# INDIVIDUAL ORDER MESSAGE HELPER FUNCTIONS
#
# ie Messages sent to direct messages for each user to add in their order
#


def format_order_message(order: Order) -> str:
    jio = order.jio
    message = (
        f"Supper Jio Order #{jio.id}: <b>{jio.restaurant}</b>\n"
        f"Additional Information: \n{jio.description}\n\n"
        "Your Orders:\n"
    )

    message += "\n".join(order.food_list) if order.food_list else "None"

    if order.has_paid():
        message += "\n\n💰 You have declared payment! 💰"

    if jio.is_closed():
        message += "\n\n🛑 Jio is closed! 🛑"

    return message


def order_message_keyboard_markup(order: Order) -> InlineKeyboardMarkup | None:
    jio = order.jio
    jio_str = str(order.jio_id)

    if not jio.is_closed():
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "➕ Add Order",
                        callback_data=enums.join(CallbackType.ADD_ORDER, jio_str),
                    ),
                    InlineKeyboardButton(
                        "❌ Delete Order",
                        callback_data=enums.join(CallbackType.DELETE_ORDER, jio_str),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "⭐ Favourite Item",
                        callback_data=enums.join(CallbackType.FAVOURITE_ITEM, jio_str),
                    )
                ],
            ]
        )

    if not order.food_list:
        # User doesn't even have a food order. Don't let them declare payment.
        return None

    if order.has_paid():
        result = [
            InlineKeyboardButton(
                "Undo Payment Declaration",
                callback_data=join(CallbackType.UNDO_PAYMENT, jio_str),
            )
        ]
    else:
        result = [
            InlineKeyboardButton(
                "Declare Payment",
                callback_data=join(CallbackType.DECLARE_PAYMENT, jio_str),
            )
        ]

    result.append(
        InlineKeyboardButton(
            "⭐ Favourite Item",
            callback_data=enums.join(CallbackType.FAVOURITE_ITEM, jio_str),
        )
    )

    return InlineKeyboardMarkup.from_column(result)


async def update_individual_order(bot: Bot, order: Order) -> None:
    try:
        text = format_order_message(order)
        markup = order_message_keyboard_markup(order)

        await bot.edit_message_text(
            text,
            chat_id=order.user.chat_id,
            message_id=order.message_id,
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
        )
    except BadRequest as e:
        logging.error(
            f"Unable to edit individual order message for user {order.user}: {e}"
        )


async def update_individuals_order(bot: Bot, jio_id: int) -> None:
    """
    This coroutine updates all the individual message each user uses to add their
    food orders.
    """
    lst = db.get_list_all_orders(jio_id)

    for order in lst:
        await update_individual_order(bot, order)


async def update_all_jio_messages(bot: Bot, jio_id: int) -> None:
    await update_consolidated_orders(bot, jio_id)
    await update_individuals_order(bot, jio_id)
