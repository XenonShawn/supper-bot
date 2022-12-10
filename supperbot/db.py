from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from config import DATABASE

engine = create_engine(DATABASE, future=True, echo=False)
Base = declarative_base()

_Session = None


def get_session() -> Session:
    global _Session

    if _Session is None:
        Base.metadata.create_all(engine)
        _Session = sessionmaker(engine)()
    return _Session
