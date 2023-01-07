"""Coroutines and helper functions relating to adding orders to existing jios."""

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import ApplicationHandlerStop, ContextTypes, ConversationHandler

from supperbot.enums import CallbackType, parse_callback_data, join, extract_jio_number
from supperbot.models import SupperJio, User, Order, FavouriteOrder


@User.initialize_user
async def interested_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Called when a user clicks "Add Order" deep link on a Supper Jio.

    This callback does a number of steps
    - Update the display name and chat id of the user so that their names will be
      displayed properly in consolidated order messages
    - Create a row in the `Order` database so they can add in their orders
    - Send a message to the user so that they can add in their orders
    """
    jio_id = extract_jio_number(context.args[0])
    user = User.get_user(update.effective_user.id)

    order = Order.create_order(SupperJio.get_jio(jio_id), user)

    await order.send_user_order(context.bot)
    raise ApplicationHandlerStop  # Do not trigger the other /start commands


@User.initialize_user
async def interested_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Same functionality as the `interested_user` coroutine, except this is for when
    the owner of a jio wants to add in their own orders.
    """
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])

    user = User.get_user(update.effective_user.id)

    order = Order.create_order(SupperJio.get_jio(jio_id), user)
    await order.send_user_order(context.bot)
    await query.answer()


async def add_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback for when a user wishes to add an order to a jio.
    """
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    jio = SupperJio.get_jio(jio_id)

    if jio.is_closed():
        await query.answer("The jio is closed!")
        return

    # TODO: Maybe allow adding multiple orders at once using line breaks?
    message = (
        f"Adding order for Order #{jio.id} - {jio.restaurant}\n\n"
        f"Please type out a single order, or choose from your favourites below."
    )

    # Get all favourite orders
    favourite_orders = [
        fav.food
        for fav in User.get_user(update.effective_user.id).favourite_orders
        if fav.restaurant == jio.restaurant
    ]
    markup = [["↩ Cancel"]]
    for i in range(0, len(favourite_orders), 2):
        # Chunk the favourites into lines of two
        markup.append(favourite_orders[i : i + 2])
    keyboard = ReplyKeyboardMarkup(markup, resize_keyboard=True)

    # Keep track of current order for the reply
    context.user_data["current_jio"] = jio

    await update.effective_chat.send_message(text=message, reply_markup=keyboard)
    await query.answer()
    return CallbackType.CONFIRM_ORDER


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO: Investigate the error that occurs here for some reason - sometimes
    #       update.message == None
    food = update.message.text

    jio: SupperJio = context.user_data.pop("current_jio")
    user = User.get_user(update.effective_user.id)
    order = Order.create_order(jio, user)

    if food != "↩ Cancel":
        order.add_food(food)
        await jio.update_main_jio_message(context.bot)
        await jio.update_shared_jio_messages(context.bot)

    await order.send_user_order(context.bot, remove_reply_markup=True)

    return ConversationHandler.END


async def delete_order(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback for when the user wishes to delete one food order
    """
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    jio_str = str(jio_id)

    # Check if jio is closed
    jio = SupperJio.get_jio(jio_id)
    if jio.is_closed():
        await query.answer("The jio is closed!")
        return

    # Obtain all user orders and display in a column
    text = "Please select which food order to delete:"
    order = Order.create_order(jio, User.get_user(update.effective_user.id))

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


async def cancel_order_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Cancel deletion of a food order.
    """
    query = update.callback_query
    jio_id = int(parse_callback_data(query.data)[1])
    jio = SupperJio.get_jio(jio_id)

    order = Order.create_order(jio, User.get_user(update.effective_user.id))

    await order.update_user_order(context.bot)
    await query.answer()


async def delete_order_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, jio_str, idx = parse_callback_data(query.data)

    jio = SupperJio.get_jio(int(jio_str))
    order = Order.create_order(jio, User.get_user(update.effective_user.id))

    if jio.is_closed():
        await query.answer("The jio is closed!")
        return

    order.delete_food(int(idx))

    await order.update_user_order(context.bot)
    await jio.update_main_jio_message(context.bot)
    await jio.update_shared_jio_messages(context.bot)

    # TODO: Consider putting result of deletion into query?
    await query.answer()


async def add_favourite_item(update: Update, _):
    query = update.callback_query
    jio_str = parse_callback_data(query.data)[1]
    jio_id = int(jio_str)

    user = User.get_user(update.effective_user.id)
    jio = SupperJio.get_jio(jio_id)
    order = Order.create_order(jio, user)

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
        "Your favourite orders are saved on a per-restaurant basis, and will be shown"
        "when you are adding an order for a jio to that restaurant.\n\n"
        "You can also view your favourites through /favourites.\n\n"
        "Orders which are already favourite'd are marked with a ⭐."
    )

    # Map the favourite food to its respective id in the database for ease of deletion
    # later below
    favourites = {
        favFood.food: favFood.id for favFood in user.get_favourite_foods(jio.restaurant)
    }

    markup = [
        InlineKeyboardButton(
            "↩ Cancel",
            callback_data=join(CallbackType.CANCEL_ORDER_ACTION, jio_str),
        )
    ]

    for idx, food in enumerate(order.food_list):
        # If food is already a favourite food, then clicking it should unfavourite it
        if food in favourites:
            row = InlineKeyboardButton(
                text="⭐ " + food,
                callback_data=join(
                    CallbackType.REMOVE_FAVOURITE_ITEM, jio_str, str(favourites[food])
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

    jio = SupperJio.get_jio(int(jio_str))
    user = User.get_user(update.effective_user.id)
    order = Order.create_order(jio, user)

    # Get food name
    food = order.food_list[int(idx_str)]

    # Update database
    # TODO: What if too many - need check
    if not FavouriteOrder.create(user, restaurant, food):
        await update.effective_chat.send_message(
            "You have too many favourite items for this restaurant. "
            "Please remove some by going to /start and viewing your favourite orders."
        )
        return

    await add_favourite_item(update, _)


async def delete_favourite_item(update: Update, _):
    query = update.callback_query
    fav_id = int(parse_callback_data(query.data)[2])

    FavouriteOrder.delete(fav_id, update.effective_user.id)
    await add_favourite_item(update, _)
