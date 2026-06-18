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
    content: str = ""
    status: str = Field(default="complete", index=True)  # "pending" | "complete" | "failed"
    meta: dict = Field(default_factory=dict, sa_column=Column("metadata", _JSON, nullable=False))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )


def create_newsletter(subject: str) -> int | None:
    """Open a placeholder newsletter row before generation and return its id, or None if storage is unconfigured."""
    if not is_configured():
        return None

    try:
        newsletter = Newsletter(subject=subject, content="", status="pending")

        with Session(get_engine()) as session:
            session.add(newsletter)
            session.commit()
            session.refresh(newsletter)

        return newsletter.id
    except Exception as error:
        logger.warning("failed to open newsletter for %s: %s", subject, error)

        return None


def finalize_newsletter(
    newsletter_id: int | None, *, content: str | None = None, metadata: dict | None = None, status: str = "complete"
) -> None:
    """Fill in a previously opened newsletter row (best-effort, no-op if unconfigured or the row is missing)."""
    if newsletter_id is None or not is_configured():
        return

    try:
        with Session(get_engine()) as session:
            newsletter = session.get(Newsletter, newsletter_id)

            if newsletter is None:
                return

            if content is not None:
                newsletter.content = content

            if metadata is not None:
                newsletter.meta = metadata

            newsletter.status = status
            session.add(newsletter)
            session.commit()
    except Exception as error:
        logger.warning("failed to finalize newsletter %s: %s", newsletter_id, error)


def save_newsletter(subject: str, content: str, metadata: dict | None = None) -> int | None:
    """Archive a generated newsletter and return its row id, or None if storage is unconfigured or the write fails."""
    newsletter_id = create_newsletter(subject)

    if newsletter_id is None:
        return None

    finalize_newsletter(newsletter_id, content=content, metadata=metadata or {})

    return newsletter_id
