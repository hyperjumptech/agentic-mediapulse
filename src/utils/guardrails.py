import re
from collections.abc import Awaitable, Callable

from agent_framework import (
    AgentContext,
    AgentMiddleware,
    AgentResponse,
    FunctionInvocationContext,
    FunctionMiddleware,
    Message,
    MiddlewareTermination,
)

_URL = re.compile(r"https?://[^\s\)]+")


class SubjectGuardrail(AgentMiddleware):
    """Block requests that carry no subject to research."""

    async def process(self, context: AgentContext, call_next: Callable[[], Awaitable[None]]) -> None:
        last = context.messages[-1] if context.messages else None
        if not (last and last.text and last.text.strip()):
            context.result = AgentResponse(
                messages=[
                    Message(
                        role="assistant",
                        contents=["Please provide a subject, e.g. a ticker (BBCA), a company, or an industry."],
                    )
                ]
            )
            raise MiddlewareTermination(result=context.result)

        await call_next()


class SourceRegistry:
    """Collects every URL the search tools actually returned during a run."""

    def __init__(self) -> None:
        self.urls: set[str] = set()


def _result_text(result: object) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    if isinstance(result, (list, tuple)):
        return " ".join(_result_text(item) for item in result)

    return getattr(result, "text", None) or str(result)


class RecordSources(FunctionMiddleware):
    """Capture URLs from each search tool result into a shared registry."""

    def __init__(self, registry: SourceRegistry) -> None:
        self.registry = registry

    async def process(self, context: FunctionInvocationContext, call_next: Callable[[], Awaitable[None]]) -> None:
        await call_next()
        self.registry.urls.update(_URL.findall(_result_text(context.result)))


class EnforceCitations(AgentMiddleware):
    """Strip any Read link whose URL was never returned by a search."""

    def __init__(self, registry: SourceRegistry) -> None:
        self.registry = registry

    async def process(self, context: AgentContext, call_next: Callable[[], Awaitable[None]]) -> None:
        await call_next()
        if context.stream or context.result is None or not self.registry.urls:
            return

        for message in context.result.messages:
            for content in message.contents:
                if getattr(content, "type", None) != "text" or not content.text:
                    continue
                kept = []
                for line in content.text.splitlines():
                    urls = _URL.findall(line)
                    if urls and not all(url in self.registry.urls for url in urls):
                        continue
                    kept.append(line)
                content.text = "\n".join(kept)
