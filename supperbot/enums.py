from __future__ import annotations

from enum import unique, Enum


@unique
class CallbackType(str, Enum):
    """
    Enumerations for callbacks.

    The callback system in Telegram uses a callback string. To differentiate between the
    different actions, the first three characters of the callback data will be the
    action (listed below). The rest of the string will then be the "arguments" required,
    delimited by colons (':') when necessary.
    """

    # Supper Jio Creation - Starts with 0
    CREATE_JIO = "000"
    SELECT_RESTAURANT = "001"
    ADDITIONAL_DETAILS = "002"
    FINISHED_CREATION = "003"

    AMEND_DESCRIPTION = "010"
    CANCEL_AMEND_DESCRIPTION = "011"
    FINISH_AMEND_DESCRIPTION = "012"

    CLOSE_JIO = "020"

    VIEW_CREATED_JIOS = "030"
    CANCEL_VIEW = "031"
    VIEW_JOINED_JIOS = "035"

    RESEND_MAIN_MESSAGE = "040"
    OWNER_ADD_ORDER = "041"

    # Modifying of Orders - starts with 1
    ADD_ORDER = "100"
    CONFIRM_ORDER = "101"

    MODIFY_ORDER = "110"

    DELETE_ORDER = "120"
    CANCEL_ORDER_ACTION = "121"
    DELETE_ORDER_ITEM = "122"

    REFRESH_ORDER = "130"

    # Closed Jios for host - starts with 2
    REOPEN_JIO = "200"

    CREATE_ORDERING_LIST = "210"
    BACK = "211"

    PING_ALL_UNPAID = "220"

    # Closed jios for users - starts with 3
    DECLARE_PAYMENT = "300"

    UNDO_PAYMENT = "310"

    # Favourite Order System - starts with 4
    FAVOURITE_ITEM = "400"
    CONFIRM_FAVOURITE_ITEM = "401"  # Format - 141:jio_id:restaurant:idx
    REMOVE_FAVOURITE_ITEM = "402"  # Format - 142:jio_id:favourite_item_idx

    MAIN_MENU_FAVOURITES = "410"
    VIEW_FAVOURITE_ITEMS = "411"
    MAIN_MENU_REMOVE_FAV_ITEM = "412"  # 412:restaurant:favourite_item_idx
    MAIN_MENU_CONFIRM_DELETE_FAV_ITEM = "413"  # 413:restaurant:favourite_item_idx

    NOP = "999"


def regex_pattern(callback_data: str) -> str:
    return "^" + callback_data + "$"


def join(*args: str) -> str:
    return ":".join(args)


def parse_callback_data(callback_data: str) -> list[str]:
    return callback_data.split(":")


# Useful Regex Variables
CALLBACK_REGEX = "|".join(CallbackType)
