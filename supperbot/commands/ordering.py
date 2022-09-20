"""Coroutines and helper functions relating to adding orders to existing jios."""

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Bot,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.constants import ParseMode
from telegram.ext import ConversationHandler, ContextTypes

from supperbot.db import db
from supperbot.enums import CallbackType, parse_callback_data, join

from supperbot.commands.helper import (
    update_consolidated_orders,
    format_order_message,
    order_message_keyboard_markup,
    update_individual_order,
)


async def interested_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Called when a user clicks "Add Order" deep link on a Supper Jio.

    This callback does a number of steps
    - Update the display name and chat id of the user so that their names will be
      displayed properly in consolidated order messages
    - Create a row in the `Order` database so they can add in their orders
    - Send a message to the user so that they can add in their orders
    """
    # TODO: Refactor out the getting of order id.
    jio_id = int(context.args[0][5:])

    # Update user display name and chat id
    db.upsert_user(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_chat.id,
    )

    # Create an `Order` row for the user
    db.create_order(jio_id=jio_id, user_id=update.effective_user.id)

    await format_and_send_user_orders(
        update.effective_user.id, update.effective_chat.id, jio_id, context.bot
    )


async def interested_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Same functionality as the `interested_user` coroutine, except this is for when
    the owner of a jio wants to add in their own orders.
    """
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])

    # Update user display name and chat id
    db.upsert_user(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_chat.id,
    )

    # Create an `Order` row for the user
    db.create_order(jio_id=jio_id, user_id=update.effective_user.id)

    await format_and_send_user_orders(
        update.effective_user.id, update.effective_chat.id, jio_id, context.bot
    )
    await query.answer()


async def format_and_send_user_orders(
    user_id: int,
    chat_id: int,
    jio_id: int,
    bot: Bot,
    *,
    remove_reply_markup: bool = False,
):
    # TODO: check if order even exists
    order = db.get_order(jio_id, user_id)

    message = format_order_message(order)
    keyboard = order_message_keyboard_markup(order)

    if remove_reply_markup:
        # Send a normal message to remove the Reply Keyboard,
        # then edit in the InlineKeyboard
        clear_msg = await bot.send_message(
            chat_id=chat_id,
            text="Please wait while the message loads...",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.HTML,
        )
        await clear_msg.delete()

    msg = await bot.send_message(
        chat_id=chat_id,
        text=message,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )
    db.update_order_message_id(order.jio.id, order.user_id, msg.message_id)


async def add_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback for when a user wishes to add an order to a jio.
    """
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    jio = db.get_jio(jio_id)

    if jio.is_closed():
        await query.answer("The jio is closed!")
        return

    # TODO: Maybe allow adding multiple orders at once using line breaks?
    message = (
        f"Adding order for Order #{jio.id} - {jio.restaurant}\n\n"
        f"Please type out a single order, or choose from your favourites below."
    )

    # Get all favourite orders
    favourite_orders = list(
        db.get_favourite_orders(update.effective_user.id, jio.restaurant)
    )

    markup = [["↩ Cancel"]]
    for i in range(0, len(favourite_orders), 2):
        # Chunk the favourites into lines of two
        markup.append(favourite_orders[i : i + 2])
    keyboard = ReplyKeyboardMarkup(markup, resize_keyboard=True)

    # Keep track of current order for the reply
    context.user_data["current_order"] = jio_id

    await update.effective_chat.send_message(text=message, reply_markup=keyboard)
    await query.answer()
    return CallbackType.CONFIRM_ORDER


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO: Investigate the error that occurs here for some reason - sometimes update.message == None
    food = update.message.text

    jio_id = context.user_data["current_order"]
    del context.user_data["current_order"]

    if food != "↩ Cancel":
        db.add_food_order(jio_id, update.effective_user.id, food)
        await update_consolidated_orders(context.bot, jio_id)

    await format_and_send_user_orders(
        update.effective_user.id,
        update.effective_chat.id,
        jio_id,
        context.bot,
        remove_reply_markup=True,
    )

    return ConversationHandler.END


async def delete_order(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback for when the user wishes to delete one food order
    """
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    jio_str = str(jio_id)

    # Check if jio is closed
    jio = db.get_jio(jio_id)

    if jio.is_closed():
        await query.answer("The jio is closed!")
        return

    # Obtain all user orders and display in a column
    text = "Please select which food order to delete:"
    order = db.get_order(jio_id, update.effective_user.id)

    keyboard = InlineKeyboardMarkup.from_column(
        [
            InlineKeyboardButton(
                "↩ Cancel",
                callback_data=join(CallbackType.CANCEL_ORDER_ACTION, jio_str),
            )
        ]
        # Use a list comprehension to generate the rest of the buttons
        # TODO: Create a next page functionality? Too many buttons can cause an error
        + [
            InlineKeyboardButton(
                food,
                callback_data=join(CallbackType.DELETE_ORDER_ITEM, jio_str, str(idx)),
            )
            for idx, food in enumerate(order.food_list)
        ]
    )

    await update.effective_message.edit_text(text, reply_markup=keyboard)
    await query.answer()


