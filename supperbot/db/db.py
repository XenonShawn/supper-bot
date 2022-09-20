from __future__ import annotations

from sqlalchemy import select, update, and_, delete

from supperbot.db.models import (
    Stage,
    PaidStatus,
    SupperJio,
    Order,
    User,
    Message,
    Session,
    FavouriteOrder,
)


_session = Session()

#
# Supper Jio
#


def create_jio(owner_id: int, restaurant: str, description: str) -> SupperJio:
    jio = SupperJio(owner_id, restaurant, description)

    _session.add(jio)
    _session.commit()
    return jio


def get_jio(jio_id: int) -> SupperJio:
    stmt = select(SupperJio).where(SupperJio.id == jio_id)
    return _session.scalars(stmt).one()


def update_jio_message_id(jio_id: int, chat_id: int, message_id: int) -> None:
    _session.execute(
        update(SupperJio)
        .where(SupperJio.id == jio_id)
        .values(chat_id=chat_id, message_id=message_id)
    )
    _session.commit()


def update_jio_status(jio_id: int, status: Stage) -> None:
    stmt = update(SupperJio).where(SupperJio.id == jio_id).values(status=status)
    _session.execute(stmt)
    _session.commit()


def delete_jio(jio: SupperJio):
    raise NotImplementedError


def get_user_jios(
    owner_id: int,
    *,
    limit: int | None = 10,
    allow_closed: bool = False,
    desc: bool = True,
) -> list[SupperJio]:
    stmt = select(SupperJio).filter_by(owner_id=owner_id)

    if not allow_closed:
        stmt = stmt.where(SupperJio.status != Stage.CLOSED)

    if desc:
        stmt = stmt.order_by(SupperJio.timestamp.desc())
    else:
        stmt = stmt.order_by(SupperJio.timestamp)

    if limit is None:
        return _session.scalars(stmt).fetchall()
    return _session.scalars(stmt).fetchmany(size=limit)


def get_joined_jios(user_id: int, *, limit: int | None = 10) -> list[SupperJio]:
    stmt = (
        select(SupperJio)
        .join(Order)
        .filter_by(user_id=user_id)
        .order_by(SupperJio.timestamp.desc())
    )

    if limit is None:
        return _session.scalars(stmt).fetchall()
    return _session.scalars(stmt).fetchmany(size=limit)


def edit_jio_description(jio: SupperJio, description: str) -> None:
    jio.description = description
    _session.commit()


#
# Users
#


def upsert_user(user_id: int, display_name: str, chat_id: int) -> User:
    # Unfortunately, SQLAlchemy does not seem to support upserts directly.
    stmt = select(User).where(User.id == user_id)
    user = _session.scalars(stmt).one_or_none()

    if user is None:
        user = User(id=user_id, display_name=display_name, chat_id=chat_id)
        _session.add(user)
    else:
        user.display_name = display_name
        user.chat_id = chat_id

    _session.commit()

    return user


def get_user_name(user_id: int) -> str:
    stmt = select(User.display_name).filter_by(id=user_id)
    return _session.scalars(stmt).one()


#
# Orders
#


def create_order(jio_id: int, user_id: int) -> Order:
    # Check if there exists an existing food order already
    stmt = select(Order).filter_by(jio_id=jio_id, user_id=user_id)
    order = _session.scalars(stmt).one_or_none()

    # If there is no existing order for this jio_io and user, then create a new one
    if order is None:
        order = Order(jio_id=jio_id, user_id=user_id, food="", paid=PaidStatus.NOT_PAID)
        _session.add(order)
        _session.commit()

    return order


def add_food_order(jio_id: int, user_id: int, food: str) -> Order:
    """
    Adds one food order to the jio with id `jio_id` for user with id `user_id`.

    The food orders are stored in a single row per user per jio, delimited by tabs.
    """
    stmt = select(Order).filter_by(jio_id=jio_id, user_id=user_id)
    order = _session.scalars(stmt).one()

    # If there are existing food orders. Insert a tab to delimit the food orders.
    if order.food:
        order.food += "\t"

    order.food += food
    _session.commit()
    return order


