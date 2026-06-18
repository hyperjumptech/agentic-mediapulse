import asyncio
import contextvars
import time
from collections.abc import Awaitable, Callable, Mapping
from contextlib import contextmanager

from agent_framework import (
    AgentContext,
    AgentMiddleware,
    FunctionInvocationContext,
    FunctionMiddleware,
    MiddlewareTermination,
)

from db.agent_activity import log_activity

# The id of the newsletter every agent/tool event in the current run belongs to (None outside a tracked run).
current_newsletter_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "current_newsletter_id", default=None
)
# The name of the agent currently executing, so tool events can be attributed to their agent.
current_agent_name: contextvars.ContextVar[str | None] = contextvars.ContextVar("current_agent_name", default=None)


@contextmanager
def newsletter_scope(newsletter_id: int | None):
    """Bind every agent/tool event inside the block to `newsletter_id` (propagates into asyncio tasks)."""
    token = current_newsletter_id.set(newsletter_id)

    try:
        yield newsletter_id
    finally:
        current_newsletter_id.reset(token)


def _elapsed_ms(start_time: float) -> int:
    return int((time.monotonic() - start_time) * 1000)


def _serialize_arguments(arguments: object) -> object:
    """Reduce tool-call arguments to a JSON-serializable form for the activity `meta` column."""
    if arguments is None:
        return None

    if hasattr(arguments, "model_dump"):
        try:
            return arguments.model_dump(mode="json")
        except Exception:
            return str(arguments)

    if isinstance(arguments, Mapping):
        return dict(arguments)

    return str(arguments)


def _result_text(result: object) -> str:
    if result is None:
        return ""

    if isinstance(result, str):
        return result

    if isinstance(result, (list, tuple)):
        return " ".join(_result_text(item) for item in result)

    return getattr(result, "text", None) or str(result)


async def _log_event(newsletter_id: int | None, **event_fields: object) -> None:
    """Persist one activity event off the event loop. Best-effort: tracking never breaks a run."""
    if newsletter_id is None:
        return

    try:
        await asyncio.to_thread(log_activity, newsletter_id=newsletter_id, **event_fields)
    except Exception:
        pass


class ActivityTracker(AgentMiddleware):
    """Record every agent run: status, duration, and token usage, tied to the current newsletter."""

    async def process(self, context: AgentContext, call_next: Callable[[], Awaitable[None]]) -> None:
        newsletter_id = current_newsletter_id.get()
        agent_name = getattr(context.agent, "name", None) or getattr(context.agent, "id", None) or "agent"
        client = getattr(context.agent, "client", None)
        model = getattr(client, "model", None)
        agent_name_token = current_agent_name.set(agent_name)
        start_time = time.monotonic()
        status, error = "ok", None

        try:
            await call_next()
        except MiddlewareTermination:
            status = "terminated"

            raise
        except Exception as exception:
            status, error = "error", f"{type(exception).__name__}: {exception}"

            raise
        finally:
            current_agent_name.reset(agent_name_token)
            result = context.result
            usage_details = getattr(result, "usage_details", None) or {}

            await _log_event(
                newsletter_id,
                kind="agent",
                name=agent_name,
                model=model,
                status=status,
                duration_ms=_elapsed_ms(start_time),
                input_tokens=usage_details.get("input_token_count"),
                output_tokens=usage_details.get("output_token_count"),
                total_tokens=usage_details.get("total_token_count"),
                error=error,
                meta={"finish_reason": getattr(result, "finish_reason", None)},
            )


class ToolTracker(FunctionMiddleware):
    """Record every tool call: status, duration, arguments, and the owning agent."""

    async def process(self, context: FunctionInvocationContext, call_next: Callable[[], Awaitable[None]]) -> None:
        newsletter_id = current_newsletter_id.get()
        tool_name = getattr(context.function, "name", None) or "tool"
        start_time = time.monotonic()
        status, error = "ok", None

        try:
            await call_next()
        except Exception as exception:
            status, error = "error", f"{type(exception).__name__}: {exception}"

            raise
        finally:
            await _log_event(
                newsletter_id,
                kind="tool",
                name=tool_name,
                status=status,
                duration_ms=_elapsed_ms(start_time),
                error=error,
                meta={
                    "agent": current_agent_name.get(),
                    "arguments": _serialize_arguments(context.arguments),
                    "result_chars": len(_result_text(context.result)),
                },
            )


ACTIVITY_TRACKER = ActivityTracker()
TOOL_TRACKER = ToolTracker()
