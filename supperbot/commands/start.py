"""File containing the start and help commands for the bot"""
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import InlineKeyboardMarkupLimit, ParseMode
from telegram.error import BadRequest

from supperbot.db import db
from supperbot.enums import CallbackType, join, parse_callback_data


async def help_command(update: Update, _) -> None:
    """Send a message when the command /help is issued."""
    await update.effective_chat.send_message(text="Use /start to use this bot!")


async def start_group(update: Update, _) -> None:
    """Send a message when the command /start is issued, but not in a DM."""
    await update.effective_chat.send_message(
        text="Please initialize me in direct messages!"
    )


async def start(update: Update, _) -> None:
    message = (
        "Welcome to the SupperFarFetch bot!\n\n"
        "Just click the buttons below to create a supper jio!"
    )

    reply_markup = InlineKeyboardMarkup.from_column(
        [
            InlineKeyboardButton(
                "🆕 Create Supper Jio", callback_data=CallbackType.CREATE_JIO
            ),
            InlineKeyboardButton(
                "📖 View Your Created Jios", callback_data=CallbackType.VIEW_CREATED_JIOS
            ),
            InlineKeyboardButton(
                "📑 View Joined Jios", callback_data=CallbackType.VIEW_JOINED_JIOS
            ),
            InlineKeyboardButton(
                "🍿 View Favourite Items",
                callback_data=CallbackType.MAIN_MENU_FAVOURITES,
            ),
        ]
    )

    await update.effective_chat.send_message(text=message, reply_markup=reply_markup)


async def view_created_jios(update: Update, _) -> None:
    """
    Allow the user to view the jios that they have created
    """

    query = update.callback_query

    # TODO: Create a next page functionality for the buttons so that more can be viewed
    # Telegram has a limitation on how many buttons there can be. Currently, it's 100.
    # However, 100 buttons is still too many. Right now the limit is 50.
    jios = db.get_user_jios(
        update.effective_user.id,
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
    Allow the user to view the jios that they have joined
    """

    query = update.callback_query

    # TODO: Create a next page functionality for the buttons so that more can be viewed
    # Telegram has a limitation on how many buttons there can be. Currently, it's 100.
    # However, 100 buttons is still too many. Right now the limit is 50.
    # TODO: Maybe consider only showing orders that the user has ordered something?
    jios = db.get_joined_jios(
        update.effective_user.id,
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

    # try:
    #     await update.effective_message.edit_reply_markup(None)
    # except BadRequest as e:
    #     logging.error(f"`view_favourites` unable to edit previous message: {e}")
    if update.callback_query:
        await update.callback_query.answer()

    # Obtain all restaurants they have favourite items for
    restaurants = db.get_favourite_restaurants(update.effective_user.id)

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
    # try:
    #     await update.effective_message.edit_reply_markup(None)
    # except BadRequest as e:
    #     logging.error(
    #         f"`view_restaurant_favourites` unable to edit previous message: {e}"
    #     )
    query = update.callback_query
    await query.answer()

    # Obtain the favourite foods
    restaurant = parse_callback_data(query.data)[1]
    favourite = db.get_favourite_orders(update.effective_user.id, restaurant)

    markup = [
        InlineKeyboardButton("↩ Cancel", callback_data=CallbackType.CANCEL_VIEW)
    ] + [
        InlineKeyboardButton(
            food,
            callback_data=join(
                CallbackType.MAIN_MENU_REMOVE_FAV_ITEM,
                restaurant,
                str(db.get_fav_id(update.effective_user.id, restaurant, food)),
            ),
        )
        for food in favourite
    ]
    keyboard = InlineKeyboardMarkup.from_column(markup)

    message = (
        "The following are your favourite items from past orders.\n\n"
        "You can remove them by clicking on them."
    )

    await update.effective_message.edit_text(message, reply_markup=keyboard)


async def main_menu_confirm_favourite_action(update: Update, _):

    # try:
    #     await update.effective_message.edit_reply_markup(None)
    # except BadRequest as e:
    #     logging.error(
    #         f"`main_menu_confirm_favourite_action` unable to edit previous message: {e}"
    #     )
    query = update.callback_query
    await query.answer()

    _, restaurant, idx_str = parse_callback_data(query.data)
    favourite_order = db.get_favourite(int(idx_str))

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
    # try:
    #     await update.effective_message.edit_reply_markup(None)
    # except BadRequest as e:
    #     logging.error(
    #         f"`main_menu_confirm_delete_fav_item` unable to edit previous message: {e}"
    #     )
    query = update.callback_query
    await query.answer()

    _, restaurant, idx_str = parse_callback_data(query.data)
    db.remove_favourite_order(int(idx_str), update.effective_user.id)
    await view_restaurant_favourites(update, _)


async def nop(update: Update, _):
    await update.callback_query.answer()
