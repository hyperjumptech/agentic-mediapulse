import logging
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException

from agents.campaign import run_campaign
from db.mediapulse import fetch_subscriptions

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="MediaPulse Newsletter API")
logger = logging.getLogger("mediapulse.api")


def require_api_key(x_api_key: str = Header(default="")) -> None:
    """Reject requests whose `X-API-Key` header does not match the `SECRET_KEY` env var."""
    expected = os.getenv("SECRET_KEY", "")

    if not expected:
        raise HTTPException(status_code=503, detail="Server missing SECRET_KEY")

    if not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


async def _run_all(send: bool) -> None:
    try:
        result = await run_campaign(send=send, log=logger.info)
        logger.info("campaign finished: %s delivered (send=%s)", len(result["delivered"]), send)
    except Exception:
        logger.exception("campaign failed")


async def _run_user(email: str, send: bool) -> None:
    try:
        subscriptions = fetch_subscriptions(email=email)
        await run_campaign(subscriptions=subscriptions, send=send, log=logger.info)
        logger.info("test run for %s finished (send=%s)", email, send)
    except Exception:
        logger.exception("test run for %s failed", email)


@app.post("/run", status_code=202, dependencies=[Depends(require_api_key)])
async def run(background: BackgroundTasks, dry_run: bool = True) -> dict:
    """Start the full campaign in the background and return immediately.

    Every followed ticker is generated (max 3 in parallel) and delivered to all subscribers.
    `dry_run=true` (default) generates and renders but does not email.
    """
    background.add_task(_run_all, send=not dry_run)

    return {"status": "started", "scope": "all", "dry_run": dry_run}


@app.post("/test", status_code=202, dependencies=[Depends(require_api_key)])
async def test(email: str, background: BackgroundTasks, dry_run: bool = True) -> dict:
    """Start a single-user run in the background and return immediately.

    Generates the user's followed tickers and emails only them. `dry_run=true` (default)
    generates and renders but does not email.
    """
    background.add_task(_run_user, email=email, send=not dry_run)

    return {"status": "started", "scope": email, "dry_run": dry_run}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
