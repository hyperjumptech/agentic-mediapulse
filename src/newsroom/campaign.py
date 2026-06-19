import asyncio
import time

from agents.runtime.tracking import newsletter_scope
from db.mediapulse import fetch_subscriptions
from db.newsletters import create_newsletter, finalize_newsletter
from emails.mailer import send_email
from emails.templates.newsletter import has_sections, newsletter_sources, render_newsletter_email
from newsroom.orchestrator import run_newsletter
from newsroom.translation import store_translations

CONCURRENCY = 3
SEND_INTERVAL = 1.0  # seconds between emails


async def run_campaign(*, subscriptions: list[dict] | None = None, send: bool = False, log=print) -> dict:
    """Generate one newsletter per followed ticker and deliver each the moment it is ready."""
    if subscriptions is None:
        subscriptions = fetch_subscriptions()

    subscribers_by_ticker: dict[str, list[dict]] = {}

    for subscription in subscriptions:
        subscribers_by_ticker.setdefault(subscription["ticker"], []).append(subscription)

    tickers = sorted(subscribers_by_ticker)
    log(f"{len(subscriptions)} subscriptions, {len(tickers)} unique tickers, concurrency {CONCURRENCY}")

    generate_semaphore = asyncio.Semaphore(CONCURRENCY)
    send_lock = asyncio.Lock()
    last_send = 0.0
    delivered: list[dict] = []

    async def deliver(ticker: str, recipients: list[dict], markdown: str, newsletter_id: int | None) -> None:
        nonlocal last_send

        if not has_sections(markdown):
            finalize_newsletter(
                newsletter_id, content=markdown, metadata={"ticker": ticker, "sources": []}, status="failed"
            )
            log(f"skipped {ticker}: newsletter has no sections, not sending")

            return

        email = render_newsletter_email(markdown, ticker=ticker)
        finalize_newsletter(
            newsletter_id, content=markdown, metadata={"ticker": ticker, "sources": newsletter_sources(markdown)}
        )

        for subscription in recipients:
            if send:
                # Serialize sends so the 1/sec limit holds even across concurrently finished tickers.
                async with send_lock:
                    wait = SEND_INTERVAL - (time.monotonic() - last_send)

                    if wait > 0:
                        await asyncio.sleep(wait)

                    send_email(subscription["email"], email["subject"], email["html"], email["text"])
                    last_send = time.monotonic()

                log(f"sent {ticker} -> {subscription['email']}")
            else:
                log(f"[dry-run] would send {ticker} -> {subscription['email']}: {email['subject']}")

            delivered.append({"email": subscription["email"], "ticker": ticker})

    async def process(ticker: str, recipients: list[dict]) -> None:
        newsletter_id = create_newsletter(ticker)

        with newsletter_scope(newsletter_id):
            async with generate_semaphore:
                log(f"generating {ticker} ...")

                try:
                    markdown = await run_newsletter(ticker)
                except Exception as error:
                    finalize_newsletter(newsletter_id, status="failed")
                    log(f"failed {ticker}: {error}")

                    return

                log(f"done {ticker}")

            await deliver(ticker, recipients, markdown, newsletter_id)

            if has_sections(markdown):
                try:
                    await store_translations(newsletter_id, markdown, ticker=ticker, log=log)
                except Exception as error:
                    log(f"translations failed {ticker}: {error}")

    await asyncio.gather(*(process(ticker, recipients) for ticker, recipients in subscribers_by_ticker.items()))

    return {"subscriptions": len(subscriptions), "tickers": tickers, "delivered": delivered, "sent": send}
