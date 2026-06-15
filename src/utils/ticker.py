import asyncio
from typing import Any

from agent_framework import AgentSession, ContextProvider, SessionContext

from utils.db import fetch_ticker_profile


class TickerProfileProvider(ContextProvider):
    """Enrich the analyst with exchange listing details when the subject is a known ticker."""

    SOURCE_ID = "ticker_profile"

    def __init__(self) -> None:
        super().__init__(self.SOURCE_ID)

    async def before_run(
        self, *, agent: Any, session: AgentSession | None, context: SessionContext, state: dict[str, Any]
    ) -> None:
        symbol = (context.input_messages[-1].text if context.input_messages else "").strip()
        if not symbol:
            return
        try:
            # Run the blocking DB lookup off the event loop; best-effort, never blocks generation.
            profile = await asyncio.to_thread(fetch_ticker_profile, symbol)
        except Exception:
            profile = None
        if not profile:
            return
        details = "\n".join(f"- {label}: {value}" for label, value in profile.items())
        context.extend_instructions(
            self.source_id,
            f"The subject '{symbol}' is a listed stock ticker. Verified company details from the exchange "
            "listing database are below, treat them as ground truth. Anchor the brief on this exact company: "
            "use these for Subject, Ticker/Exchange, Sector, and Key players, and infer Market and Locale "
            "(gl/hl codes) from the headquarters location. Some values are in Indonesian, render them in "
            f"English in the brief:\n{details}",
        )
