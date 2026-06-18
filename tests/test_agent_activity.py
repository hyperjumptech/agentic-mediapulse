from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import db.agent_activity as agent_activity
import db.engine as engine_module


def _use_sqlite(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine, tables=[agent_activity.AgentActivity.__table__])
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    monkeypatch.setattr(engine_module, "_engine", engine)

    return engine


def test_log_activity_skips_without_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert agent_activity.log_activity(newsletter_id=1, kind="agent", name="analyst", status="ok") is None


def test_log_activity_inserts_and_roundtrips(monkeypatch):
    engine = _use_sqlite(monkeypatch)
    row_id = agent_activity.log_activity(
        newsletter_id=7,
        kind="agent",
        name="researcher_quick_hits",
        model="gpt-4.1-mini",
        status="ok",
        duration_ms=1200,
        input_tokens=300,
        output_tokens=120,
        total_tokens=420,
        meta={"finish_reason": "stop"},
    )

    assert isinstance(row_id, int)

    with Session(engine) as session:
        rows = session.exec(select(agent_activity.AgentActivity)).all()

    assert len(rows) == 1
    assert rows[0].newsletter_id == 7
    assert rows[0].kind == "agent"
    assert rows[0].name == "researcher_quick_hits"
    assert rows[0].model == "gpt-4.1-mini"
    assert rows[0].total_tokens == 420
    assert rows[0].meta == {"finish_reason": "stop"}


def test_log_activity_records_failure(monkeypatch):
    engine = _use_sqlite(monkeypatch)
    agent_activity.log_activity(newsletter_id=9, kind="tool", name="search", status="error", error="RuntimeError: boom")

    with Session(engine) as session:
        row = session.exec(select(agent_activity.AgentActivity)).one()

    assert row.status == "error"
    assert row.error == "RuntimeError: boom"
    assert row.total_tokens is None


def test_log_activity_swallows_errors(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")

    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(agent_activity, "get_engine", boom)

    assert agent_activity.log_activity(newsletter_id=1, kind="agent", name="analyst", status="ok") is None
