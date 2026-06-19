import emails.templates.newsletter as email_template

_MARKDOWN = (
    "# ACME Pulse: Big Week\n\nA strong week for ACME.\n\n"
    "## Deals & Movements\n"
    "ACME raised money. [Read: Funding](https://x.com/acme-funding-news)\n\n---\n"
    "## Empty Section\n"
    "no links here, should be skipped\n"
)


def test_inline_escapes_text_and_renders_links():
    rendered = email_template._inline("see [here](https://x.com/p) now\nline2")
    assert '<a href="https://x.com/p"' in rendered
    assert ">here</a>" in rendered
    assert "<br>" in rendered


def test_inline_escapes_html_special_characters():
    assert "&lt;script&gt;" in email_template._inline("<script>")


def test_parse_extracts_title_summary_and_items():
    title, summary, sections = email_template._parse(_MARKDOWN)
    assert title == "ACME Pulse: Big Week"
    assert summary == "A strong week for ACME."

    sections_by_name = dict(sections)
    deals = sections_by_name["Deals & Movements"]
    assert deals[0]["summary"] == "ACME raised money."
    assert deals[0]["title"] == "Funding"
    assert deals[0]["url"] == "https://x.com/acme-funding-news"


def test_parse_defaults_title_when_missing():
    title, _, _ = email_template._parse("no heading here")
    assert title == "Newsletter"


def test_render_returns_subject_html_and_text():
    out = email_template.render_newsletter_email(_MARKDOWN, ticker="ACME")
    assert out["subject"] == "ACME Pulse: Big Week"
    assert 'href="https://x.com/acme-funding-news"' in out["html"]
    assert "Read: Funding" in out["html"]
    assert "A strong week for ACME." in out["text"]
    assert "subscribed to ACME updates" in out["text"]


def test_render_skips_sections_without_items():
    out = email_template.render_newsletter_email(_MARKDOWN)
    assert "Empty Section" not in out["html"]


def test_render_includes_unsubscribe_link_when_url_given():
    out = email_template.render_newsletter_email(_MARKDOWN, ticker="ACME", unsubscribe_url="https://x.com/unsub")
    assert 'href="https://x.com/unsub"' in out["html"]
    assert "Unsubscribe from ACME updates" in out["html"]


def test_render_uses_generic_footer_without_subject():
    out = email_template.render_newsletter_email(_MARKDOWN)
    assert "subscribed to updates" in out["text"]


def test_newsletter_sources_extracts_cited_urls():
    assert email_template.newsletter_sources(_MARKDOWN) == ["https://x.com/acme-funding-news"]


def test_newsletter_sources_dedupes_and_preserves_order():
    markdown = (
        "# T\n\n## A\n"
        "one [Read: a](https://x.com/1)\n\n---\n"
        "two [Read: b](https://x.com/2)\n\n---\n"
        "three [Read: c](https://x.com/1)\n"
    )
    assert email_template.newsletter_sources(markdown) == ["https://x.com/1", "https://x.com/2"]


def test_newsletter_sources_empty_without_links():
    assert email_template.newsletter_sources("# Title\n\nNo links here.") == []


def test_has_sections_true_for_cited_newsletter():
    assert email_template.has_sections(_MARKDOWN) is True


def test_has_sections_false_without_items():
    assert email_template.has_sections("# ACME Pulse: Big Week\n\nStandfirst only, no sections.\n") is False
