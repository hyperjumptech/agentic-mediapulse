import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine

# Put `src` on the path so the app's db package imports the same way it does at runtime.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv
from sqlmodel import SQLModel

from db.agent_activity import AgentActivity
from db.engine import _engine_url
from db.memory import SubjectMemory
from db.newsletters import Newsletter

load_dotenv()

# Register every model on SQLModel.metadata so autogenerate can see the full schema.
_REGISTERED_MODELS = (Newsletter, SubjectMemory, AgentActivity)
target_metadata = SQLModel.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _database_url() -> str:
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is not set; Alembic needs it to run migrations.")

    return _engine_url()


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_database_url(), pool_pre_ping=True)

    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
