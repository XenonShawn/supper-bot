from __future__ import annotations

from datetime import datetime
import logging
from typing import TYPE_CHECKING

from sqlalchemy import Column, BigInteger, String, Integer, select, ForeignKey
from sqlalchemy.orm import relationship

from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.helpers import create_deep_linked_url

from supperbot.db import Base, get_session
from supperbot.enums import CallbackType, join, Stage

from supperbot.models import Order

if TYPE_CHECKING:
    from supperbot.models import User, Message


class SupperJio(Base):
    """Represents a created Supper Jio."""

    __tablename__ = "supper_jios"

    id = Column(Integer, primary_key=True, nullable=False)
    description = Column(String, nullable=False)
    restaurant = Column(String(32), nullable=False)
    owner_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    status = Column(Integer, nullable=False)
    chat_id = Column(BigInteger, nullable=True)
    message_id = Column(Integer, unique=True, nullable=True)
    timestamp = Column(String, nullable=False)

    owner: User = relationship("User", back_populates="jios")
    shared_messages: list[Message] = relationship("Message", back_populates="jio")
    orders: list[Order] = relationship("Order", back_populates="jio")

    def __init__(self, owner_id: int, restaurant: str, description: str):
        # TODO: Do bounds checking for restaurant field
        self.owner_id = owner_id
        self.restaurant = restaurant
        self.description = description
        self.status = Stage.CREATED
        self.timestamp = str(datetime.now())

    def __str__(self):
        closed = "Closed, " if self.status == Stage.CLOSED else ""
        return f"Order {self.id}: {self.restaurant} ({closed + self.timestamp[:10]})"

    @staticmethod
    def create(owner_id: int, restaurant: str, description: str) -> SupperJio:
        jio = SupperJio(owner_id, restaurant, description)

        session = get_session()
        session.add(jio)
        session.commit()
        return jio

    @staticmethod
    def get_jio(jio_id: int) -> SupperJio:
        stmt = select(SupperJio).where(SupperJio.id == jio_id)
        session = get_session()

        return session.scalars(stmt).one()

    def update(
        self,
        *,
        chat_id: int = None,
        message_id: int = None,
        description: str = None,
        status: Stage = None,
    ) -> None:
        """
        Update the chat and message id for the Supper Jio message.

        This method is necessary as the chat and message id is not available until a
        message is sent in Telegram.
        """
        if chat_id is not None:
            self.chat_id = chat_id

        if message_id is not None:
            self.message_id = message_id

        if description is not None:
            self.description = description

        if status is not None:
            self.status = status

        get_session().commit()

    def is_closed(self) -> bool:
        return self.status == Stage.CLOSED

    @property
    def message(self) -> str:
        """
        The text that will be displayed in the host's main message and the shared
        messages in the groups.
        """
        message = (
            f"Supper Jio Order #{self.id}: <b>{self.restaurant}</b>\n"
            f"Additional Information: \n{self.description}\n\n"
            "Current Orders:\n"
        )

        orders: list[Order] = self.orders
        order_list = "\n".join(
            _format_individual_orders(order) for order in orders if order.food_list
        )
        message += order_list if order_list else "None"

        if self.is_closed():
            message += "\n🛑 Jio is closed! 🛑"

        return message

    @property
    def keyboard_markup(self) -> InlineKeyboardMarkup:
        """
        The inline keyboard markup for the host main message.
        :return:
        """
        jio_str = str(self.id)

        if self.is_closed():
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
                        "📢 Broadcast Message",
                        callback_data=join(CallbackType.BROADCAST_MESSAGE, jio_str),
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

    def shared_message_reply_markup(self, bot: Bot) -> InlineKeyboardMarkup | None:
        if self.is_closed():
            return None

        return InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                text="➕ Add Order",
                url=create_deep_linked_url(bot.username, f"order{self.id}"),
            )
        )

    async def update_main_jio_message(self, bot: Bot):
        """
        Update the host's jio message, i.e. the one used to control the supper jio.
        """
        # TODO: Consider if we should resend the message if editing fails?
        try:
            await bot.edit_message_text(
                self.message,
                self.chat_id,
                self.message_id,
                parse_mode=ParseMode.HTML,
                reply_markup=self.keyboard_markup,
            )
        except BadRequest as e:
            logging.error(
                f"Unable to edit original jio message for order {self.id}: {e}"
            )

    async def update_shared_jio_messages(self, bot: Bot):
        """
        Updates all shared jio messages, i.e. the messages sent to groups by the host.
        """
        text = self.message
        reply_markup = self.shared_message_reply_markup(bot)
        for msg in self.shared_messages:
            try:
                await bot.edit_message_text(
                    text,
                    inline_message_id=msg.message_id,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                )
            except BadRequest as e:
                logging.error(f"Unable to edit message with message_id {msg.id}: {e}")

    async def update_individual_order_messages(self, bot: Bot):
        """
        Updates all individual order messages.

        Obviously, this method uses the API a lot, especially if there are many users.
        Care must be taken to ensure that all functions using this method are rate
        limited.
        """
        for order in self.orders:
            await order.update_user_order(bot)

    async def update_all_jio_messages(self, bot: Bot):
        """
        Updates all messages relating to this jio, i.e. the host's message, the shared
        messages and the individual user messages.

        Essentially just `update_main_jio_message`, `update_shared_jio_messages` and
        `update_individual_order_messages` all together.

        As this method uses the API a lot, especially if there are many users in this
        Supper Jio, care must be taken to ensure that all function using this method
        are rate limited.
        """
        await self.update_main_jio_message(bot)
        await self.update_shared_jio_messages(bot)
        await self.update_individual_order_messages(bot)


def _format_individual_orders(order: Order):
    """
    Formats individual orders for shared messages.
    """
    if not order.food_list:
        return f"{order.user.display_name} -- None"

    ordered = f"{order.user.display_name} -- " + "; ".join(order.food_list)

    if order.has_paid():
        return "<s>" + ordered + "</s> Paid"
    return ordered
