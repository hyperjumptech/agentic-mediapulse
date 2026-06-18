import logging
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Session, SQLModel

from db.engine import get_engine, is_configured

logger = logging.getLogger(__name__)

# JSONB on Postgres, plain JSON elsewhere so the offline test suite can use SQLite.
_JSON = JSON().with_variant(JSONB(), "postgresql")


class AgentActivity(SQLModel, table=True):
    __tablename__ = "agent_activity"

    id: int | None = Field(default=None, primary_key=True)
    newsletter_id: int = Field(index=True)
    kind: str  # "agent" | "tool"
    name: str = Field(index=True)
    model: str | None = Field(default=None, index=True)  # the model behind an agent run (null for tools)
    status: str  # "ok" | "error" | "terminated"
    duration_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    error: str | None = None
    meta: dict = Field(default_factory=dict, sa_column=Column("metadata", _JSON, nullable=False))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )


def log_activity(
    *,
    newsletter_id: int,
    kind: str,
    name: str,
    status: str,
    model: str | None = None,
    duration_ms: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
    error: str | None = None,
    meta: dict | None = None,
) -> int | None:
    """Record one agent or tool event and return its row id, or None if storage is unconfigured or the write fails."""
    if not is_configured():
        return None

    try:
        activity = AgentActivity(
            newsletter_id=newsletter_id,
            kind=kind,
            name=name,
            status=status,
            model=model,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            error=error,
            meta=meta or {},
        )

        with Session(get_engine()) as session:
            session.add(activity)
            session.commit()
            session.refresh(activity)

        return activity.id
    except Exception as write_error:
        logger.warning("failed to log activity %s/%s: %s", kind, name, write_error)

        return None
