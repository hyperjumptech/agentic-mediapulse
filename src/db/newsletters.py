import logging
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Session, SQLModel

from db.engine import get_engine, is_configured

logger = logging.getLogger(__name__)

# JSONB on Postgres, plain JSON elsewhere so the offline test suite can use SQLite.
_JSON = JSON().with_variant(JSONB(), "postgresql")


class Newsletter(SQLModel, table=True):
    __tablename__ = "newsletters"

    id: int | None = Field(default=None, primary_key=True)
    subject: str = Field(index=True)
    content: str
    meta: dict = Field(default_factory=dict, sa_column=Column("metadata", _JSON, nullable=False))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )


def save_newsletter(subject: str, content: str, metadata: dict | None = None) -> int | None:
    """Archive a generated newsletter and return its row id, or None if storage is unconfigured or the write fails."""
    if not is_configured():
        return None

    try:
        newsletter = Newsletter(subject=subject, content=content, meta=metadata or {})

        with Session(get_engine()) as session:
            session.add(newsletter)
            session.commit()
            session.refresh(newsletter)

        return newsletter.id
    except Exception as error:
        logger.warning("failed to store newsletter for %s: %s", subject, error)

        return None
