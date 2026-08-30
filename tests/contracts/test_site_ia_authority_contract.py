"""Site IA Authority Contract: the Main Agent owns site planning; Python renders.

This contract pins the phase-1 static-site refactor boundaries. The static site
system is the ONLY place the site's Information Architecture may be decided.
These guarantees are expressed as source/AST contracts so a future change that
quietly re-introduces Python-side IA heuristics fails loudly without executing:

1. **Python does not decide documentation IA** — the static-site renderer never
   derives page roles, navigation groups, ordering, or hierarchy from filenames
   or keywords.
2. **Site navigation comes from SitePresentationPlan** — SiteCompiler consumes
   an LLM-authored plan; the compiled site's nav (groups, order, routes,
   hierarchy, localized titles) is rendered verbatim from that plan.
3. **Main Agent is the only Site planning authority** — only the LLM / Skill
   layer authors the plan; the build command is gated on the plan's existence
   and never fabricates one.
4. **The renderer has no semantic page classification** — the static-site
   renderer contains no filename/keyword → category/priority/title mapping and
   no fixed Diátaxis-style page-template categories.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_MD = PROJECT_ROOT / "SKILL.md"
SRC_DIR = PROJECT_ROOT / "src/makewiki_skills"
RENDERER_DIR = SRC_DIR / "renderer"
SITE_COMPILER_PATH = RENDERER_DIR / "site_compiler.py"
CLI_PATH = SRC_DIR / "cli.py"
SITE_SUBSKILL = PROJECT_ROOT / "subskills" / "site" / "SKILL.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _modules_under(pkg_name: str) -> list[Path]:
    return sorted((SRC_DIR / pkg_name).glob("*.py"))


# ---------------------------------------------------------------------------
# 1. Python does not decide documentation IA
# ---------------------------------------------------------------------------


def test_legacy_filename_categorizer_removed():
    """The static-site renderer no longer infers page roles from filenames.

    ``_categorize_doc`` (the filename/keyword → category/priority/title table:
    readme→Overview, getting-started→Getting Started, faq→FAQ,
    installation|deployment→Installation & Deployment, usage→Usage & Workflows,
    configuration|environment-variables→Configuration, troubleshooting→
    Operations & Support, else→Reference) must be gone. Its removal is the core
    of "Python does not decide documentation IA".
    """
    text = _read(SITE_COMPILER_PATH)
    assert "_categorize_doc" not in text


def test_site_compiler_has_no_priority_or_category_fields():
    """No ``category``/``priority`` page fields survive in the static renderer.

    The old pipeline attached a semantic ``category`` string and a numeric sort
    ``priority`` to every document. Those were Python's IA decision. The
    plan-driven renderer drops both: navigation grouping/ordering come from the
    plan's ``nav_group``/``ordering`` instead.
    """
    text = _read(SITE_COMPILER_PATH)
    assert "priority" not in text, "priority sort field must not resurface"
    assert "_categorize_doc" not in text


def test_site_compiler_contains_no_filename_keyword_category_map():
    """No filename→semantic-title keyword branches exist in the renderer.

    A filename categorizer manifests as ``slug.lower() in (...readme, index...)``
    or ``startswith("getting-started")`` returning a semantic label. We assert
    none of the literal heuristic triggers the old code used are present in a
    Python-side role-mapping capacity. (``startswith`` string ops for markdown
    link/html parsing are mechanical and unrelated.)
    """
    text = _read(SITE_COMPILER_PATH)
    # The static renderer must not classify slugs by these documented keywords.
    for branch in (
        'in ("readme", "index")',
        'in ("README", "INDEX")',
        '("readme", "index")',
        'startswith("getting-started")',
        'startswith("installation")',
        'startswith("deployment")',
        'startswith("configuration")',
        'startswith("environment-variables")',
        'startswith("troubleshooting")',
        'startswith("faq")',
    ):
        assert branch not in text, f"filename→semantic branch present: {branch}"


def test_static_site_template_has_no_hardcoded_page_roles():
    """The renderer's emitted site has no fixed Diátaxis-style page categories.

    Diátaxis is a cognitive rubric owned by the LLM; it must never become a
    Python page template. The static renderer must not hardcode the site section
    labels as literal template strings used for grouping.
    """
    text = _read(SITE_COMPILER_PATH)
    # These are the semantic section labels the OLD categorizer returned as
    # Python-injected nav groups. They are permitted in the module *docstring*
    # (which describes what is NOT inferred), but must not be used as emitted
    # group labels. We check only for the emitted-template forms.
    assert '"Overview"' not in text and "'Overview'" not in text
    assert '"Getting Started"' not in text and "'Getting Started'" not in text
    assert '"FAQ"' not in text and "'FAQ'" not in text
    assert '"Deployment"' not in text and "'Deployment'" not in text


# ---------------------------------------------------------------------------
# 2. Site navigation comes from SitePresentationPlan
# ---------------------------------------------------------------------------


def test_site_compiler_consumes_site_presentation_plan():
    """SiteCompiler's contract requires an LLM-authored SitePresentationPlan.

    The constructor accepts (and compile resolves) a ``SitePresentationPlan``.
    Without one it raises rather than fabricating an IA.
    """
    text = _read(SITE_COMPILER_PATH)
    assert "SitePresentationPlan" in text
    assert "from makewiki_skills.model.site_presentation import" in text
    assert "SitePlanRequiredError" in text
    assert "site_plan" in text or "plan" in text
    assert "navigation" in text


def test_site_model_plan_carries_ia_fields():
    """The SitePresentationPlan model holds each required IA field."""
    model_path = SRC_DIR / "model" / "site_presentation.py"
    text = _read(model_path)
    for field in (
        "project_title",
        "project_description",
        "document_id",
        "route",
        "titles",
        "nav_group",
        "ordering",
        "languages",
        "visual",
    ):
        assert field in text, f"SitePresentationPlan missing required field: {field}"
    assert "class SitePresentationPlan(" in text
    assert "class SiteNavItem(" in text


def test_site_model_plan_is_exported():
    """The plan is part of the model package's public surface."""
    model_init = _read(SRC_DIR / "model" / "__init__.py")
    assert "SitePresentationPlan" in model_init
    assert "load_site_presentation" in model_init


