import os

from alembic import context
from app import models  # noqa: F401
from app.db import Base
from sqlalchemy import create_engine

config = context.config
engine = create_engine(os.environ["MIGRATION_DATABASE_URL"])
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
