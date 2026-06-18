from agent_framework import Agent

from agents.runtime.chat_client import SKILLS, chat_client
from agents.runtime.guardrails import EnforceCitations, SourceRegistry
from agents.runtime.make_agent import make_agent
from agents.sections import Section
from agents.tools import web_fetch


def make_writer(section: Section, registry: SourceRegistry) -> Agent:
    """Writes one beat's section from the researcher's candidate articles."""
    return make_agent(
        name=f"writer_{section.slug}",
        description=f"Writes the {section.name} section from researched sources.",
        client=chat_client("writer"),
        instructions=(
            f"You write the '{section.name}' section ({section.focus}) from the CANDIDATES you are given. "
            "Consult the **section-research** skill for output format, summary writing style, and house style. "
            "Pick the strongest stories — at least 2, at most 5. Skip share-price and analyst-rating candidates. "
            "You may call web_fetch on a candidate URL to read the full article first. "
            "Output only the entries: no section heading, no preamble."
        ),
        tools=[web_fetch],
        context_providers=[SKILLS],
        middleware=[EnforceCitations(registry)],
    )
