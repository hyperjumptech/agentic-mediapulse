import agents.runtime.chat_client as client


class FakeChatClient:
    def __init__(self, *, model, base_url):
        self.model = model
        self.base_url = base_url


def _patch(monkeypatch):
    monkeypatch.setattr(client, "OpenAIChatCompletionClient", FakeChatClient)


def test_chat_client_prefers_role_specific_model(monkeypatch):
    _patch(monkeypatch)
    monkeypatch.setenv("RESEARCHER_MODEL", "role-model")
    monkeypatch.setenv("OPENAI_MODEL", "general-model")
    assert client.chat_client("researcher").model == "role-model"


def test_chat_client_falls_back_to_openai_model(monkeypatch):
    _patch(monkeypatch)
    monkeypatch.delenv("WRITER_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "general-model")
    assert client.chat_client("writer").model == "general-model"


def test_chat_client_uses_default_model(monkeypatch):
    _patch(monkeypatch)
    monkeypatch.delenv("EDITOR_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    assert client.chat_client("editor").model == "gpt-4.1-mini"


def test_chat_client_passes_base_url(monkeypatch):
    _patch(monkeypatch)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://proxy.example/v1")
    assert client.chat_client("analyst").base_url == "https://proxy.example/v1"
