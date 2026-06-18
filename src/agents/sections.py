from dataclasses import dataclass


@dataclass(frozen=True)
class Section:
    name: str
    focus: str

    @property
    def slug(self) -> str:
        return self.name.lower().replace(" & ", "_").replace(" ", "_")


SECTIONS = [
    Section("Competitive Landscape", "rivals, market-share moves, head-to-head comparisons"),
    Section("Deals & Movements", "M&A, funding, partnerships, executive hires and exits"),
    Section("Regulatory & Policy Watch", "regulators, lawsuits, compliance, new rules"),
    Section("Disruptors & Tech", "new entrants, emerging technology, AI and platform shifts"),
    Section("Quick Hits", "short notable items that fit no other section"),
]
