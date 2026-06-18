import asyncio
import re
import urllib.parse

from agents.analyst import analyst
from agents.beats import BEATS
from agents.editor import editor
from agents.managing_editor import managing_editor
from agents.reviewer import reviewer
from agents.sections import SECTIONS
from db.memory import remember_subject

_URL_RE = re.compile(r"https?://[^\s\)]+")
_READ_RE = re.compile(r"\[Read:[^\]]*\]\(([^)]*)\)")
_LISTING_PARAMS = {"l", "page", "p", "start", "offset", "q", "s", "query", "cat", "category"}
RETRIES = 2
DISCUSSION_ROUNDS = 3  # newsroom roundtable: max rounds of gap-finding + targeted fill-in (early-exits on COMPLETE)
MAX_GAPS_PER_ROUND = 3
_GAP_RE = re.compile(r"^\s*[-*•]?\s*(.+?)\s*::\s*(.+?)\s*$")


def _is_ok(verdict: str) -> bool:
    return verdict.strip().upper().startswith("OK")


def _humanize(text: str) -> str:
    """Strip em/en dashes and semicolons from prose so it reads like a person wrote it."""
    text = re.sub(r"(?<=\d)\s*[—–]\s*(?=\d)", "-", text)  # keep number ranges: 200–250 -> 200-250
    text = re.sub(r"\s*[—–]\s*", ", ", text)
    text = text.replace(";", ",")
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r",\s*,", ", ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()


def _is_article(url: str) -> bool:
    """True only for links that look like a single article, not a listing/index/category page."""
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return False

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False

    segments = [segment for segment in parsed.path.split("/") if segment]

    if not segments:
        return False

    if parsed.query and {key.lower() for key in urllib.parse.parse_qs(parsed.query)} & _LISTING_PARAMS:
        return False

    slug = re.sub(r"\.(html?|aspx?|php|jsp)$", "", segments[-1], flags=re.IGNORECASE)

    return slug.count("-") >= 2 or bool(re.fullmatch(r"\d{4,}", slug))


# --- deterministic check (objective gate; feedback is routed back to the agent) ---


def _section_problems(draft: str, allowed_urls: set[str]) -> list[str]:
    problems: list[str] = []
    reads = _READ_RE.findall(draft)

    if len(reads) < 2:
        problems.append(
            "Include at least 2 and at most 5 entries, each a single sentence"
            " ending with a '[Read: <title>](<url>)' line."
        )

    for raw in reads:
        url = raw.strip()

        if not url.startswith("http"):
            problems.append(f"Entry has no real URL: {url or '(empty)'}")
        elif url not in allowed_urls:
            problems.append(f"URL not from the researched sources: {url}")
        elif not _is_article(url):
            problems.append(f"URL is a listing/index/category page, not an article — cite a specific story: {url}")

    return problems


async def _profile(subject: str) -> str:
    return (await analyst.run(subject)).text


async def _run_beat(beat, brief: str) -> tuple[str, str]:
    section = beat.section
    head = f"{brief}\n\nBEAT: {section.name} — {section.focus}"

    # researcher finds sources; deterministic sufficiency feedback
    candidates, note = "", ""

    for _ in range(RETRIES):
        candidates = (await beat.researcher.run(head + note)).text

        if len({*_URL_RE.findall(candidates)}) >= 3:
            break

        note = "\n\nFEEDBACK: too few sources with real URLs, widen recency to 'week' or try different queries."

    # writer drafts from candidates; deterministic citation/format feedback
    draft, feedback = "", ""

    for _ in range(RETRIES + 1):
        draft = (
            await beat.writer.run(f"BRIEF:\n{brief}\n\nCANDIDATES:\n{candidates}\n\nSECTION: {section.name}{feedback}")
        ).text
        problems = _section_problems(draft, beat.registry.urls)

        if not problems:
            break

        feedback = "\n\nFEEDBACK (fix these):\n- " + "\n- ".join(problems)

    # editor reviews the section (agent feedback -> one writer revision)
    verdict = (await editor.run(f"REVIEW the '{section.name}' section:\n\n{draft}")).text

    if not _is_ok(verdict):
        draft = (
            await beat.writer.run(
                f"BRIEF:\n{brief}\n\nCANDIDATES:\n{candidates}\n\nSECTION: {section.name}\n\n"
                f"EDITOR FEEDBACK:\n{verdict}\n\nRewrite the entries addressing the feedback."
            )
        ).text

    return section.name, draft


