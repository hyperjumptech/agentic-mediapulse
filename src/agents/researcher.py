from agent_framework import Agent

from agents.runtime.chat_client import SKILLS, chat_client
from agents.runtime.guardrails import RecordSources, SourceRegistry
from agents.runtime.make_agent import make_agent
from agents.sections import Section
from agents.tools import search


def make_researcher(section: Section, registry: SourceRegistry) -> Agent:
    """A news researcher for one beat: finds and ranks candidate articles."""
    return make_agent(
        name=f"researcher_{section.slug}",
        description=f"Finds and ranks sources for the {section.name} beat.",
        client=chat_client("researcher"),
        instructions=(
            f"You are a news researcher for the '{section.name}' beat ({section.focus}). "
            "Consult the **section-research** skill for search strategy, article selection criteria, and what to skip. "
            "Return the 8 most relevant candidates, each as: title, real URL, date, and a one-line note on why it "
            "matters, written in English. The writer needs at least 2 and up to 5 strong, distinct stories. "
            "You may query in the subject's local language. Never invent a URL. Output only the list, no preamble."
        ),
        tools=[search],
        context_providers=[SKILLS],
        middleware=[RecordSources(registry)],
    )
