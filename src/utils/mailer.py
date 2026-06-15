import os

import httpx


def send_email(to: str | list[str], subject: str, html: str, text: str | None = None) -> dict:
    """Send an email via the Resend API.

    Reads `RESEND_API_KEY` and the sender from `EMAIL_FROM`. Returns the Resend response JSON.
    """
    payload: dict = {
        "from": os.getenv("EMAIL_FROM", "Mediapulse <onboarding@resend.dev>"),
        "to": [to] if isinstance(to, str) else to,
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text

    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}", "Content-Type": "application/json"},
        json=payload,
        timeout=30.0,
    )
    response.raise_for_status()

    return response.json()
