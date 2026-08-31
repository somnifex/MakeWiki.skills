"""Tests for the LLM-authored SitePresentationPlan model.

The plan is authored by the Main Agent / Site Designer LLM; Python only validates
the schema, resolves localized documents, and renders. ``nav_item_by_id`` is a
pure lookup by the stable, LLM-authored ``document_id``: it recurses through
children at any depth and never infers or invents IA.
"""

from makewiki_skills.model.site_presentation import (
    SiteNavItem,
    SitePresentationPlan,
)


def _deep_plan() -> SitePresentationPlan:
    return SitePresentationPlan(
        navigation=[
            SiteNavItem(
                document_id="docs",
                route="/docs",
                title="Docs",
                nav_group="Main",
                children=[
                    SiteNavItem(
                        document_id="guides",
                        route="/docs/guides",
                        title="Guides",
                        nav_group="Main",
                        children=[
                            SiteNavItem(
                                document_id="deep/deploy",
                                route="/docs/guides/deploy",
                                title="Deploy",
                                nav_group="Main",
                            )
                        ],
                    )
                ],
            ),
            SiteNavItem(
                document_id="reference",
                route="/reference",
                title="Reference",
                nav_group="Main",
            ),
        ]
    )


def test_nav_item_by_id_finds_nested_children_beyond_two_levels():
    """Lookup recurses through children without a shallow two-level limit."""
    plan = _deep_plan()
    assert plan.nav_item_by_id("deep/deploy") is not None
    assert plan.nav_item_by_id("deep/deploy").document_id == "deep/deploy"
    assert plan.nav_item_by_id("guides").document_id == "guides"
    assert plan.nav_item_by_id("docs").document_id == "docs"
    assert plan.nav_item_by_id("reference").document_id == "reference"


def test_nav_item_by_id_returns_none_for_unknown():
    """An unknown document returns None — Python never invents a nav item."""
    plan = _deep_plan()
    assert plan.nav_item_by_id("nonexistent") is None
    assert plan.nav_item_by_id("") is None


def test_nav_item_by_id_exact_id_match_only():
    """Lookup matches the exact LLM-authored document_id, not prefixes."""
    plan = _deep_plan()
    assert plan.nav_item_by_id("deep") is None
    assert plan.nav_item_by_id("reference/") is None
    assert plan.nav_item_by_id("Reference") is None


def test_nav_item_by_id_empty_plan():
    assert SitePresentationPlan().nav_item_by_id("anything") is None
