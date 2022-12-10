from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Integer,
    select,
    ForeignKey,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import relationship

from telegram import (
    Bot,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest

from supperbot.db import Base, get_session
from supperbot.enums import CallbackType, join, PaidStatus

if TYPE_CHECKING:
    from supperbot.models import SupperJio, User


class Order(Base):
    """
    Represents an order made by a user for a specific supper jio.

    The food orders are consolidated into a single tab separated string instead
    of using another table.
    """

    __tablename__ = "orders"

    jio_id = Column(Integer, ForeignKey("supper_jios.id"))
    user_id = Column(BigInteger, ForeignKey("users.id"))
    food = Column(String)  # Tab separated
    paid = Column(Integer)
    message_id = Column(Integer, unique=True, nullable=True)

    __table_args__ = (PrimaryKeyConstraint("jio_id", "user_id"),)

    user = relationship("User", back_populates="orders")
    jio = relationship("SupperJio", back_populates="orders")

    def has_paid(self) -> bool:
        return self.paid == PaidStatus.PAID

    @property
    def food_list(self) -> list[str]:
        return self.food.split("\t") if self.food else []

    def __repr__(self):
        return f"Order {self.jio_id}: ({self.user_id=}) {self.food}"

    def __str__(self):
        jio = self.jio
        message = (
            f"Supper Jio Order #{jio.id}: <b>{jio.restaurant}</b>\n"
            f"Additional Information: \n{jio.description}\n\n"
            "Your Orders:\n"
        )

        message += "\n".join(self.food_list) if self.food_list else "None"

        if self.has_paid():
            message += "\n\n💰 You have declared payment! 💰"

        if jio.is_closed():
            message += "\n\n🛑 Jio is closed! 🛑"

        return message

    @staticmethod
    def create_order(
        jio: SupperJio = None,
        user: User = None,
        jio_id: int = None,
        user_id: int = None,
    ) -> Order:
        """
        Create a new order for the user for the provided Supper Jio, if an order does
        not already exist.

        Either jio or jio_id, and either user or user_id, must be present.
        """
        jio_id = jio_id or jio.id
        user_id = user_id or user.id
        session = get_session()
        stmt = select(Order).filter_by(jio_id=jio_id, user_id=user_id)
        order = session.scalars(stmt).one_or_none()

        # If there is no existing order for this jio and user, then create a new one
        if order is None:
            order = Order(
                jio_id=jio_id, user_id=user_id, food="", paid=PaidStatus.NOT_PAID
            )
            session.add(order)
            session.commit()

        return order

    def add_food(self, food: str) -> None:
        """
        The food orders are strong in a single row per user per jio, delimited by tabs.
        """
        if self.food:
            self.food += "\t" + food
        else:
            self.food = food

        get_session().commit()

    def delete_food(self, food_idx: int) -> None:
        """
        Delete a food order based on its position.

        Deletion is based on position instead of the name of the food, due to
        1) Possibility of multiple foods with the same name
        2) Telegram callback information is limited to 64 bytes
        """
        old = self.food_list
        if food_idx > len(old):
            raise ValueError(
                "The index of the food should be smaller than the size of the list."
            )
        old.pop(food_idx)
        self.food = "\t".join(old)
        get_session().commit()

    def update(self, *, message_id: int = None, paid_status: PaidStatus = None) -> None:
        if message_id is not None:
            self.message_id = message_id

        if paid_status is not None:
            self.paid = paid_status
        get_session().commit()

    @property
    def keyboard_markup(self) -> InlineKeyboardMarkup | None:
        jio = self.jio
        jio_str = str(self.jio_id)

        if not jio.is_closed():
            return InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "➕ Add Order",
                            callback_data=join(CallbackType.ADD_ORDER, jio_str),
                        ),
                        InlineKeyboardButton(
                            "❌ Delete Order",
                            callback_data=join(CallbackType.DELETE_ORDER, jio_str),
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "⭐ Favourite Item",
                            callback_data=join(CallbackType.FAVOURITE_ITEM, jio_str),
                        )
                    ],
                ]
            )

        if not self.food_list:
            # User doesn't even have a food order. Don't let them declare payment.
            return None

        if self.has_paid():
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
                callback_data=join(CallbackType.FAVOURITE_ITEM, jio_str),
            )
        )

        return InlineKeyboardMarkup.from_column(result)

    async def send_user_order(self, bot: Bot, *, remove_reply_markup: bool = False):
        """
        Sends a new message containing the user's food orders and updates the database.
        """
        # TODO: Check if a user revoking permission for the bot to send a message will
        #       cause an error
        # TODO: Determine if it makes sense for this to be here
        if remove_reply_markup:
            # Send a normal message to remove the Reply Keyboard,
            # then edit in the InlineKeyboard
            clear_msg = await bot.send_message(
                chat_id=self.user.chat_id,
                text="Please wait while the message loads...",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode=ParseMode.HTML,
            )
            await clear_msg.delete()

        # TODO: Should try remove the previous buttons
        msg = await bot.send_message(
            chat_id=self.user.chat_id,
            text=str(self),
            reply_markup=self.keyboard_markup,
            parse_mode=ParseMode.HTML,
        )
        self.update(message_id=msg.message_id)

    async def update_user_order(self, bot: Bot):
        """
        Similar to `send_user_order`, except that it edits the (latest sent) message
        instead of sending a new one. This is more useful in scenarios where it is less
        likely for the message to have "expired".

        Note that messages can only be edited within 48 hours.
        """
        # TODO: Maybe make it resend if cannot edit?
        try:
            await bot.edit_message_text(
                str(self),
                chat_id=self.user.chat_id,
                message_id=self.message_id,
                parse_mode=ParseMode.HTML,
                reply_markup=self.keyboard_markup,
            )
        except BadRequest as e:
            logging.error(
                f"Unable to edit individual order message for user {self.user}: {e}"
            )
