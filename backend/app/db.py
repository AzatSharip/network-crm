import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

DATABASE_URL = os.environ.get("DATABASE_URL", "")
engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    if engine is None:
        raise RuntimeError("DATABASE_URL required")
    with Session(engine, expire_on_commit=False) as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
