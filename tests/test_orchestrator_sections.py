import agents.orchestrator as orchestrator

_DRAFT = (
    "Some chatter here\n"
    "Apple launched a new chip today.\n"
    "[Read: Apple chip](https://site.com/apple-new-chip-launch)\n"
    "---\n"
    "## stray heading\n"
    "Top gainers on the IHSG rallied.\n"
    "[Read: market](https://site.com/ihsg-top-gainers-today)\n"
    "---\n"
    "Acme Bank opened a branch in Jakarta.\n"
    "[Read: BCA](https://site.com/bca-branch-jakarta-opening)\n"
)


def test_clean_section_keeps_well_formed_entries_only():
    cleaned = orchestrator._clean_section(_DRAFT)
    assert "Apple launched a new chip today." in cleaned
    assert "Acme Bank opened a branch in Jakarta." in cleaned
    assert "## stray heading" not in cleaned
    assert "Some chatter here" not in cleaned


def test_clean_section_drops_market_noise():
    cleaned = orchestrator._clean_section(_DRAFT)
    assert "IHSG" not in cleaned
    assert "ihsg-top-gainers-today" not in cleaned


def test_clean_section_caps_at_five_entries():
    entry = "Thing number {n} happened in the market.\n[Read: t{n}](https://site.com/story-number-{n}-today)\n---\n"
    draft = "".join(entry.format(n=index) for index in range(8))
    cleaned = orchestrator._clean_section(draft)
    assert cleaned.count("[Read:") == 5


def test_section_problems_flags_too_few_entries():
    draft = "Only one entry here.\n[Read: a](https://site.com/a-b-c-story)\n---\n"
    problems = orchestrator._section_problems(draft, {"https://site.com/a-b-c-story"})
    assert any("at least 2" in problem for problem in problems)


def test_section_problems_flags_urls_not_in_sources():
    allowed = {"https://site.com/apple-new-chip-launch"}
    problems = orchestrator._section_problems(_DRAFT, allowed)
    assert any("ihsg-top-gainers-today" in problem for problem in problems)
    assert any("bca-branch-jakarta-opening" in problem for problem in problems)
    assert all("apple-new-chip-launch" not in problem for problem in problems)


def test_dedupe_urls_drops_repeated_entry():
    newsletter = (
        "# ACME Pulse: Title\n\nSummary sentence.\n\n"
        "## Competitive Landscape\n"
        "Entry one happened.\n\n[Read: a](https://site.com/entry-one-story)\n\n---\n\n"
        "Entry one happened.\n\n[Read: a](https://site.com/entry-one-story)\n\n---\n"
    )
    deduped = orchestrator._dedupe_urls(newsletter)
    assert deduped.count("https://site.com/entry-one-story") == 1


def test_subject_terms_resolves_canonical_name_and_folds_aliases():
    brief = "Subject: PT Nusantara Sample Sentosa Tbk\nTicker/Exchange: ACME (IDX)\nThemes: a, b"
    name, pattern = orchestrator._subject_terms("ACME", brief)
    assert name == "Nusantara Sample Sentosa"

    folded = pattern.sub(name, "ACME rose while Nusantara Sample Sentosa fell")
    assert folded == "Nusantara Sample Sentosa rose while Nusantara Sample Sentosa fell"


def test_subject_terms_ticker_is_case_sensitive():
    # A ticker spelled like a common word must match case-sensitively, so lowercase prose is untouched.
    _, pattern = orchestrator._subject_terms("PEAR", "Subject: Pear Co\nTicker/Exchange: PEAR")
    folded = pattern.sub("X", "a pear slept, PEAR rose")
    assert folded == "a pear slept, X rose"


def test_canonicalize_subject_collapses_repeated_name():
    brief = "Subject: PT Nusantara Sample Sentosa Tbk\nTicker/Exchange: ACME"
    name, pattern = orchestrator._subject_terms("ACME", brief)
    text = "ACME Nusantara Sample Sentosa announced results"
    result = orchestrator._canonicalize_subject(text, name, pattern)
    assert "Nusantara Sample Sentosa Nusantara Sample Sentosa" not in result


def test_canonicalize_subject_noop_when_pattern_is_none():
    assert orchestrator._canonicalize_subject("unchanged text", "Name", None) == "unchanged text"


def test_assemble_builds_titled_edition_without_double_pulse_prefix():
    drafts = {
        "Quick Hits": "A small but notable thing happened.\n[Read: q](https://site.com/quick-hit-story-today)\n---\n"
    }
    out = orchestrator._assemble("ACME", "ACME Pulse: Big Week", "A strong week.", drafts)
    assert out.startswith("# ACME Pulse: Big Week")
    assert out.count("Pulse:") == 1
    assert "A strong week." in out
    assert "## Quick Hits" in out


def test_assemble_skips_sections_with_no_usable_entries():
    out = orchestrator._assemble("ACME", "Title", "Summary.", {"Quick Hits": "just chatter, no link"})
    assert "## Quick Hits" not in out
