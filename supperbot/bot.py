import logging

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ChosenInlineResultHandler,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

from supperbot.enums import CallbackType
from supperbot.commands.start import (
    start_group,
    start,
    help_command,
    view_created_jios,
    cancel_view,
    view_joined_jios,
    view_favourites,
    view_restaurant_favourites,
    main_menu_confirm_favourite_action,
    main_menu_confirm_delete_fav_item,
    nop,
)
from supperbot.commands.creation import (
    create,
    additional_details,
    inline_query,
    shared_jio,
    finished_creation,
    resend_main_message,
    amend_description,
    finish_amend_description,
    cancel_amend_description,
)
from supperbot.commands.ordering import (
    interested_user,
    interested_owner,
    add_order,
    confirm_order,
    delete_order,
    cancel_order_action,
    delete_order_item,
    add_favourite_item,
    confirm_favourite_item,
    delete_favourite_item,
)
from supperbot.commands.close import (
    close_jio,
    reopen_jio,
    create_ordering_list,
    back,
    ping_unpaid_users,
)
from supperbot.commands.payment import declare_payment, undo_payment

from config import TOKEN


async def not_implemented_callback(update: Update, _) -> None:
    query = update.callback_query
    await query.answer("This functionality is currently not implemented!")


async def unrecognized_callback(update: Update, _) -> None:
    await not_implemented_callback(update, _)
    logging.error(f"Unexpected callback data received: {update.callback_query.data}")


async def set_commands(context: CallbackContext) -> None:
    await context.bot.set_my_commands(
        [
            ("/start", "Start the bot"),
            ("/favourites", "View your favourite items for each restaurant"),
        ]
    )
    logging.info(f"Started as {context.bot.name}")


application = ApplicationBuilder().concurrent_updates(False).token(TOKEN).build()
application.job_queue.run_once(set_commands, 0)

# View previously created jios
application.add_handler(
    CallbackQueryHandler(view_created_jios, pattern=CallbackType.VIEW_CREATED_JIOS)
)

application.add_handler(
    CallbackQueryHandler(view_joined_jios, pattern=CallbackType.VIEW_JOINED_JIOS)
)

application.add_handler(
    CallbackQueryHandler(cancel_view, pattern=CallbackType.CANCEL_VIEW)
)

# Handler for the creation of a supper jio
create_jio_handler = CallbackQueryHandler(create, pattern=CallbackType.CREATE_JIO)
create_jio_conv_handler = ConversationHandler(
    entry_points=[create_jio_handler],
    states={
        CallbackType.ADDITIONAL_DETAILS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, additional_details)
        ],
        CallbackType.FINISHED_CREATION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, finished_creation)
        ],
    },
    fallbacks=[create_jio_handler],
)
application.add_handler(create_jio_conv_handler)

# Handler for editing the description of a supper jio
amend_description_handler = CallbackQueryHandler(
    amend_description, pattern=CallbackType.AMEND_DESCRIPTION
)
amend_description_conv_handler = ConversationHandler(
    entry_points=[amend_description_handler],
    states={
        CallbackType.FINISH_AMEND_DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, finish_amend_description)
        ]
    },
    fallbacks=[
        amend_description_handler,
        CallbackQueryHandler(
            cancel_amend_description, pattern=CallbackType.CANCEL_AMEND_DESCRIPTION
        ),
    ],
)
application.add_handler(amend_description_conv_handler)


# Handler for when a user clicks on the "Add Order" button on a jio
application.add_handler(
    CommandHandler("start", interested_user, filters.Regex(r"order\d"))
)
application.add_handler(
    CallbackQueryHandler(interested_owner, pattern=CallbackType.OWNER_ADD_ORDER)
)


# Handler for adding of orders to a jio
add_order_handler = CallbackQueryHandler(add_order, pattern=CallbackType.ADD_ORDER)
add_order_conv_handler = ConversationHandler(
    entry_points=[add_order_handler],
    states={
        CallbackType.CONFIRM_ORDER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_order)
        ]
    },
    # Allow users to press "add order" again - otherwise it'll show them
    # "not implemented" and I'm not sure why it's happening
    fallbacks=[add_order_handler],
)
application.add_handler(add_order_conv_handler)
application.add_handler(
    CallbackQueryHandler(resend_main_message, pattern=CallbackType.RESEND_MAIN_MESSAGE)
)