def delete_food_order(order: Order, food_idx) -> None:
    old = order.food_list
    old.pop(food_idx)
    order.food = "\t".join(old)
    _session.commit()


def update_order_message_id(jio_id: int, user_id: int, message_id: int) -> None:
    stmt = select(Order).filter_by(jio_id=jio_id, user_id=user_id)
    order = _session.scalars(stmt).one()

    order.message_id = message_id
    _session.commit()


def get_list_complete_orders(jio_id: int) -> list[Order]:
    """
    Returns a list of `Order` objects for the jio with `jio_id`, for users
    who have made at least one food order.
    """
    stmt = select(Order).filter_by(jio_id=jio_id).where(Order.food != "")
    return _session.scalars(stmt).fetchall()


def get_list_all_orders(jio_id: int) -> list[Order]:
    stmt = select(Order).filter_by(jio_id=jio_id)
    return _session.scalars(stmt).fetchall()


def get_order(jio_id: int, user_id: int) -> Order:
    stmt = select(Order).filter_by(jio_id=jio_id, user_id=user_id)
    return _session.scalars(stmt).one()


def update_order_payment(jio_id: int, user_id: int, status: PaidStatus):
    _session.execute(
        update(Order)
        .where(and_(Order.jio_id == jio_id, Order.user_id == user_id))
        .values(paid=status)
    )
    _session.commit()


#
# Favourite Orders
# NOTE: Too many functions. Consider refactoring, the names are quite confusing
#


def get_favourite_restaurants(user_id: int) -> set[str]:
    """
    Returns the list of restaurants for which the user has a favourite item.
    :param user_id:
    :return:
    """
    stmt = select(FavouriteOrder.restaurant).filter_by(user_id=user_id)
    return set(_session.scalars(stmt).fetchall())


def get_favourite_orders(user_id: int, restaurant: str) -> set[str]:
    """
    Returns the user's favourite orders for the restaurant.
    """
    stmt = select(FavouriteOrder.food).filter_by(user_id=user_id, restaurant=restaurant)
    return set(_session.scalars(stmt).fetchall())


def get_fav_id(user_id: int, restaurant: str, food: str) -> int:
    stmt = select(FavouriteOrder.id).filter_by(
        user_id=user_id, restaurant=restaurant, food=food
    )
    return _session.scalars(stmt).one()


def get_favourite(fav_id: int) -> FavouriteOrder:
    stmt = select(FavouriteOrder).filter_by(id=fav_id)
    return _session.scalars(stmt).one()


def add_favourite_order(user_id: int, restaurant: str, food: str) -> bool:
    """
    Adds the user's favourite orders for a specified restaurant.
    Each user can only have up to 10 favourite orders per restaurant.

    :param user_id: The user's id.
    :param restaurant: The restaurant's name.
    :param food: The name of the favourite food.
    :return: A boolean indicating whether the upsert was successful.
    """
    favourite = get_favourite_orders(user_id, restaurant)
    if len(favourite) >= 10:
        return False

    if food not in favourite:
        _session.add(FavouriteOrder(user_id=user_id, restaurant=restaurant, food=food))
        _session.commit()

    return True


def remove_favourite_order(fav_id: int, user_id: int) -> None:
    """
    Removes one favourite order from a user for a restaurant.
    User id is provided as a sanity check

    :param fav_id: The id of the favourite food
    :param user_id: The id of the user
    """
    stmt = delete(FavouriteOrder).filter_by(id=fav_id, user_id=user_id)
    _session.execute(stmt)
    _session.commit()


#
# Messages
#


def new_msg(jio_id: int, message_id: str) -> Message:
    msg = Message(jio_id=jio_id, message_id=message_id)
    _session.add(msg)
    _session.commit()
    return msg


def get_msg_id(jio_id: int) -> list[str]:
    stmt = select(Message.message_id).filter_by(jio_id=jio_id)
    return _session.scalars(stmt).all()
