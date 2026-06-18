import asyncio
from typing import Any

from agent_framework import AgentSession, ContextProvider, SessionContext

from db.memory import recall_subject


class SubjectMemoryProvider(ContextProvider):
    """Recall a previously resolved brief for the subject from Postgres."""

    SOURCE_ID = "subject_memory"

    def __init__(self) -> None:
        super().__init__(self.SOURCE_ID)

    async def before_run(
        self, *, agent: Any, session: AgentSession | None, context: SessionContext, state: dict[str, Any]
    ) -> None:
        text = context.input_messages[-1].text if context.input_messages else ""
        brief = await asyncio.to_thread(recall_subject, text)

        if brief:
            context.extend_instructions(
                self.source_id,
                f"A previously resolved brief for '{text.strip()}' is below. Verify it is still current, "
                f"then update only what changed:\n{brief}",
            )
