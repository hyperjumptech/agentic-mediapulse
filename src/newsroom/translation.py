import asyncio
import os
import re

from agents.translator import translator
from db.engine import is_configured
from db.newsletter_translations import upsert_translation
from emails.templates.newsletter import _parse, newsletter_sources
from newsroom.orchestrator import _humanize

_NUMBERED_RE = re.compile(r"^\s*(\d+)[.):]\s*(.*)$")


def target_languages() -> list[str]:
    """Configured target languages from `NEWSLETTER_LANGUAGES` (comma-separated), English filtered out."""
    seen: set[str] = set()
    languages: list[str] = []

    for part in os.getenv("NEWSLETTER_LANGUAGES", "").split(","):
        name = part.strip()
        key = name.lower()

        if not name or key in ("english", "en") or key in seen:
            continue

        seen.add(key)
        languages.append(name)

    return languages


def _collect_strings(title: str, summary: str, sections: list[tuple[str, list[dict]]]) -> list[str]:
    """Flatten every human-readable string in a fixed order: title, summary, then each section name and its items."""
    strings = [title, summary]

    for name, items in sections:
        strings.append(name)

        for item in items:
            strings.append(item["summary"])
            strings.append(item["title"])

    return strings


def _emit_markdown(strings: list[str], sections: list[tuple[str, list[dict]]]) -> str:
    """Rebuild the newsletter markdown from translated strings plus the original URLs and structure."""
    cursor = iter(strings)
    title = next(cursor)
    summary = next(cursor)
    parts = [f"# {title}", "", summary, ""]

    for _name, items in sections:
        section_name = next(cursor)
        entries = []

        for item in items:
            blurb = next(cursor)
            link_title = next(cursor)
            entries.append(f"{blurb}\n\n[Read: {link_title}]({item['url']})\n\n---")

        parts.append(f"## {section_name}")
        parts.append("\n\n".join(entries))
        parts.append("")

    return "\n".join(parts).strip() + "\n"


def _parse_numbered(text: str, count: int) -> list[str] | None:
    """Parse `<n>. <text>` lines back into an ordered list, or None unless every number 1..count is present once."""
    found: dict[int, str] = {}

    for line in text.splitlines():
        match = _NUMBERED_RE.match(line)

        if match:
            found[int(match.group(1))] = match.group(2).strip()

    if set(found) != set(range(1, count + 1)):
        return None

    return [found[number] for number in range(1, count + 1)]


async def _translate_strings(language: str, strings: list[str]) -> list[str] | None:
    """Translate an ordered list of snippets, returning the translated list or None on a malformed response."""
    numbered = "\n".join(f"{index}. {snippet}" for index, snippet in enumerate(strings, 1))
    prompt = f"TARGET LANGUAGE: {language}\n\nSNIPPETS:\n{numbered}"
    response = (await translator.run(prompt)).text
    parsed = _parse_numbered(response, len(strings))

    if parsed is None:
        return None

    return [_humanize(snippet) for snippet in parsed]


async def translate_markdown(base_markdown: str, language: str) -> str | None:
    """Translate an assembled newsletter into `language`, preserving URLs and structure. None on failure."""
    title, summary, sections = _parse(base_markdown)
    strings = _collect_strings(title, summary, sections)
    translated = await _translate_strings(language, strings)

    if translated is None:
        return None

    return _emit_markdown(translated, sections)


async def store_translations(newsletter_id: int | None, base_markdown: str, *, ticker: str, log=print) -> None:
    """Translate the finished newsletter into each configured language and store it (best-effort, never raises out)."""
    if newsletter_id is None or not is_configured():
        return

    languages = target_languages()

    if not languages:
        return

    async def one(language: str) -> None:
        try:
            content = await translate_markdown(base_markdown, language)

            if content is None:
                log(f"translation skipped {ticker} [{language}]: malformed translator output")

                return

            upsert_translation(
                newsletter_id,
                language,
                subject=ticker,
                content=content,
                metadata={"ticker": ticker, "sources": newsletter_sources(content)},
            )
            log(f"translated {ticker} [{language}]")
        except Exception as error:
            log(f"translation failed {ticker} [{language}]: {error}")

    await asyncio.gather(*(one(language) for language in languages))