async def _cover_beats(brief: str) -> dict[str, str]:
    results = await asyncio.gather(*(_run_beat(beat, brief) for beat in BEATS))

    return dict(results)


def _gaps_from(verdict: str, sections: set[str]) -> list[tuple[str, str]]:
    """Parse the managing editor's 'Section :: missing angle' lines into known-section gaps."""
    gaps: list[tuple[str, str]] = []

    for line in verdict.splitlines():
        match = _GAP_RE.match(line)

        if not match:
            continue

        section, need = match.group(1).strip(), match.group(2).strip()

        if section in sections and need:
            gaps.append((section, need))

    return gaps


async def _fill_gap(beat, brief: str, need: str) -> str:
    """Targeted research and write for one missing angle. Best-effort: returns '' on failure."""
    try:
        candidates = (
            await beat.researcher.run(f"{brief}\n\nFind recent, real sources specifically about: {need}")
        ).text
        draft = await beat.writer.run(
            f"BRIEF:\n{brief}\n\nCANDIDATES:\n{candidates}\n\nSECTION: {beat.section.name}\n"
            f"Add coverage of this specific angle: {need}"
        )

        return draft.text
    except Exception:
        return ""


async def _newsroom_discussion(brief: str, drafts: dict[str, str]) -> dict[str, str]:
    """Manager-driven roundtable: the managing editor names coverage gaps and the relevant
    beat's researcher and writer fill each one. Bounded to DISCUSSION_ROUNDS, then stops early
    once the editor says the edition is complete. New entries pass the same per-section guards.
    """
    beats_by_name = {beat.section.name: beat for beat in BEATS}

    for _ in range(DISCUSSION_ROUNDS):
        edition = "\n\n".join(f"## {section.name}\n{drafts[section.name]}" for section in SECTIONS)
        verdict = (await managing_editor.run(f"BRIEF:\n{brief}\n\nCURRENT EDITION:\n{edition}")).text

        if verdict.strip().upper().startswith("COMPLETE"):
            break

        gaps = _gaps_from(verdict, set(beats_by_name))[:MAX_GAPS_PER_ROUND]

        if not gaps:
            break

        additions = await asyncio.gather(*(_fill_gap(beats_by_name[section], brief, need) for section, need in gaps))

        for (section, _), addition in zip(gaps, additions):
            if addition.strip():
                drafts[section] = f"{drafts[section]}\n\n{addition}"

    return drafts


async def _masthead(brief: str, drafts: dict[str, str], notes: str = "") -> tuple[str, str]:
    body = "\n\n".join(f"## {section.name}\n{drafts[section.name]}" for section in SECTIONS)
    prompt = f"MASTHEAD\n\nBRIEF:\n{brief}\n\nSECTION DRAFTS:\n{body}"

    if notes:
        prompt += f"\n\nREVIEWER NOTES (address these):\n{notes}"

    out = (await editor.run(prompt)).text.strip()
    lines = out.splitlines()
    title = lines[0].lstrip("# ").strip() if lines else "Newsletter"
    summary_lines = [line for line in lines[1:] if line.strip().upper().rstrip(".") != "OK"]
    summary = "\n".join(summary_lines).strip()

    return _humanize(title), _first_sentences(_humanize(summary))  # masthead summary stays one sentence


_LINK_RE = re.compile(r"\[Read:[^\]]*\]\([^)]*\)")
_LEADING_MARKER_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
# Split only at real sentence ends: .?! then space then a capital or digit. A decimal such as
# "0.5%" has no space after its dot, so it is never a split point (no mid-number truncation).
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_MAX_SENTENCES = 1
_MAX_WORDS = 45  # also cap comma-spliced run-ons that are technically one sentence
# Stock-index / price / technical-analysis chatter; readers want company news, not market noise.
_MARKET_NOISE_RE = re.compile(
    r"\b(ihsg|jci|top (gainers|losers)|rekomendasi saham|saham pilihan|level psikologis|macd|"
    r"stochastic rsi|golden cross|death cross|support and resistance|resistance level|price target|"
    r"target harga|technical analysis|analisis teknikal)\b",
    re.IGNORECASE,
)
_WORD_RE = re.compile(r"[a-z0-9]+")
_PULSE_PREFIX_RE = re.compile(r"^\s*(\w+\s+)?pulse\s*:\s*", re.IGNORECASE)  # strip an echoed "<TICKER> Pulse:"

