from utils.sections import SECTIONS, Section


def test_slug_replaces_ampersand_and_spaces():
    assert Section("Competitive Landscape", "x").slug == "competitive_landscape"
    assert Section("Deals & Movements", "x").slug == "deals_movements"
    assert Section("Regulatory & Policy Watch", "x").slug == "regulatory_policy_watch"


def test_section_is_frozen():
    section = Section("Quick Hits", "short items")
    try:
        section.name = "Other"
    except Exception as error:
        assert "frozen" in type(error).__name__.lower() or "cannot assign" in str(error).lower()
    else:
        raise AssertionError("Section should be immutable")


def test_sections_catalogue_is_well_formed():
    assert len(SECTIONS) == 5

    names = [section.name for section in SECTIONS]
    slugs = [section.slug for section in SECTIONS]

    assert len(set(names)) == len(names)
    assert len(set(slugs)) == len(slugs)
    assert all(section.focus for section in SECTIONS)
