from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey, delete, select
from sqlalchemy.orm import relationship

from supperbot.db import Base, get_session

if TYPE_CHECKING:
    from supperbot.models import User, SupperJio


class FavouriteOrder(Base):
    """Stores the favourite orders of each user for each restaurant"""

    MAX_FAVOURITE_ITEMS_PER_RESTAURANT = 10

    __tablename__ = "favourite_orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    restaurant = Column(String(32))
    food = Column(String)

    user = relationship("User", back_populates="favourite_orders")

    def __repr__(self):
        return (
            f"FavouriteOrder"
            f"({self.id=}, {self.user_id=}, {self.restaurant=}, {self.food=}"
        )

    @staticmethod
    def create(user: User, restaurant: str, food: str):
        """
        Adds the user's favourite orders for a specified restaurant.
        Each user can only have up to 10 favourite orders per restaurant.

        :param user: The user.
        :param restaurant: The restaurant's name.
        :param food: The name of the favourite food.
        :return: A boolean indicating whether the insert was successful.
        """
        favourite = user.get_favourite_foods(restaurant)
        if len(favourite) >= FavouriteOrder.MAX_FAVOURITE_ITEMS_PER_RESTAURANT:
            return False

        if food not in favourite:
            session = get_session()
            session.add(
                FavouriteOrder(user_id=user.id, restaurant=restaurant, food=food)
            )
            session.commit()

        return True

    @staticmethod
    def get_favourite(fav_id: int) -> FavouriteOrder:
        """
        Get a FavouriteOrder object based on its id
        """
        stmt = select(FavouriteOrder).filter_by(id=fav_id)
        return get_session().scalars(stmt).one()

    @staticmethod
    def delete(fav_id: int, user_id: int):
        session = get_session()
        stmt = delete(FavouriteOrder).filter_by(id=fav_id, user_id=user_id)
        session.execute(stmt)
        session.commit()
