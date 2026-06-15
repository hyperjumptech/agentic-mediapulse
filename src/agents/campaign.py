import asyncio
import time

from agents.orchestrator import run_newsletter
from utils.db import fetch_subscriptions
from utils.email_template import render_newsletter_email
from utils.mailer import send_email

CONCURRENCY = 3
SEND_INTERVAL = 1.0  # seconds between emails — keeps us under Resend's rate limit (1/sec)


async def run_campaign(*, subscriptions: list[dict] | None = None, send: bool = False, log=print) -> dict:
    """Generate one newsletter per followed ticker and deliver each the moment it is ready.

    Tickers are generated at most CONCURRENCY at a time. As soon as a ticker's newsletter is
    done it is sent to that ticker's subscribers and then dropped, so the whole batch is never
    held in memory at once. Sends are globally rate-limited to one email per SEND_INTERVAL
    seconds. `send=False` is a dry run: it generates and renders but does not email.
    Pass `subscriptions` to scope the run (e.g. one user); defaults to all active subscribers.
    """
    if subscriptions is None:
        subscriptions = fetch_subscriptions()

    subscribers_by_ticker: dict[str, list[dict]] = {}
    for subscription in subscriptions:
        subscribers_by_ticker.setdefault(subscription["symbol"], []).append(subscription)
    tickers = sorted(subscribers_by_ticker)
    log(f"{len(subscriptions)} subscriptions, {len(tickers)} unique tickers, concurrency {CONCURRENCY}")

    generate_semaphore = asyncio.Semaphore(CONCURRENCY)
    send_lock = asyncio.Lock()
    last_send = 0.0
    delivered: list[dict] = []

    async def deliver(symbol: str, recipients: list[dict], markdown: str) -> None:
        nonlocal last_send
        email = render_newsletter_email(markdown, subject_symbol=symbol)
        for subscription in recipients:
            if send:
                # Serialize sends so the 1/sec limit holds even across concurrently finished tickers.
                async with send_lock:
                    wait = SEND_INTERVAL - (time.monotonic() - last_send)
                    if wait > 0:
                        await asyncio.sleep(wait)
                    send_email(subscription["email"], email["subject"], email["html"], email["text"])
                    last_send = time.monotonic()
                log(f"sent {symbol} -> {subscription['email']}")
            else:
                log(f"[dry-run] would send {symbol} -> {subscription['email']}: {email['subject']}")
            delivered.append({"email": subscription["email"], "symbol": symbol})

    async def process(symbol: str, recipients: list[dict]) -> None:
        async with generate_semaphore:
            log(f"generating {symbol} ...")
            try:
                markdown = await run_newsletter(symbol)
            except Exception as error:
                log(f"failed {symbol}: {error}")
                return
            log(f"done {symbol}")
        # Generation slot is freed above; send now, then `markdown` falls out of scope and is released.
        await deliver(symbol, recipients, markdown)

    await asyncio.gather(*(process(symbol, recipients) for symbol, recipients in subscribers_by_ticker.items()))

    return {"subscriptions": len(subscriptions), "tickers": tickers, "delivered": delivered, "sent": send}