# --- subject naming: pin one consistent name for the subject across the whole edition ---
_PT_PREFIX_RE = re.compile(r"^\s*PT\.?\s+", re.IGNORECASE)
_TBK_SUFFIX_RE = re.compile(r"[\s,]+\(?Tbk\)?\.?\s*$", re.IGNORECASE)
_SUBJECT_LINE_RE = re.compile(r"^\s*Subject\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_TICKER_LINE_RE = re.compile(r"^\s*Ticker(?:/Exchange)?\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)


def _short_name(name: str) -> str:
    """Drop the Indonesian legal wrapper so 'PT Dian Swastatika Sentosa Tbk' becomes 'Dian Swastatika Sentosa'."""
    return _TBK_SUFFIX_RE.sub("", _PT_PREFIX_RE.sub("", name)).strip(" ,.")


def _subject_terms(subject: str, brief: str) -> tuple[str, "re.Pattern | None"]:
    """Resolve one canonical display name for the subject plus a pattern matching every alias to fold into it.

    Returns (name, None) when there is nothing worth normalizing, e.g. an industry or theme subject.
    """
    subject = subject.strip()
    match = _SUBJECT_LINE_RE.search(brief)
    raw_name = match.group(1).strip() if match else ""
    name = _short_name(raw_name) or raw_name or subject

    if len(name) < 2:
        return subject, None

    # Company-name aliases match case-insensitively: they are distinctive proper nouns with no common-word risk.
    names: set[str] = {name}

    if raw_name:
        names.update({raw_name, f"PT {name} Tbk", f"PT {name}", f"{name} Tbk"})

    words = name.split()

    if len(words) >= 3:
        names.add(" ".join(words[:2]))  # fold a shortened form back, but never down to one (often generic) word

    # Ticker symbols match case-sensitively only. A ticker like BABY or MAP is a common word in lower case,
    # so folding "baby" or "map" into the company name would wreck the prose; only the all-caps ticker is meant.
    tickers: set[str] = set()
    ticker_match = _TICKER_LINE_RE.search(brief)

    for candidate in (subject, ticker_match.group(1) if ticker_match else ""):
        token = re.split(r"[\s,/(]+", candidate.strip(), maxsplit=1)[0].strip(" .")

        if re.fullmatch(r"[A-Z]{3,6}\d{0,2}", token):  # an uppercase exchange ticker like DSSA or GOTO
            tickers.add(token)

    alternatives = [re.escape(alias) for alias in sorted(names, key=len, reverse=True) if alias]
    alternatives += [f"(?-i:{re.escape(ticker)})" for ticker in sorted(tickers, key=len, reverse=True)]

    if not alternatives:
        return name, None

    pattern = re.compile(r"\b(?:" + "|".join(alternatives) + r")\b", re.IGNORECASE)

    return name, pattern


def _canonicalize_subject(text: str, name: str, pattern: "re.Pattern | None") -> str:
    """Fold every explicit alias of the subject (ticker, legal name, shortened name) to one consistent name.

    Generic back-references like 'the company' or 'it' are left alone, so entries can open in varied, natural
    ways instead of every one leading with the full name.
    """
    if pattern is None:
        return text

    text = pattern.sub(name, text)
    text = re.sub(r"\b(" + re.escape(name) + r")(?:\s+\1\b)+", r"\1", text)  # collapse an accidental "Name Name"

    return text


def _canonical_url(url: str) -> str:
    """Normalize a URL so the same article via different query strings dedupes to one key."""
    try:
        parsed = urllib.parse.urlparse(url.strip().lower())
    except ValueError:
        return url.strip().lower()

    host = parsed.netloc.removeprefix("www.")

    return f"{host}{parsed.path.rstrip('/')}"


def _content_key(text: str) -> frozenset:
    """The significant words of an entry, for near-duplicate detection."""
    return frozenset(word for word in _WORD_RE.findall(text.lower()) if len(word) > 3)


def _too_similar(tokens: frozenset, seen: list, threshold: float = 0.55) -> bool:
    """True if `tokens` overlaps any kept entry at or above `threshold` (Jaccard similarity)."""
    for prior in seen:
        union = tokens | prior

        if union and len(tokens & prior) / len(union) >= threshold:
            return True

    return False


def _first_sentences(text: str, limit: int = _MAX_SENTENCES) -> str:
    """Keep at most `limit` sentences, then cap a comma-spliced run-on at `_MAX_WORDS`.

    Splits only at safe boundaries (never inside a number like "0.5%").
    """
    parts = _SENTENCE_SPLIT_RE.split(text)
    kept = text if len(parts) <= limit else " ".join(parts[:limit])
    words = kept.split()

    if len(words) <= _MAX_WORDS:
        return kept

    clipped = " ".join(words[:_MAX_WORDS])

    if "," in clipped:
        clipped = clipped[: clipped.rfind(",")]  # end on a clause, not mid-thought

    return clipped.rstrip(" ,.;:") + "."


