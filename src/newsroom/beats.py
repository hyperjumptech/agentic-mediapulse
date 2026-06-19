from dataclasses import dataclass

from agent_framework import Agent

from agents.researcher import make_researcher
from agents.runtime.guardrails import SourceRegistry
from agents.sections import SECTIONS, Section
from agents.writer import make_writer


@dataclass
class Beat:
    """One section's desk: a researcher and writer sharing a citation registry."""

    section: Section
    researcher: Agent
    writer: Agent
    registry: SourceRegistry


def _make_beat(section: Section) -> Beat:
    registry = SourceRegistry()

    return Beat(
        section=section,
        researcher=make_researcher(section, registry),
        writer=make_writer(section, registry),
        registry=registry,
    )


BEATS = [_make_beat(section) for section in SECTIONS]
