from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import db.engine as engine_module
import db.newsletter_translations as translations


def _use_sqlite(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine, tables=[translations.NewsletterTranslation.__table__])
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    monkeypatch.setattr(engine_module, "_engine", engine)

    return engine


def test_upsert_translation_skips_without_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert translations.upsert_translation(1, "Indonesian", subject="ACME", content="# x") is None


def test_upsert_translation_inserts_and_roundtrips(monkeypatch):
    engine = _use_sqlite(monkeypatch)
    metadata = {"ticker": "ACME", "sources": ["https://x.com/a"]}
    row_id = translations.upsert_translation(1, "Indonesian", subject="ACME", content="# ACME Pulse", metadata=metadata)

    assert isinstance(row_id, int)

    with Session(engine) as session:
        rows = session.exec(select(translations.NewsletterTranslation)).all()

    assert len(rows) == 1
    assert rows[0].newsletter_id == 1
    assert rows[0].subject == "ACME"
    assert rows[0].language == "Indonesian"
    assert rows[0].status == "completed"
    assert rows[0].meta == metadata


def test_upsert_translation_overwrites_same_language(monkeypatch):
    engine = _use_sqlite(monkeypatch)
    translations.upsert_translation(1, "Indonesian", subject="ACME", content="first")
    translations.upsert_translation(1, "Indonesian", subject="ACME", content="second")

    with Session(engine) as session:
        rows = session.exec(select(translations.NewsletterTranslation)).all()

    assert len(rows) == 1  # one row per (newsletter_id, language), not duplicated
    assert rows[0].content == "second"


def test_get_translation_reads_back(monkeypatch):
    _use_sqlite(monkeypatch)
    translations.upsert_translation(7, "Thai", subject="GLOBEX", content="# GLOBEX")
    row = translations.get_translation(7, "Thai")

    assert row is not None
    assert row.subject == "GLOBEX"
    assert row.content == "# GLOBEX"


def test_upsert_translation_swallows_errors(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")

    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(translations, "get_engine", boom)

    assert translations.upsert_translation(1, "Indonesian", subject="ACME", content="x") is None


def test_upsert_translation_noop_without_id(monkeypatch):
    _use_sqlite(monkeypatch)

    assert translations.upsert_translation(None, "Indonesian", subject="ACME", content="x") is None