def _clean_section(draft: str, name: str = "", pattern: "re.Pattern | None" = None) -> str:
    """Rebuild a section from only its well-formed entries (summary + Read link + ---).

    Drops agent chatter, stray headings, and trailing commentary by keeping, for each
    Read link, just the prose paragraph directly above it. When `name` is given, every
    alias of the subject in the prose is folded to that one name.
    """
    lines = draft.splitlines()
    entries: list[str] = []

    for index, line in enumerate(lines):
        link = _LINK_RE.search(line)

        if not link:
            continue

        cursor = index - 1

        while cursor >= 0 and not lines[cursor].strip():
            cursor -= 1

        if cursor < 0:
            continue

        body = lines[cursor].strip()

        if body == "---" or body.startswith("#") or _LINK_RE.search(body):
            continue

        body = _LEADING_MARKER_RE.sub("", body)  # drop any leading bullet or number marker

        if _MARKET_NOISE_RE.search(body) or _MARKET_NOISE_RE.search(link.group(0)):
            continue  # drop stock-index / price / technical-analysis noise; readers want company news

        body = _humanize(body)

        if name:
            body = _canonicalize_subject(body, name, pattern)

        body = _first_sentences(body)
        entries.append(f"{body}\n\n{link.group(0)}\n\n---")

    # Cap at the 5 most important entries per section even if the writer drafted more.
    return "\n\n".join(entries[:5])


def _assemble(
    subject: str, title: str, summary: str, drafts: dict[str, str], name: str = "", pattern: "re.Pattern | None" = None
) -> str:
    subject = subject.strip()

    # The editor sometimes echoes a "<TICKER> Pulse:" prefix; strip any leading one so we never double it.
    while _PULSE_PREFIX_RE.match(title):
        title = _PULSE_PREFIX_RE.sub("", title, count=1).strip()

    if name:
        summary = _canonicalize_subject(summary, name, pattern)

    parts = [f"# {subject} Pulse: {title}", "", summary, ""]

    for section in SECTIONS:
        body = _clean_section(drafts.get(section.name, ""), name, pattern)

        if not body.strip():
            continue  # skip a section with no usable entries rather than printing a bare heading

        parts.append(f"## {section.name}")
        parts.append(body)
        parts.append("")

    return "\n".join(parts).strip() + "\n"


def _dedupe_urls(newsletter: str) -> str:
    """Drop entries that repeat an earlier one, by canonical URL or near-identical wording."""
    seen_urls: set[str] = set()
    seen_tokens: list[frozenset] = []
    out: list[str] = []
    entry: list[str] = []

    def flush() -> bool:
        urls = [_canonical_url(url) for url in _URL_RE.findall("\n".join(entry))]
        summary = " ".join(
            line for line in entry if line.strip() and line.strip() != "---" and not _LINK_RE.search(line)
        )
        tokens = _content_key(summary)

        if (urls and any(url in seen_urls for url in urls)) or _too_similar(tokens, seen_tokens):
            entry.clear()
            return False

        seen_urls.update(urls)

        if tokens:
            seen_tokens.append(tokens)

        out.extend(entry)
        entry.clear()

        return True

    for line in newsletter.splitlines():
        stripped = line.strip()

        if stripped == "---":
            if flush():
                out.append(line)
        elif stripped.startswith("#"):
            out.extend(entry)
            entry.clear()
            out.append(line)
        else:
            entry.append(line)

    out.extend(entry)

    return "\n".join(out)


async def run_newsletter(subject: str) -> str:
    brief = await _profile(subject)
    remember_subject(subject, brief)
    name, pattern = _subject_terms(subject, brief)

    drafts = await _cover_beats(brief)
    drafts = await _newsroom_discussion(brief, drafts)
    title, summary = await _masthead(brief, drafts)
    newsletter = _assemble(subject, title, summary, drafts, name, pattern)

    # reviewer critiques the whole edition (agent feedback -> one masthead revision)
    verdict = (await reviewer.run(newsletter)).text

    if not _is_ok(verdict):
        title, summary = await _masthead(brief, drafts, notes=verdict)
        newsletter = _assemble(subject, title, summary, drafts, name, pattern)

    return _dedupe_urls(newsletter)
