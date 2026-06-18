import agents.providers.memory as memory_provider
import agents.providers.ticker as ticker_provider


class Msg:
    def __init__(self, text):
        self.text = text


class FakeContext:
    def __init__(self, text):
        self.input_messages = [Msg(text)]
        self.added = []

    def extend_instructions(self, source_id, text):
        self.added.append((source_id, text))


async def test_subject_memory_provider_injects_recalled_brief(monkeypatch):
    monkeypatch.setattr(memory_provider, "recall_subject", lambda subject: "previous brief")
    provider = memory_provider.SubjectMemoryProvider()
    context = FakeContext("ACME")

    await provider.before_run(agent=None, session=None, context=context, state={})

    assert len(context.added) == 1
    _source_id, text = context.added[0]
    assert "previous brief" in text


async def test_subject_memory_provider_noop_when_nothing_recalled(monkeypatch):
    monkeypatch.setattr(memory_provider, "recall_subject", lambda subject: None)
    provider = memory_provider.SubjectMemoryProvider()
    context = FakeContext("ACME")

    await provider.before_run(agent=None, session=None, context=context, state={})

    assert context.added == []


async def test_ticker_provider_injects_profile_details(monkeypatch):
    monkeypatch.setattr(
        ticker_provider,
        "fetch_ticker_profile",
        lambda ticker: {"Company": "Acme Sample Corp", "Sector": "Technology"},
    )
    provider = ticker_provider.TickerProfileProvider()
    context = FakeContext("ACME")

    await provider.before_run(agent=None, session=None, context=context, state={})

    assert len(context.added) == 1
    _source_id, text = context.added[0]
    assert "Acme Sample Corp" in text
    assert "- Sector: Technology" in text


async def test_ticker_provider_noop_for_blank_subject(monkeypatch):
    monkeypatch.setattr(ticker_provider, "fetch_ticker_profile", lambda ticker: {"Company": "X"})
    provider = ticker_provider.TickerProfileProvider()
    context = FakeContext("   ")

    await provider.before_run(agent=None, session=None, context=context, state={})

    assert context.added == []


async def test_ticker_provider_noop_when_profile_missing(monkeypatch):
    monkeypatch.setattr(ticker_provider, "fetch_ticker_profile", lambda ticker: None)
    provider = ticker_provider.TickerProfileProvider()
    context = FakeContext("ACME")

    await provider.before_run(agent=None, session=None, context=context, state={})

    assert context.added == []


async def test_ticker_provider_swallows_lookup_errors(monkeypatch):
    def boom(ticker):
        raise RuntimeError("db down")

    monkeypatch.setattr(ticker_provider, "fetch_ticker_profile", boom)
    provider = ticker_provider.TickerProfileProvider()
    context = FakeContext("ACME")

    await provider.before_run(agent=None, session=None, context=context, state={})

    assert context.added == []
