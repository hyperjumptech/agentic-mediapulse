import os

from sqlmodel import create_engine

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
    """Build the engine once per process. The schema is owned by Alembic migrations, not create_all."""
    global _engine

    if _engine is None:
        _engine = create_engine(_engine_url(), pool_pre_ping=True)

    return _engine
