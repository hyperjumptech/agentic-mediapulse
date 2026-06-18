import os
from pathlib import Path

from agent_framework import SkillsProvider
from agent_framework.openai import OpenAIChatCompletionClient

SKILLS = SkillsProvider.from_paths(skill_paths=Path(__file__).parent.parent / "skills")


def chat_client(role: str) -> OpenAIChatCompletionClient:
    """Build a chat client for an agent role (model from `<ROLE>_MODEL`, then `OPENAI_MODEL`, then a default)."""
    model = os.getenv(f"{role.upper()}_MODEL") or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    return OpenAIChatCompletionClient(model=model, base_url=os.getenv("OPENAI_BASE_URL"))
