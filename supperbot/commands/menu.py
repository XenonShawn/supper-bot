import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import InlineKeyboardMarkupLimit, ParseMode
from telegram.error import BadRequest

from supperbot.commands.start import start
from supperbot.enums import CallbackType, join, parse_callback_data
from supperbot.models import User, FavouriteOrder


async def view_created_jios(update: Update, _) -> None:
    """
    Present to the user a list of Supper Jios that they have created.

    Accessible through the main menu using the /start command.
    """

    query = update.callback_query
    user = User.get_user(update.effective_user.id)

    # TODO: Create a next page functionality for the buttons so that more can be viewed
    # Telegram has a limitation on how many buttons there can be. Currently, it's 100.
    # However, 100 buttons is still too many. Right now the limit is 50.
    jios = user.get_created_jios(
        limit=min(50, InlineKeyboardMarkupLimit.TOTAL_BUTTON_NUMBER - 1),
        allow_closed=True,
    )

    if not jios:
        # User has not created any jios
        await update.effective_chat.send_message(text="You have not created any jios.")
        await query.answer()
        return

    text = (
        "Which of your jios do you want to view?\n"
        "Only the most recent 50 jios can be viewed."
    )

    keyboard = InlineKeyboardMarkup.from_column(
        [InlineKeyboardButton("↩ Cancel", callback_data=CallbackType.CANCEL_VIEW)]
        # Use a list comprehension to generate the rest of the buttons
        + [
            InlineKeyboardButton(
                str(jio),
                callback_data=join(CallbackType.RESEND_MAIN_MESSAGE, str(jio.id)),
            )
            for jio in jios
        ]
    )

    await update.effective_chat.send_message(text, reply_markup=keyboard)
    await query.answer()


async def cancel_view(update: Update, _) -> None:
    # Try removing the message
    try:
        await update.effective_message.edit_reply_markup(None)
    except BadRequest as e:
        logging.error(f"Unable to cancel view past messages: {e}")

    await start(update, _)


async def view_joined_jios(update: Update, _) -> None:
    """
    Present to the user a list of Supper Jios that they have participated in.

    Accessible through the main menu using the /start command.
    """

    query = update.callback_query
    user = User.get_user(update.effective_user.id)

    # TODO: Create a next page functionality for the buttons so that more can be viewed
    # Telegram has a limitation on how many buttons there can be. Currently, it's 100.
    # However, 100 buttons is still too many. Right now the limit is 50.
    # TODO: Maybe consider only showing orders that the user has ordered something?
    jios = user.get_joined_jios(
        limit=min(50, InlineKeyboardMarkupLimit.TOTAL_BUTTON_NUMBER - 1),
    )

    if not jios:
        # User has not created any jios
        await update.effective_chat.send_message(text="You have not joined any jios.")
        await query.answer()
        return

    text = (
        "Which of the jios do you want to view?\n"
        "Only the most recent 50 jios can be viewed."
    )

    keyboard = InlineKeyboardMarkup.from_column(
        [InlineKeyboardButton("↩ Cancel", callback_data=CallbackType.CANCEL_VIEW)]
        # Use a list comprehension to generate the rest of the buttons
        + [
            InlineKeyboardButton(
                str(jio),
                # TODO: `OWNER_ADD_ORDER` is correct, the function is correct.
                #       But name isn't nice, should refactor?
                callback_data=join(CallbackType.OWNER_ADD_ORDER, str(jio.id)),
            )
            for jio in jios
        ]
    )

    await update.effective_chat.send_message(text, reply_markup=keyboard)
    await query.answer()


async def view_favourites(update: Update, _):
    """
    Allow users to view their favourite items for each restaurant they are in.
    """

    if update.callback_query:
        await update.callback_query.answer()

    user = User.get_user(update.effective_user.id)

    # Obtain all restaurants they have favourite items for
    restaurants = user.get_favourite_restaurants()

    markup = [
        InlineKeyboardButton("↩ Cancel", callback_data=CallbackType.CANCEL_VIEW)
    ] + [
        InlineKeyboardButton(
            r, callback_data=join(CallbackType.VIEW_FAVOURITE_ITEMS, r)
        )
        for r in restaurants
    ]
    keyboard = InlineKeyboardMarkup.from_column(markup)

    message = (
        "You can view your favourite items for each of the restaurants below.\n\n"
        "Favourite items can be added by joining a Jio and adding your items there."
    )

    await update.effective_chat.send_message(message, reply_markup=keyboard)


async def view_restaurant_favourites(update: Update, _):
    query = update.callback_query
    await query.answer()

    user = User.get_user(update.effective_user.id)

    # Obtain the favourite foods
    restaurant = parse_callback_data(query.data)[1]
    favourites = user.get_favourite_orders(restaurant)

    markup = [
        InlineKeyboardButton("↩ Cancel", callback_data=CallbackType.CANCEL_VIEW)
    ] + [
        InlineKeyboardButton(
            food.food,
            callback_data=join(
                CallbackType.MAIN_MENU_REMOVE_FAV_ITEM, restaurant, str(food.id)
            ),
        )
        for food in favourites
    ]
    keyboard = InlineKeyboardMarkup.from_column(markup)

    message = (
        "The following are your favourite items from past orders.\n\n"
        "You can remove them by clicking on them."
    )

    await update.effective_message.edit_text(message, reply_markup=keyboard)


async def main_menu_confirm_favourite_action(update: Update, _):

    query = update.callback_query
    await query.answer()

    _, restaurant, idx_str = parse_callback_data(query.data)
    favourite_order = FavouriteOrder.get_favourite(int(idx_str))

    markup = [
        InlineKeyboardButton(
            "✅ Yes",
            callback_data=join(
                CallbackType.MAIN_MENU_CONFIRM_DELETE_FAV_ITEM, restaurant, idx_str
            ),
        ),
        InlineKeyboardButton(
            "❌ No",
            callback_data=join(CallbackType.VIEW_FAVOURITE_ITEMS, restaurant),
        ),
    ]
    keyboard = InlineKeyboardMarkup.from_row(markup)
    message = (
        f"You are about to delete <b>{favourite_order.food}</b> from "
        f"<b>{restaurant}</b>. Are you sure?"
    )

    await update.effective_message.edit_text(
        message, reply_markup=keyboard, parse_mode=ParseMode.HTML
    )


async def main_menu_confirm_delete_fav_item(update: Update, _):
    query = update.callback_query
    await query.answer()

    _, restaurant, idx_str = parse_callback_data(query.data)
    FavouriteOrder.delete(int(idx_str), update.effective_user.id)
    await view_restaurant_favourites(update, _)
