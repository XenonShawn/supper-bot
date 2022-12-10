from __future__ import annotations

from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from supperbot.db import Base, get_session


class Message(Base):
    """
    Represents a jio message that has been shared to a group or another person.
    """

    __tablename__ = "shared_messages"

    id = Column(Integer, primary_key=True)
    jio_id = Column(Integer, ForeignKey("supper_jios.id"))
    message_id = Column(String, unique=True)

    jio = relationship("SupperJio", back_populates="shared_messages")

    def __repr__(self):
        return f"SharedMessage({self.jio_id=}, {self.message_id=})"

    @staticmethod
    def create(jio_id: int, message_id: str) -> Message:
        msg = Message(jio_id=jio_id, message_id=message_id)

        session = get_session()
        session.add(msg)
        session.commit()
        return msg
