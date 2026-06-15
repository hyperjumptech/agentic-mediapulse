import utils.memory as memory


class Msg:
    def __init__(self, text):
        self.text = text


class MemoryContext:
    def __init__(self, text):
        self.input_messages = [Msg(text)]
        self.added = []

    def extend_instructions(self, source_id, text):
        self.added.append((source_id, text))


def test_key_normalizes_subject():
    assert memory._key("  HELLO ") == "mediapulse:subject:hello"
    assert memory._key("") == "mediapulse:subject:"


def test_remember_subject_writes_with_ttl(monkeypatch):
    captured = {}

    def fake_set(key, value, ex):
        captured.update(key=key, value=value, ex=ex)

    monkeypatch.setattr(memory._client, "set", fake_set)
    monkeypatch.setattr(memory, "_TTL", 1000)
    memory.remember_subject("ACME", "brief text")
    assert captured["key"] == "mediapulse:subject:acme"
    assert captured["value"] == "brief text"
    assert captured["ex"] == 1000


def test_remember_subject_swallows_redis_errors(monkeypatch):
    def boom(*args, **kwargs):
        raise memory.redis.RedisError("down")

    monkeypatch.setattr(memory._client, "set", boom)
    memory.remember_subject("ACME", "brief")  # must not raise


async def test_memory_provider_injects_recalled_brief(monkeypatch):
    monkeypatch.setattr(memory._client, "get", lambda key: "previous brief")
    provider = memory.SubjectMemoryProvider()
    context = MemoryContext("ACME")

    await provider.before_run(agent=None, session=None, context=context, state={})

    assert len(context.added) == 1
    source_id, text = context.added[0]
    assert "previous brief" in text


async def test_memory_provider_noop_when_nothing_recalled(monkeypatch):
    monkeypatch.setattr(memory._client, "get", lambda key: None)
    provider = memory.SubjectMemoryProvider()
    context = MemoryContext("ACME")

    await provider.before_run(agent=None, session=None, context=context, state={})

    assert context.added == []


async def test_memory_provider_survives_redis_error(monkeypatch):
    def boom(key):
        raise memory.redis.RedisError("down")

    monkeypatch.setattr(memory._client, "get", boom)
    provider = memory.SubjectMemoryProvider()
    context = MemoryContext("ACME")

    await provider.before_run(agent=None, session=None, context=context, state={})

    assert context.added == []
