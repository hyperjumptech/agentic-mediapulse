import pytest
from agent_framework import AgentResponse, Message, MiddlewareTermination

import agents.runtime.guardrails as guardrails


class Msg:
    def __init__(self, text):
        self.text = text


class GuardContext:
    def __init__(self, messages):
        self.messages = messages
        self.result = None


class FunctionContext:
    def __init__(self, result):
        self.result = result


class AgentContextFake:
    def __init__(self, result, stream=False):
        self.result = result
        self.stream = stream


async def _noop():
    return None


def test_result_text_handles_variants():
    assert guardrails._result_text(None) == ""
    assert guardrails._result_text("hello") == "hello"
    assert guardrails._result_text(["a", "b"]) == "a b"

    class HasText:
        text = "from-attr"

    assert guardrails._result_text(HasText()) == "from-attr"


async def test_subject_guardrail_blocks_empty_input():
    context = GuardContext([Msg("   ")])
    with pytest.raises(MiddlewareTermination):
        await guardrails.SubjectGuardrail().process(context, _noop)
    assert "provide a subject" in context.result.text.lower()


async def test_subject_guardrail_passes_real_subject():
    called = {"next": False}

    async def call_next():
        called["next"] = True

    context = GuardContext([Msg("ACME")])
    await guardrails.SubjectGuardrail().process(context, call_next)
    assert called["next"] is True


async def test_record_sources_collects_urls():
    registry = guardrails.SourceRegistry()
    context = FunctionContext("see https://a.com/1 and https://a.com/2 now")
    await guardrails.RecordSources(registry).process(context, _noop)
    assert registry.urls == {"https://a.com/1", "https://a.com/2"}


async def test_enforce_citations_strips_uncited_lines():
    registry = guardrails.SourceRegistry()
    registry.urls = {"https://good.com/x"}
    text = "Cited https://good.com/x\nUncited https://bad.com/y\nNo url here"
    response = AgentResponse(messages=[Message(role="assistant", contents=[text])])
    context = AgentContextFake(response)

    await guardrails.EnforceCitations(registry).process(context, _noop)

    result = context.result.text
    assert "https://good.com/x" in result
    assert "https://bad.com/y" not in result
    assert "No url here" in result


async def test_enforce_citations_noop_when_registry_empty():
    registry = guardrails.SourceRegistry()  # no urls recorded
    text = "Uncited https://bad.com/y"
    response = AgentResponse(messages=[Message(role="assistant", contents=[text])])
    context = AgentContextFake(response)

    await guardrails.EnforceCitations(registry).process(context, _noop)

    assert "https://bad.com/y" in context.result.text
