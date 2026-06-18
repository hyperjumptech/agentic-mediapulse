import logging
from datetime import datetime

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, Session, SQLModel

from db.engine import get_engine, is_configured

logger = logging.getLogger(__name__)


class SubjectMemory(SQLModel, table=True):
    __tablename__ = "subject_memory"

    subject: str = Field(primary_key=True)  # normalized key: stripped + lowercased
    brief: str
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    )


def _key(subject: str) -> str:
    return (subject or "").strip().lower()


def remember_subject(subject: str, brief: str) -> None:
    """Upsert a resolved brief for a subject (best-effort, no-op if unconfigured)."""
    key = _key(subject)

    if not key or not is_configured():
        return

    try:
        with Session(get_engine()) as session:
            existing = session.get(SubjectMemory, key)

            if existing:
                existing.brief = brief
            else:
                existing = SubjectMemory(subject=key, brief=brief)

            session.add(existing)
            session.commit()
    except Exception as error:
        logger.warning("failed to store subject memory for %s: %s", subject, error)


def recall_subject(subject: str) -> str | None:
    """Return the latest stored brief for a subject, or None (best-effort)."""
    key = _key(subject)

    if not key or not is_configured():
        return None

    try:
        with Session(get_engine()) as session:
            row = session.get(SubjectMemory, key)

            return row.brief if row else None
    except Exception as error:
        logger.warning("failed to recall subject memory for %s: %s", subject, error)

        return None
