import pytest
from agent_framework import MiddlewareTermination

import agents.runtime.tracking as tracking


class FakeClient:
    model = "gpt-test"


class FakeAgent:
    name = "analyst"
    client = FakeClient()


class FakeResult:
    def __init__(self, usage=None, finish_reason="stop"):
        self.usage_details = usage or {}
        self.finish_reason = finish_reason


class FakeAgentContext:
    def __init__(self):
        self.agent = FakeAgent()
        self.result = None


class FakeFunction:
    name = "search"


class FakeToolContext:
    def __init__(self, arguments, result):
        self.function = FakeFunction()
        self.arguments = arguments
        self.result = result


def _capture(monkeypatch):
    events = []

    def fake_log_activity(**kwargs):
        events.append(kwargs)

    monkeypatch.setattr(tracking, "log_activity", fake_log_activity)

    return events


async def test_activity_tracker_records_ok(monkeypatch):
    events = _capture(monkeypatch)
    context = FakeAgentContext()

    async def call_next():
        context.result = FakeResult(usage={"input_token_count": 10, "output_token_count": 4, "total_token_count": 14})

    with tracking.newsletter_scope(42):
        await tracking.ActivityTracker().process(context, call_next)

    assert len(events) == 1
    event = events[0]
    assert event["newsletter_id"] == 42
    assert event["kind"] == "agent"
    assert event["name"] == "analyst"
    assert event["model"] == "gpt-test"
    assert event["status"] == "ok"
    assert event["total_tokens"] == 14
    assert event["meta"] == {"finish_reason": "stop"}


async def test_activity_tracker_records_termination(monkeypatch):
    events = _capture(monkeypatch)
    context = FakeAgentContext()

    async def call_next():
        raise MiddlewareTermination(result=None)

    with tracking.newsletter_scope(1):
        with pytest.raises(MiddlewareTermination):
            await tracking.ActivityTracker().process(context, call_next)

    assert events[0]["status"] == "terminated"


async def test_activity_tracker_records_error(monkeypatch):
    events = _capture(monkeypatch)
    context = FakeAgentContext()

    async def call_next():
        raise RuntimeError("boom")

    with tracking.newsletter_scope(1):
        with pytest.raises(RuntimeError):
            await tracking.ActivityTracker().process(context, call_next)

    assert events[0]["status"] == "error"
    assert "RuntimeError: boom" == events[0]["error"]


async def test_activity_tracker_skips_outside_scope(monkeypatch):
    events = _capture(monkeypatch)
    context = FakeAgentContext()

    async def call_next():
        context.result = FakeResult()

    await tracking.ActivityTracker().process(context, call_next)  # no newsletter_scope active

    assert events == []


async def test_tool_tracker_records_call(monkeypatch):
    events = _capture(monkeypatch)
    context = FakeToolContext(arguments={"query": "ACME news"}, result="some result text")

    async def call_next():
        return None

    with tracking.newsletter_scope(5):
        await tracking.ToolTracker().process(context, call_next)

    assert len(events) == 1
    event = events[0]
    assert event["newsletter_id"] == 5
    assert event["kind"] == "tool"
    assert event["name"] == "search"
    assert event["status"] == "ok"
    assert event["meta"]["arguments"] == {"query": "ACME news"}
    assert event["meta"]["result_chars"] == len("some result text")