async def cancel_order_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    order = db.get_order(jio_id, update.effective_user.id)

    await update_individual_order(context.bot, order)
    await query.answer()


async def delete_order_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, jio_str, idx = parse_callback_data(query.data)
    order = db.get_order(int(jio_str), update.effective_user.id)

    # TODO: Low priority: Check if jio is closed. Typically message should be overriden
    #       But it's possible that someone send the message elsewhere

    db.delete_food_order(order, int(idx))

    await update_individual_order(context.bot, order)
    await query.answer()
    await update_consolidated_orders(context.bot, int(jio_str))


async def add_favourite_item(update: Update, _):
    query = update.callback_query
    jio_str = parse_callback_data(query.data)[1]
    jio_id = int(jio_str)
    jio = db.get_jio(jio_id)
    order = db.get_order(jio_id, update.effective_user.id)

    if not order.food_list:
        await update.effective_chat.send_message(
            "You have yet to make any order. "
            "Please add an order to choose a favourite item."
        )
        await query.answer()
        return

    # Obtain all user orders and display in a column
    text = (
        "Please select your current orders below to toggle between being in your "
        "favourites for this restaurant.\n\n"
        "Your favourite orders are saved per restaurant, and will be shown when you "
        "are adding an order for a jio to that restaurant.\n\n"
        "You can also view your favourites through /favourites.\n\n"
        "Orders which are already favourite'd are marked with a ⭐."
    )

    favourites = db.get_favourite_orders(update.effective_user.id, jio.restaurant)

    markup = [
        InlineKeyboardButton(
            "↩ Cancel",
            callback_data=join(CallbackType.CANCEL_ORDER_ACTION, jio_str),
        )
    ]

    for idx, food in enumerate(order.food_list):
        if food in favourites:
            row = InlineKeyboardButton(
                text="⭐ " + food,
                callback_data=join(
                    CallbackType.REMOVE_FAVOURITE_ITEM,
                    jio_str,
                    str(db.get_fav_id(update.effective_user.id, jio.restaurant, food)),
                ),
            )

        else:
            row = InlineKeyboardButton(
                text=food,
                callback_data=join(
                    CallbackType.CONFIRM_FAVOURITE_ITEM,
                    jio_str,
                    jio.restaurant,
                    str(idx),
                ),
            )

        markup.append(row)

    keyboard = InlineKeyboardMarkup.from_column(markup)

    await query.answer()
    await update.effective_message.edit_text(text, reply_markup=keyboard)


async def confirm_favourite_item(update: Update, _):
    query = update.callback_query
    _, jio_str, restaurant, idx_str = parse_callback_data(query.data)
    idx = int(idx_str)

    # Get food name
    jio_id = int(jio_str)
    order = db.get_order(jio_id, update.effective_user.id)
    food = order.food_list[idx]

    # Update database
    # TODO: What if too many - need check
    if not db.add_favourite_order(update.effective_user.id, restaurant, food):
        await update.effective_chat.send_message(
            "You have too many favourite items for this restaurant. "
            "Please remove some by going to /start and viewing your favourite orders."
        )
        return

    await add_favourite_item(update, _)


async def delete_favourite_item(update: Update, _):
    query = update.callback_query
    fav_id = int(parse_callback_data(query.data)[2])

    db.remove_favourite_order(fav_id, update.effective_user.id)
    await add_favourite_item(update, _)
