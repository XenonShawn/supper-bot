from __future__ import annotations

from sqlalchemy import Column, BigInteger, String, select
from sqlalchemy.orm import relationship

from telegram import Update
from telegram.ext import ContextTypes

from supperbot.db import Base, get_session
from supperbot.enums import Stage
from supperbot.models import SupperJio, FavouriteOrder, Order


class User(Base):
    """Represents a user."""

    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, nullable=False)
    display_name = Column(String, nullable=False)
    chat_id = Column(BigInteger, nullable=False)

    jios = relationship("SupperJio", back_populates="owner")
    orders = relationship("Order", back_populates="user")
    favourite_orders = relationship("FavouriteOrder", back_populates="user")

    @staticmethod
    def get_user(user_id: int) -> User:
        """
        Get an instance of a user that is already stored in the database.
        """
        session = get_session()
        stmt = select(User).filter_by(id=user_id)
        return session.scalars(stmt).one()

    @staticmethod
    def upsert(user_id: int, display_name: str, chat_id: int) -> User:
        # Unfortunately, SQLAlchemy does not seem to support upserts directly.
        session = get_session()
        stmt = select(User).where(User.id == user_id)
        user = session.scalars(stmt).one_or_none()

        if user is None:
            user = User(id=user_id, display_name=display_name, chat_id=chat_id)
            session.add(user)
        else:
            user.display_name = display_name
            user.chat_id = chat_id

        session.commit()
        return user

    def get_created_jios(
        self, *, limit: int | None = 10, allow_closed: bool = False, desc: bool = True
    ) -> list[SupperJio]:
        """
        Returns a list a joins this user has created.
        """

        stmt = select(SupperJio).filter_by(owner_id=self.id)

        if not allow_closed:
            stmt = stmt.where(SupperJio.status != Stage.CLOSED)

        if desc:
            stmt = stmt.order_by(SupperJio.timestamp.desc())
        else:
            stmt = stmt.order_by(SupperJio.timestamp)

        if limit is None:
            return get_session().scalars(stmt).fetchall()
        return get_session().scalars(stmt).fetchmany(size=limit)

    def get_joined_jios(self, *, limit: int | None = 10) -> list[SupperJio]:
        """
        Returns a list of jios this user has joined.
        """
        stmt = (
            select(SupperJio)
            .join(Order)
            .filter_by(user_id=self.id)
            .order_by(SupperJio.timestamp.desc())
        )

        session = get_session()
        if limit is None:
            return session.scalars(stmt).fetchall()
        return session.scalars(stmt).fetchmany(size=limit)

    def get_favourite_foods(self, restaurant: str) -> list[FavouriteOrder]:
        stmt = select(FavouriteOrder).filter_by(user_id=self.id, restaurant=restaurant)
        return get_session().scalars(stmt).fetchall()

    def get_favourite_restaurants(self) -> set[str]:
        """
        Returns a set of restaurants for which the user has a favourite item.
        """
        stmt = select(FavouriteOrder.restaurant).filter_by(user_id=self.id)
        return set(get_session().scalars(stmt).fetchall())

    def get_favourite_orders(self, restaurant: str) -> list[FavouriteOrder]:
        """
        Returns the list of the user's favourite orders for the specified restaurant.
        """
        stmt = select(FavouriteOrder).filter_by(user_id=self.id, restaurant=restaurant)
        return get_session().scalars(stmt).fetchall()

    @staticmethod
    def initialize_user(coroutine):
        """
        Decorator to assist in adding users to the database.
        """

        async def inner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            User.upsert(
                update.effective_user.id,
                update.effective_user.first_name,
                update.effective_chat.id,
            )
            await coroutine(update, context)

        return inner
