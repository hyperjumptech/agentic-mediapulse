from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import db.engine as engine_module
import db.memory as memory


def _use_sqlite(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine, tables=[memory.SubjectMemory.__table__])
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    monkeypatch.setattr(engine_module, "_engine", engine)

    return engine


def test_key_normalizes_subject():
    assert memory._key("  HELLO ") == "hello"
    assert memory._key("") == ""


def test_remember_subject_skips_without_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    memory.remember_subject("ACME", "brief")  # no-op, must not raise


def test_recall_subject_skips_without_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert memory.recall_subject("ACME") is None


def test_remember_and_recall_roundtrip(monkeypatch):
    _use_sqlite(monkeypatch)
    memory.remember_subject("ACME", "first brief")

    assert memory.recall_subject("acme") == "first brief"  # recall normalizes the key


def test_remember_subject_upserts_one_row(monkeypatch):
    engine = _use_sqlite(monkeypatch)
    memory.remember_subject("ACME", "first")
    memory.remember_subject("acme", "second")  # same normalized key

    assert memory.recall_subject("ACME") == "second"

    with Session(engine) as session:
        rows = session.exec(select(memory.SubjectMemory)).all()

    assert len(rows) == 1


def test_recall_unknown_subject_returns_none(monkeypatch):
    _use_sqlite(monkeypatch)

    assert memory.recall_subject("NOPE") is None
