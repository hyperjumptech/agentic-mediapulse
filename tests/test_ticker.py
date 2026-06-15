import utils.ticker as ticker


class Msg:
    def __init__(self, text):
        self.text = text


class TickerContext:
    def __init__(self, text):
        self.input_messages = [Msg(text)]
        self.added = []

    def extend_instructions(self, source_id, text):
        self.added.append((source_id, text))


async def test_provider_injects_profile_details(monkeypatch):
    monkeypatch.setattr(
        ticker, "fetch_ticker_profile", lambda symbol: {"Company": "Acme Sample Corp", "Sector": "Technology"}
    )
    provider = ticker.TickerProfileProvider()
    context = TickerContext("ACME")

    await provider.before_run(agent=None, session=None, context=context, state={})

    assert len(context.added) == 1
    _, text = context.added[0]
    assert "Acme Sample Corp" in text
    assert "- Sector: Technology" in text


async def test_provider_noop_for_blank_subject(monkeypatch):
    monkeypatch.setattr(ticker, "fetch_ticker_profile", lambda symbol: {"Company": "X"})
    provider = ticker.TickerProfileProvider()
    context = TickerContext("   ")

    await provider.before_run(agent=None, session=None, context=context, state={})

    assert context.added == []


async def test_provider_noop_when_profile_missing(monkeypatch):
    monkeypatch.setattr(ticker, "fetch_ticker_profile", lambda symbol: None)
    provider = ticker.TickerProfileProvider()
    context = TickerContext("ACME")

    await provider.before_run(agent=None, session=None, context=context, state={})

    assert context.added == []


async def test_provider_swallows_lookup_errors(monkeypatch):
    def boom(symbol):
        raise RuntimeError("db down")

    monkeypatch.setattr(ticker, "fetch_ticker_profile", boom)
    provider = ticker.TickerProfileProvider()
    context = TickerContext("ACME")

    await provider.before_run(agent=None, session=None, context=context, state={})

    assert context.added == []
