import re

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import db.engine as engine_module
import db.newsletter_translations as translations_db
import newsroom.translation as translation
from emails.templates.newsletter import _parse, newsletter_sources
from newsroom.translation import (
    _collect_strings,
    _emit_markdown,
    store_translations,
    target_languages,
    translate_markdown,
)

_MARKDOWN = (
    "# ACME Pulse: Big Week\n\n"
    "A short summary sentence.\n\n"
    "## Competitive Landscape\n"
    "Rival did something.\n\n[Read: Rival news](https://x.com/a)\n\n---\n\n"
    "Another move happened.\n\n[Read: Other](https://x.com/b)\n\n---\n\n"
    "## Quick Hits\n"
    "A small thing.\n\n[Read: Small](https://x.com/c)\n\n---\n"
)

_NUMBERED = re.compile(r"^\s*(\d+)\.\s*(.*)$")


class _Result:
    def __init__(self, text):
        self.text = text


class _FakeTranslator:
    """Stand-in for the translator agent that maps each numbered snippet through `transform`."""

    def __init__(self, transform):
        self._transform = transform

    async def run(self, prompt):
        lines = []

        for line in prompt.splitlines():
            match = _NUMBERED.match(line)

            if match:
                lines.append(f"{match.group(1)}. {self._transform(match.group(2))}")

        return _Result("\n".join(lines))


def test_emit_markdown_roundtrips_through_parse():
    title, summary, sections = _parse(_MARKDOWN)
    strings = _collect_strings(title, summary, sections)
    emitted = _emit_markdown(strings, sections)
    title2, summary2, sections2 = _parse(emitted)

    assert title2 == title
    assert summary2 == summary
    assert [name for name, _items in sections2] == [name for name, _items in sections]
    assert newsletter_sources(emitted) == newsletter_sources(_MARKDOWN)


def test_collect_strings_order_and_count():
    title, summary, sections = _parse(_MARKDOWN)
    strings = _collect_strings(title, summary, sections)
    item_count = sum(len(items) for _name, items in sections)

    # title + summary + one per section name + two per item (summary, link title)
    assert len(strings) == 2 + len(sections) + 2 * item_count
    assert strings[0] == title
    assert strings[1] == summary


def test_target_languages_parsing(monkeypatch):
    monkeypatch.setenv("NEWSLETTER_LANGUAGES", " Indonesian , english ,Indonesian, Thai , en ")

    assert target_languages() == ["Indonesian", "Thai"]


def test_target_languages_empty(monkeypatch):
    monkeypatch.delenv("NEWSLETTER_LANGUAGES", raising=False)

    assert target_languages() == []


async def test_translate_markdown_preserves_urls_and_translates(monkeypatch):
    monkeypatch.setattr(translation, "translator", _FakeTranslator(str.upper))
    out = await translate_markdown(_MARKDOWN, "Indonesian")

    assert out is not None
    assert newsletter_sources(out) == newsletter_sources(_MARKDOWN)
    assert "RIVAL DID SOMETHING." in out  # a blurb was translated (uppercased)
    assert "BIG WEEK" in out  # the title/subject was translated


async def test_translate_markdown_humanizes_output(monkeypatch):
    monkeypatch.setattr(translation, "translator", _FakeTranslator(lambda text: f"{text} — extra"))
    out = await translate_markdown(_MARKDOWN, "Indonesian")

    assert out is not None
    assert "—" not in out  # _humanize strips the em dash the fake injected


async def test_translate_markdown_returns_none_on_count_mismatch(monkeypatch):
    class _Truncated:
        async def run(self, prompt):
            return _Result("1. only one line")

    monkeypatch.setattr(translation, "translator", _Truncated())

    assert await translate_markdown(_MARKDOWN, "Indonesian") is None


async def test_store_translations_writes_completed_row(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine, tables=[translations_db.NewsletterTranslation.__table__])
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    monkeypatch.setattr(engine_module, "_engine", engine)
    monkeypatch.setenv("NEWSLETTER_LANGUAGES", "Indonesian")
    monkeypatch.setattr(translation, "translator", _FakeTranslator(lambda text: text))

    await store_translations(1, _MARKDOWN, ticker="ACME", log=lambda *a: None)

    with Session(engine) as session:
        rows = session.exec(select(translations_db.NewsletterTranslation)).all()

    assert len(rows) == 1
    assert rows[0].newsletter_id == 1
    assert rows[0].language == "Indonesian"
    assert rows[0].subject == "ACME"
    assert rows[0].status == "completed"
    assert newsletter_sources(rows[0].content) == newsletter_sources(_MARKDOWN)


async def test_store_translations_noop_without_languages(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    monkeypatch.delenv("NEWSLETTER_LANGUAGES", raising=False)
    called = []
    monkeypatch.setattr(translation, "translate_markdown", lambda *a, **k: called.append(a))

    await store_translations(1, _MARKDOWN, ticker="ACME", log=lambda *a: None)

    assert called == []
