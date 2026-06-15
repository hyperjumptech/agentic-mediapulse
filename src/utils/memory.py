import os
from typing import Any

import redis
from agent_framework import AgentSession, ContextProvider, SessionContext

_PREFIX = "mediapulse:subject:"
_TTL = int(os.getenv("SUBJECT_TTL", "604800"))  # briefs expire after 7 days by default; 0 = never
_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)


def _key(subject: str) -> str:
    return _PREFIX + (subject or "").strip().lower()


def remember_subject(subject: str, brief: str) -> None:
    """Persist a resolved brief for a subject to Redis (best-effort; no-op if Redis is down)."""
    try:
        _client.set(_key(subject), brief, ex=_TTL or None)
    except redis.RedisError:
        pass


class SubjectMemoryProvider(ContextProvider):
    """Recall a previously resolved brief for the subject from Redis."""

    SOURCE_ID = "subject_memory"

    def __init__(self) -> None:
        super().__init__(self.SOURCE_ID)

    async def before_run(
        self, *, agent: Any, session: AgentSession | None, context: SessionContext, state: dict[str, Any]
    ) -> None:
        text = context.input_messages[-1].text if context.input_messages else ""
        try:
            brief = _client.get(_key(text))
        except redis.RedisError:
            brief = None
        if brief:
            context.extend_instructions(
                self.source_id,
                f"A previously resolved brief for '{text.strip()}' is below. Verify it is still current, "
                f"then update only what changed:\n{brief}",
            )