# Deleting orders handlers
application.add_handler(
    CallbackQueryHandler(delete_order, pattern=CallbackType.DELETE_ORDER)
)
application.add_handler(
    CallbackQueryHandler(cancel_order_action, pattern=CallbackType.CANCEL_ORDER_ACTION)
)
application.add_handler(
    CallbackQueryHandler(delete_order_item, pattern=CallbackType.DELETE_ORDER_ITEM)
)

# Adding favourite orders
application.add_handler(
    CallbackQueryHandler(add_favourite_item, pattern=CallbackType.FAVOURITE_ITEM)
)
application.add_handler(
    CallbackQueryHandler(
        confirm_favourite_item, pattern=CallbackType.CONFIRM_FAVOURITE_ITEM
    )
)
application.add_handler(
    CallbackQueryHandler(
        delete_favourite_item, pattern=CallbackType.REMOVE_FAVOURITE_ITEM
    )
)

# Viewing favourites
application.add_handler(
    CallbackQueryHandler(view_favourites, pattern=CallbackType.MAIN_MENU_FAVOURITES)
)
application.add_handler(
    CommandHandler("favourites", view_favourites, filters.ChatType.PRIVATE)
)

# Viewing favourite items in main menu
application.add_handler(
    CallbackQueryHandler(
        view_restaurant_favourites, pattern=CallbackType.VIEW_FAVOURITE_ITEMS
    )
)

# Confirming whether to delete favourite item
application.add_handler(
    CallbackQueryHandler(
        main_menu_confirm_favourite_action,
        pattern=CallbackType.MAIN_MENU_REMOVE_FAV_ITEM,
    )
)
application.add_handler(
    CallbackQueryHandler(
        main_menu_confirm_delete_fav_item,
        pattern=CallbackType.MAIN_MENU_CONFIRM_DELETE_FAV_ITEM,
    )
)

# Close and reopen jio handler
application.add_handler(CallbackQueryHandler(close_jio, pattern=CallbackType.CLOSE_JIO))
application.add_handler(
    CallbackQueryHandler(reopen_jio, pattern=CallbackType.REOPEN_JIO)
)

# Create ordering list handler
application.add_handler(
    CallbackQueryHandler(
        create_ordering_list, pattern=CallbackType.CREATE_ORDERING_LIST
    )
)
application.add_handler(CallbackQueryHandler(back, pattern=CallbackType.BACK))

# Payment handlers
application.add_handler(
    CallbackQueryHandler(declare_payment, pattern=CallbackType.DECLARE_PAYMENT)
)
application.add_handler(
    CallbackQueryHandler(undo_payment, pattern=CallbackType.UNDO_PAYMENT)
)

# Ping unpaid users
application.add_handler(
    CallbackQueryHandler(ping_unpaid_users, pattern=CallbackType.PING_ALL_UNPAID)
)

# /start and /help command handler
application.add_handler(CommandHandler("start", start_group, ~filters.ChatType.PRIVATE))
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))

# InlineQuery and InlineQuery result handler
application.add_handler(InlineQueryHandler(inline_query))
application.add_handler(ChosenInlineResultHandler(shared_jio, pattern="order"))

# No-Operation (empty buttons)
application.add_handler(CallbackQueryHandler(nop, pattern=CallbackType.NOP))

# Not yet implemented callbacks
unimplemented_callbacks = "|".join(
    (
        CallbackType.AMEND_DESCRIPTION,
        CallbackType.PING_ALL_UNPAID,
    )
)
application.add_handler(
    CallbackQueryHandler(not_implemented_callback, unimplemented_callbacks)
)

# Fall through for any callbacks
application.add_handler(CallbackQueryHandler(unrecognized_callback))