# ---------------------------------------------------------------------------
# 3. Main Agent is the only Site planning authority
# ---------------------------------------------------------------------------


def test_build_site_command_is_plan_gated():
    """build-site only compiles when an LLM-authored plan exists.

    The CLI resolves the plan (default ``site_presentation.json`` / ``.yaml`` in
    the wiki dir, or ``--plan``). With no plan it exits as pending/unavailable —
    it never auto-invents an Information Architecture from filenames.
    """
    text = _read(CLI_PATH)
    assert "site_presentation.json" in text
    assert "load_site_presentation" in text
    assert "--plan" in text


def test_build_site_error_name_for_missing_plan_present():
    """The compiler raises a clear plan-required error, not a filename guess."""
    text = _read(SITE_COMPILER_PATH)
    assert "SitePlanRequiredError" in text
    assert "never fabricate" in text or "fabricates" in text or "never infers" in text
    assert "Navigation" in text or "navigation" in text


def test_authoritative_skill_documents_site_planning_authority():
    """The Skill layer (Main Agent) is recorded as the Site planning authority.

    SKILL.md and the site subskill must describe the Main Agent as the author of
    the SitePresentationPlan and the build step as consuming it — mirroring how
    the SemanticAuditBundle is LLM-authored and machine-consumed.
    """
    skill = _read(SKILL_MD)
    site_subskill = _read(SITE_SUBSKILL)
    assert "SitePresentationPlan" in skill
    assert "SitePresentationPlan" in site_subskill
    # Diátaxis remains a cognitive rubric, never a Python template.
    assert "rubric" in skill or "cognitive" in skill


def test_no_diataxis_or_fixed_template_anywhere_in_python():
    """Diátaxis / fixed section names never become Python page templates."""
    for py in SRC_DIR.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        text = py.read_text(encoding="utf-8")
        assert "Diataxis" not in text
        assert "diataxis" not in text
