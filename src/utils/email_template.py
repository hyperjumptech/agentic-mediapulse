"""Render a newsletter (our markdown format) into a Mediapulse HTML email + plain text.

Ported from the Hyperjump react-email `default-newsletter` template, so the layout and
styling match: a white 600px card, section labels, per-item summaries with a "Read" link,
hairline separators, and a Mediapulse / Hyperjump branding footer.
"""

import html as _html
import re

DEFAULT_MEDIAPULSE_SITE_URL = "https://mediapulse.hyperjump.tech"
DEFAULT_HYPERJUMP_SITE_URL = "https://hyperjump.tech"

_TITLE = re.compile(r"(?m)^#\s+(.+)$")
_READ = re.compile(r"\[Read:\s*([^\]]*)\]\(([^)\s]+)\)")
_INLINE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")

# Inline styles mirroring the react-email template.
_MAIN = (
    "background-color:#f6f9fc;"
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Ubuntu,sans-serif;"
    "margin:0;padding:0;"
)
_CONTAINER = "background-color:#ffffff;margin:0 auto;padding:24px 20px 32px;max-width:600px;"
_HEADING = "color:#1a1a1a;font-size:24px;font-weight:600;line-height:1.3;margin:0;"
_STANDFIRST = "color:#374151;font-size:17px;line-height:1.6;margin:12px 0 0;"
_HR = "border:none;border-top:1px solid #e6ebf1;margin:20px 0;"
_SECTION_LABEL = "color:#1a1a1a;font-size:18px;font-weight:600;line-height:1.3;margin:0 0 12px;"
_ITEM_SUMMARY = "color:#374151;font-size:16px;line-height:1.6;margin:0;"
_ITEM_LINK = "color:#374151;font-size:14px;line-height:1.5;margin:8px 0 0;"
_ITEM_SEP = "border:none;border-top:1px solid #e6ebf1;margin:16px 0;"
_BRANDING = "color:#374151;font-size:13px;line-height:1.5;margin:0 0 12px;"
_FOOTER = "color:#6b7280;font-size:12px;line-height:1.5;margin:0 0 8px;"
_FOOTER_MUTED = "color:#9ca3af;font-size:12px;margin:0;"
_LINK = "color:#2563eb;text-decoration:underline;"


def _inline(text: str) -> str:
    """Escape text and turn inline `[label](https://…)` into anchors; newlines to <br>."""
    out: list[str] = []
    last = 0
    for match in _INLINE.finditer(text):
        out.append(_html.escape(text[last : match.start()]))
        label = _html.escape(match.group(1))
        url = _html.escape(match.group(2), quote=True)
        out.append(f'<a href="{url}" style="{_LINK}">{label}</a>')
        last = match.end()
    out.append(_html.escape(text[last:]))

    return "".join(out).replace("\n", "<br>")


def _parse(markdown: str) -> tuple[str, str, list[tuple[str, list[dict]]]]:
    title_match = _TITLE.search(markdown)
    title = title_match.group(1).strip() if title_match else "Newsletter"
    body = markdown[title_match.end() :] if title_match else markdown

    parts = re.split(r"(?m)^##\s+(.+)$", body)
    summary = parts[0].strip()

    sections: list[tuple[str, list[dict]]] = []
    for index in range(1, len(parts), 2):
        name = parts[index].strip()
        content = parts[index + 1] if index + 1 < len(parts) else ""
        items: list[dict] = []
        for block in re.split(r"(?m)^\s*---\s*$", content):
            link = _READ.search(block)
            if not link:
                continue
            text = re.sub(r"\n{2,}", "\n", _READ.sub("", block)).strip()
            items.append({"summary": text, "title": link.group(1).strip(), "url": link.group(2).strip()})
        sections.append((name, items))

    return title, summary, sections


def render_newsletter_email(
    markdown: str,
    *,
    subject_symbol: str | None = None,
    unsubscribe_url: str | None = None,
    footer_note: str | None = None,
    mediapulse_site_url: str = DEFAULT_MEDIAPULSE_SITE_URL,
    hyperjump_site_url: str = DEFAULT_HYPERJUMP_SITE_URL,
) -> dict[str, str]:
    """Return ``{"subject", "html", "text"}`` for the newsletter markdown."""
    title, summary, sections = _parse(markdown)

    if footer_note is None:
        subject = (subject_symbol or "").strip()
        footer_note = (
            f"You are receiving this because you subscribed to {subject} updates."
            if subject
            else "You are receiving this because you subscribed to updates."
        )

    html_parts = [
        f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'></head>"
        f'<body style="{_MAIN}"><div style="{_CONTAINER}">',
        f'<h1 style="{_HEADING}">{_html.escape(title)}</h1>',
    ]
    if summary:
        html_parts.append(f'<p style="{_STANDFIRST}">{_inline(summary)}</p>')
    html_parts.append(f'<hr style="{_HR}">')

    for name, items in sections:
        if not items:
            continue
        html_parts.append(f'<h2 style="{_SECTION_LABEL}">{_html.escape(name)}</h2>')
        for position, item in enumerate(items):
            html_parts.append(f'<p style="{_ITEM_SUMMARY}">{_inline(item["summary"])}</p>')
            if item["url"]:
                cta = _html.escape(item["title"] or "the source")
                url = _html.escape(item["url"], quote=True)
                html_parts.append(f'<p style="{_ITEM_LINK}"><a href="{url}" style="{_LINK}">Read: {cta}</a></p>')
            if position < len(items) - 1:
                html_parts.append(f'<hr style="{_ITEM_SEP}">')
        html_parts.append(f'<hr style="{_HR}">')

    html_parts.append(
        f'<p style="{_BRANDING}">Brought to you by '
        f'<a href="{_html.escape(mediapulse_site_url, quote=True)}" style="{_LINK}">Mediapulse</a>, '
        f'a product of <a href="{_html.escape(hyperjump_site_url, quote=True)}" style="{_LINK}">Hyperjump</a>.</p>'
    )
    html_parts.append(f'<p style="{_FOOTER}">{_html.escape(footer_note)}</p>')
    if unsubscribe_url:
        label = _html.escape(subject_symbol or "these")
        url = _html.escape(unsubscribe_url, quote=True)
        html_parts.append(
            f'<p style="{_FOOTER_MUTED}"><a href="{url}" style="{_LINK}">Unsubscribe from {label} updates</a></p>'
        )
    html_parts.append("</div></body></html>")

    text_lines = [title, "", summary, ""] if summary else [title, ""]
    for name, items in sections:
        if not items:
            continue
        text_lines.append(name)
        for item in items:
            text_lines.append(item["summary"])
            if item["url"]:
                text_lines.append(f"Read {item['title']}: {item['url']}")
            text_lines.append("---")
        text_lines.append("")
    text_lines.append(footer_note)

    return {"subject": title, "html": "".join(html_parts), "text": "\n".join(text_lines).strip()}
