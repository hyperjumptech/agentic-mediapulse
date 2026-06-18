import utils.mailer as mailer


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _patch_post(monkeypatch, captured):
    def fake_post(url, headers, json, timeout):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return FakeResponse({"id": "email_123"})

    monkeypatch.setattr(mailer.httpx, "post", fake_post)


def test_send_email_builds_payload_and_auth(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "secret-key")
    monkeypatch.setenv("EMAIL_FROM", "News <news@example.com>")
    captured = {}
    _patch_post(monkeypatch, captured)

    result = mailer.send_email("a@b.com", "Subject", "<p>hi</p>", "hi")

    assert result == {"id": "email_123"}
    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["headers"]["Authorization"] == "Bearer secret-key"
    assert captured["json"]["from"] == "News <news@example.com>"
    assert captured["json"]["to"] == ["a@b.com"]
    assert captured["json"]["subject"] == "Subject"
    assert captured["json"]["text"] == "hi"


def test_send_email_accepts_recipient_list_and_omits_empty_text(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "secret-key")
    captured = {}
    _patch_post(monkeypatch, captured)

    mailer.send_email(["a@b.com", "c@d.com"], "S", "<p>h</p>")

    assert captured["json"]["to"] == ["a@b.com", "c@d.com"]
    assert "text" not in captured["json"]


def test_send_email_uses_default_sender(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "secret-key")
    monkeypatch.delenv("EMAIL_FROM", raising=False)
    captured = {}
    _patch_post(monkeypatch, captured)

    mailer.send_email("a@b.com", "S", "<p>h</p>")

    assert captured["json"]["from"] == "MediaPulse <onboarding@resend.dev>"
