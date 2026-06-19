import logging
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Session, SQLModel, select

from db.engine import get_engine, is_configured

logger = logging.getLogger(__name__)

# JSONB on Postgres, plain JSON elsewhere so the offline test suite can use SQLite.
_JSON = JSON().with_variant(JSONB(), "postgresql")


class NewsletterTranslation(SQLModel, table=True):
    __tablename__ = "newsletter_translations"
    __table_args__ = (UniqueConstraint("newsletter_id", "language", name="uq_newsletter_translations_nl_lang"),)

    id: int | None = Field(default=None, primary_key=True)
    newsletter_id: int = Field(index=True)  # FK-by-convention to newsletters.id
    subject: str = Field(index=True)  # the ticker, denormalized from the parent for standalone querying
    language: str = Field(index=True)
    content: str = ""
    status: str = Field(default="completed", index=True)  # "completed" | "failed"
    meta: dict = Field(default_factory=dict, sa_column=Column("metadata", _JSON, nullable=False))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )


def upsert_translation(
    newsletter_id: int | None,
    language: str,
    *,
    subject: str,
    content: str,
    status: str = "completed",
    metadata: dict | None = None,
) -> int | None:
    """Insert or update one stored translation and return its row id (best-effort, no-op if unconfigured)."""
    if newsletter_id is None or not is_configured():
        return None

    try:
        with Session(get_engine()) as session:
            statement = select(NewsletterTranslation).where(
                NewsletterTranslation.newsletter_id == newsletter_id,
                NewsletterTranslation.language == language,
            )
            translation = session.exec(statement).first()

            if translation is None:
                translation = NewsletterTranslation(newsletter_id=newsletter_id, language=language)

            translation.subject = subject
            translation.content = content
            translation.status = status
            translation.meta = metadata or {}
            session.add(translation)
            session.commit()
            session.refresh(translation)

            return translation.id
    except Exception as error:
        logger.warning("failed to store translation %s [%s]: %s", newsletter_id, language, error)

        return None


def get_translation(newsletter_id: int, language: str) -> NewsletterTranslation | None:
    """Return the stored translation for a newsletter and language, or None (best-effort)."""
    if not is_configured():
        return None

    try:
        with Session(get_engine()) as session:
            statement = select(NewsletterTranslation).where(
                NewsletterTranslation.newsletter_id == newsletter_id,
                NewsletterTranslation.language == language,
            )

            return session.exec(statement).first()
    except Exception as error:
        logger.warning("failed to read translation %s [%s]: %s", newsletter_id, language, error)

        return None
