from __future__ import annotations

from datetime import datetime
from enum import IntEnum

from sqlalchemy import (
    Column as Col,
    ForeignKey,
    BigInteger,
    Integer,
    String,
    create_engine,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from config import DATABASE


# TODO: Make this configurable
engine = create_engine(DATABASE, future=True, echo=False)


Base = declarative_base()


class Stage(IntEnum):
    CREATED = 0
    CLOSED = 1


class PaidStatus(IntEnum):
    NOT_PAID = 0
    PAID = 1


def Column(*args, **kwargs):
    """A helper function to make `sqlalchemy.Column` nullable `False` by default."""
    kwargs["nullable"] = kwargs.get("nullable", False)
    return Col(*args, **kwargs)


class User(Base):
    """Represents a user."""

    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    display_name = Column(String)
    chat_id = Column(BigInteger)


class SupperJio(Base):
    """Represents a created Supper Jio."""

    __tablename__ = "supper_jios"

    id = Column(Integer, primary_key=True)
    description = Column(String)
    restaurant = Column(String(32))
    owner_id = Column(BigInteger)
    status = Column(Integer)
    chat_id = Column(BigInteger, nullable=True)
    message_id = Column(Integer, unique=True, nullable=True)
    timestamp = Column(String)

    def __init__(self, owner_id: int, restaurant: str, description: str):
        self.owner_id = owner_id
        self.restaurant = restaurant
        self.description = description
        self.status = Stage.CREATED
        self.timestamp = str(datetime.now())

    def is_closed(self):
        return self.status != Stage.CREATED

    def __repr__(self):
        closed = "Closed, " if self.status == Stage.CLOSED else ""
        return f"Order {self.id}: {self.restaurant} ({closed + self.timestamp[:10]})"


class Message(Base):
    """Represents a shared jio message"""

    __tablename__ = "shared_messages"

    id = Column(Integer, primary_key=True)
    jio_id = Column(Integer, ForeignKey("supper_jios.id"))
    message_id = Column(String, unique=True)

    jio = relationship("SupperJio", backref="messages")

    def __repr__(self):
        return f"SharedMessage({self.jio_id=}, {self.message_id=})"


class Order(Base):
    """Represents an order made by a user"""

    __tablename__ = "orders"

    jio_id = Column(Integer, ForeignKey("supper_jios.id"))
    user_id = Column(BigInteger, ForeignKey("users.id"))
    food = Column(String)  # Tab separated
    paid = Column(Integer)
    message_id = Column(Integer, unique=True, nullable=True)

    __table_args__ = (PrimaryKeyConstraint("jio_id", "user_id"),)

    user = relationship("User", backref="orders")
    jio = relationship("SupperJio", backref="orders")

    def has_paid(self):
        return self.paid == PaidStatus.PAID

    @property
    def food_list(self) -> list[str]:
        return self.food.split("\t") if self.food else []

    def __repr__(self):
        return f"Order {self.jio_id}: ({self.user_id=}) {self.food}"


class FavouriteOrder(Base):
    """Stores the favourite orders of each user for each restaurant"""

    __tablename__ = "favourite_orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    restaurant = Column(String(32))
    food = Column(String)

    user = relationship("User", backref="favourite_orders")

    def __repr__(self):
        return (
            f"FavouriteOrder"
            f"({self.id=}, {self.user_id=}, {self.restaurant=}, {self.food=}"
        )


Base.metadata.create_all(engine)
Session = sessionmaker(engine)
