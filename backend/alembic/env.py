from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine

import cidy_api.models_db  # noqa: F401  (registers models)
from cidy_api.config import get_settings
from cidy_api.db import Base

target_metadata = Base.metadata


def run_migrations_online() -> None:
    engine = create_engine(get_settings().database_url, future=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
