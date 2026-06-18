from typing import Any

from agent_framework import Agent

from agents.runtime.tracking import ACTIVITY_TRACKER, TOOL_TRACKER


def make_agent(**kwargs: Any) -> Agent:
    """Build an Agent with tracking wired in: a shared ActivityTracker, plus a ToolTracker when it has tools."""
    extra_middleware = list(kwargs.pop("middleware", None) or [])
    trackers: list[Any] = [ACTIVITY_TRACKER]

    if kwargs.get("tools"):
        trackers.append(TOOL_TRACKER)

    kwargs["middleware"] = trackers + extra_middleware

    return Agent(**kwargs)
