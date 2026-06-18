import os

from sqlmodel import SQLModel, create_engine

_engine = None


def is_configured() -> bool:
    """True when the app's own Postgres (`DATABASE_URL`) is configured."""
    return bool(os.getenv("DATABASE_URL"))


def _engine_url() -> str:
    # Drop the Prisma-style `?schema=` query, then force the psycopg3 driver (the only one installed).
    url = os.environ["DATABASE_URL"].split("?")[0]

    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]

    return url


def get_engine():
    """Build the engine once and create the app's tables (idempotent, once per process)."""
    global _engine

    if _engine is None:
        # Import here so the models register on SQLModel.metadata before create_all, avoiding a cycle.
        from db.memory import SubjectMemory
        from db.newsletters import Newsletter

        engine = create_engine(_engine_url(), pool_pre_ping=True)
        SQLModel.metadata.create_all(engine, tables=[Newsletter.__table__, SubjectMemory.__table__])
        _engine = engine

    return _engine
