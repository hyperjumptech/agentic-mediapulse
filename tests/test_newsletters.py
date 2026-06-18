from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import db.engine as engine_module
import db.newsletters as newsletters


def _use_sqlite(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine, tables=[newsletters.Newsletter.__table__])
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    monkeypatch.setattr(engine_module, "_engine", engine)

    return engine


def test_save_newsletter_skips_without_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert newsletters.save_newsletter("ACME", "# ACME", {"ticker": "ACME"}) is None


def test_save_newsletter_inserts_and_roundtrips(monkeypatch):
    engine = _use_sqlite(monkeypatch)
    metadata = {"ticker": "ACME", "sources": ["https://x.com/a", "https://x.com/b"]}
    row_id = newsletters.save_newsletter("ACME", "# ACME Pulse: Big Week", metadata)

    assert isinstance(row_id, int)

    with Session(engine) as session:
        rows = session.exec(select(newsletters.Newsletter)).all()

    assert len(rows) == 1
    assert rows[0].subject == "ACME"
    assert rows[0].content.startswith("# ACME Pulse")
    assert rows[0].meta == metadata


def test_save_newsletter_swallows_errors(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")

    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(newsletters, "get_engine", boom)

    assert newsletters.save_newsletter("ACME", "content", {}) is None


def test_create_newsletter_opens_pending_row(monkeypatch):
    engine = _use_sqlite(monkeypatch)
    newsletter_id = newsletters.create_newsletter("ACME")

    assert isinstance(newsletter_id, int)

    with Session(engine) as session:
        row = session.get(newsletters.Newsletter, newsletter_id)

    assert row.status == "pending"
    assert row.content == ""


def test_finalize_newsletter_fills_and_completes(monkeypatch):
    engine = _use_sqlite(monkeypatch)
    newsletter_id = newsletters.create_newsletter("ACME")
    metadata = {"ticker": "ACME", "sources": ["https://x.com/a"]}
    newsletters.finalize_newsletter(newsletter_id, content="# ACME Pulse", metadata=metadata)

    with Session(engine) as session:
        row = session.get(newsletters.Newsletter, newsletter_id)

    assert row.status == "complete"
    assert row.content == "# ACME Pulse"
    assert row.meta == metadata


def test_finalize_newsletter_marks_failed(monkeypatch):
    engine = _use_sqlite(monkeypatch)
    newsletter_id = newsletters.create_newsletter("ACME")
    newsletters.finalize_newsletter(newsletter_id, status="failed")

    with Session(engine) as session:
        row = session.get(newsletters.Newsletter, newsletter_id)

    assert row.status == "failed"
    assert row.content == ""


def test_finalize_newsletter_noop_without_id(monkeypatch):
    _use_sqlite(monkeypatch)

    newsletters.finalize_newsletter(None, content="ignored")  # must not raise
