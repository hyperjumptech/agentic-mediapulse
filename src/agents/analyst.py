from agents.providers.memory import SubjectMemoryProvider
from agents.providers.ticker import TickerProfileProvider
from agents.runtime.chat_client import SKILLS, chat_client
from agents.runtime.guardrails import SubjectGuardrail
from agents.runtime.make_agent import make_agent
from agents.tools import web_fetch, web_search

analyst = make_agent(
    name="analyst",
    description="Resolves a subject into a research brief.",
    client=chat_client("analyst"),
    instructions=(
        "You are a research analyst. The subject may be a ticker, a company, or an industry/theme. "
        "Use the subject-profile skill to turn the subject into a brief."
    ),
    tools=[web_search, web_fetch],
    context_providers=[SKILLS, TickerProfileProvider(), SubjectMemoryProvider()],
    middleware=[SubjectGuardrail()],
)
