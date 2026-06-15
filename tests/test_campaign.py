import agents.campaign as campaign


def _patch_pipeline(monkeypatch, *, fail_for=()):
    async def fake_run_newsletter(symbol):
        if symbol in fail_for:
            raise RuntimeError(f"boom {symbol}")
        return f"# {symbol} markdown"

    sent = []

    monkeypatch.setattr(campaign, "run_newsletter", fake_run_newsletter)
    monkeypatch.setattr(
        campaign, "render_newsletter_email", lambda md, **kw: {"subject": "S", "html": "H", "text": "T"}
    )
    monkeypatch.setattr(campaign, "send_email", lambda *a, **k: sent.append(a))
    monkeypatch.setattr(campaign, "SEND_INTERVAL", 0.0)

    return sent


def _subs():
    return [
        {"email": "a@x.com", "symbol": "ACME"},
        {"email": "b@x.com", "symbol": "ACME"},
        {"email": "c@x.com", "symbol": "GLOBEX"},
    ]


async def test_dry_run_does_not_send(monkeypatch):
    sent = _patch_pipeline(monkeypatch)
    result = await campaign.run_campaign(subscriptions=_subs(), send=False, log=lambda *a: None)

    assert result["sent"] is False
    assert result["subscriptions"] == 3
    assert result["tickers"] == ["ACME", "GLOBEX"]  # sorted
    assert len(result["delivered"]) == 3
    assert sent == []


async def test_send_delivers_to_every_subscriber(monkeypatch):
    sent = _patch_pipeline(monkeypatch)
    result = await campaign.run_campaign(subscriptions=_subs(), send=True, log=lambda *a: None)

    assert result["sent"] is True
    assert len(sent) == 3
    recipients = {call[0] for call in sent}
    assert recipients == {"a@x.com", "b@x.com", "c@x.com"}


async def test_failed_ticker_is_skipped_others_delivered(monkeypatch):
    _patch_pipeline(monkeypatch, fail_for={"ACME"})
    result = await campaign.run_campaign(subscriptions=_subs(), send=False, log=lambda *a: None)

    delivered_symbols = {entry["symbol"] for entry in result["delivered"]}
    assert delivered_symbols == {"GLOBEX"}


async def test_run_campaign_fetches_subscriptions_when_unset(monkeypatch):
    _patch_pipeline(monkeypatch)
    monkeypatch.setattr(campaign, "fetch_subscriptions", lambda: [{"email": "z@x.com", "symbol": "ACME"}])

    result = await campaign.run_campaign(send=False, log=lambda *a: None)

    assert result["tickers"] == ["ACME"]
    assert result["delivered"] == [{"email": "z@x.com", "symbol": "ACME"}]
