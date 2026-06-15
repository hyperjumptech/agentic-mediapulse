from agent_framework import Agent

from agents.tools import search, web_fetch
from utils.client import SKILLS, chat_client
from utils.guardrails import SubjectGuardrail
from utils.memory import SubjectMemoryProvider
from utils.ticker import TickerProfileProvider

analyst = Agent(
    name="analyst",
    description="Resolves a subject into a research brief.",
    client=chat_client("analyst"),
    instructions=(
        "You are a research analyst. The subject may be a ticker, a company, or an industry/theme. "
        "Use the subject-profile skill to turn the subject into a brief."
    ),
    tools=[search, web_fetch],
    context_providers=[SKILLS, TickerProfileProvider(), SubjectMemoryProvider()],
    middleware=[SubjectGuardrail()],
)
