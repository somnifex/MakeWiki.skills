"""Integration-time mechanical draft hygiene lint.

A deterministic pre-verification check belonging to the EXISTING Integration
step: it inspects the assembled deliverable markdown tree against the
DocumentationPlan / PageSpecs / DocumentationModel and reports mechanical,
provable defects before Final Verification runs. It is NOT a new pipeline
stage, NOT a new verification level, and it never judges page quality,
persona fit, or API semantics — those belong to the LLM Reviewer and the
L0-L5 layers.

Checks (each traceable to a defect proven by the NewAPI benchmark):
- writer frontmatter leak (page_id/audience/page_type keys in deliverable md)
- internal artifact path leak (``.makewiki-artifacts/...`` in prose)
- section-marker grammar + PageSpec ``required_sections`` presence
- stable block-ID structure (duplicate ids in a doc; en/zh set equality)
- InterfaceDisposition cross-references (page_id in plan, gap_id in gaps,
  duplicate operation_id)
- plan/spec/draft drift (planned page missing a per-language draft, plus the
  existing ``plan_page_consistency_errors`` cross-reference report)

Errors block entry into Final Verification (Integration incomplete). The
Quality Gate's four-state semantics are untouched.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from makewiki_skills.model.page_spec import PageSpec
from makewiki_skills.review.section_parser import parse_document_sections
from makewiki_skills.verification.l4_cross_language import (
    _scan_blocks,
    pair_blocks_by_section_id,
)

if TYPE_CHECKING:  # pragma: no cover
    from makewiki_skills.model.documentation_model import DocumentationModel
    from makewiki_skills.model.documentation_plan import DocumentationPlan

__all__ = ["LintIssue", "run_draft_lint"]


class LintIssue(BaseModel):
    """One mechanical draft-hygiene finding."""

    rule: str  # "frontmatter_leak" | "artifact_path_leak" | ...
    severity: str = "error"  # "error" (blocks) | "warning"
    document: str = ""
    message: str = ""


_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n?", re.DOTALL)
_WRITER_ECHO_KEYS = ("page_id", "audience", "page_type", "source_claims")
_ARTIFACT_PATH_RE = re.compile(r"\.makewiki-artifacts/|12-drafts/|14-revision-results/")
_BLOCK_ID_RE = re.compile(r"\[\[id:([A-Za-z0-9_.\-]+)\]\]")


def _iter_docs(wiki_dir: Path) -> list[tuple[str, Path]]:
    """Yield (relative posix path, absolute path) for every deliverable .md."""
    out: list[tuple[str, Path]] = []
    for p in sorted(wiki_dir.rglob("*.md")):
        out.append((p.relative_to(wiki_dir).as_posix(), p))
    return out


def _lang_of(rel: str) -> str:
    return "zh-CN" if rel.endswith(".zh-CN.md") else "en"


def _base_of(rel: str) -> str:
    if rel.endswith(".zh-CN.md"):
        return rel[: -len(".zh-CN.md")]
    return rel[: -len(".md")]


def _check_frontmatter(rel: str, content: str, issues: list[LintIssue]) -> None:
    """A1 — writer frontmatter leak.

    Only frontmatter carrying writer-echo keys (page_id / audience /
    page_type / source_claims) is flagged. Frontmatter with other keys is
    legitimate site metadata the renderer strips mechanically.
    """
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return
    body = m.group(1)
    leaked = [k for k in _WRITER_ECHO_KEYS if re.search(rf"^{k}:", body, re.MULTILINE)]
    if leaked:
        issues.append(
            LintIssue(
                rule="frontmatter_leak",
                severity="error",
                document=rel,
                message=(
                    "Deliverable draft carries writer frontmatter keys "
                    f"{leaked}; writers must not emit YAML frontmatter"
                ),
            )
        )


def _check_artifact_paths(rel: str, content: str, issues: list[LintIssue]) -> None:
    """A2 — internal orchestration paths must not appear in deliverables."""
    for i, line in enumerate(content.splitlines(), 1):
        m = _ARTIFACT_PATH_RE.search(line)
        if m:
            issues.append(
                LintIssue(
                    rule="artifact_path_leak",
                    severity="error",
                    document=rel,
                    message=(
                        f"line {i}: internal artifact path "
                        f"'{m.group(0)}' referenced in deliverable prose"
                    ),
                )
            )


def _check_sections(
    rel: str,
    content: str,
    specs_by_id: dict[str, PageSpec],
    base: str,
    issues: list[LintIssue],
) -> None:
    """A3 — marker grammar (reuses parse_document_sections) + required_sections."""
    parsed = parse_document_sections(content, document_id=base, require_markers=True)
    for sid in parsed.duplicate_ids:
        issues.append(
            LintIssue(
                rule="section_marker",
                severity="error",
                document=rel,
                message=f"duplicate stable section id '{sid}'",
            )
        )
    for om in parsed.orphan_markers:
        issues.append(
            LintIssue(
                rule="section_marker",
                severity="error",
                document=rel,
                message=(
                    f"orphan section marker '{om}' (marker must be immediately "
                    "followed by a heading)"
                ),
            )
        )
    for h in parsed.missing_marker_headings:
        issues.append(
            LintIssue(
                rule="section_marker",
                severity="error",
                document=rel,
                message=f"reviewable H2 '{h}' has no stable section marker",
            )
        )
    spec = specs_by_id.get(base)
    if spec is not None:
        present = {s.section_id for s in parsed.sections}
        for required in spec.required_sections:
            if required not in present:
                issues.append(
                    LintIssue(
                        rule="required_section_missing",
                        severity="error",
                        document=rel,
                        message=(
                            f"PageSpec requires section '{required}' but the "
                            "draft has no marker for it"
                        ),
                    )
                )


def _check_block_ids(
    docs_by_base: dict[str, dict[str, str]],
    wiki_dir: Path,
    issues: list[LintIssue],
) -> None:
    """A4 — duplicate [[id]] within one doc; en/zh block-ID SET equality.

    Full byte-parity of block BODIES stays in L4a; the lint only proves the
    stable-ID structure exists identically on both sides.
    """
    for base, lang_map in sorted(docs_by_base.items()):
        for lang, content in lang_map.items():
            ids = _BLOCK_ID_RE.findall(content)
            seen: set[str] = set()
            for bid in ids:
                if bid in seen:
                    issues.append(
                        LintIssue(
                            rule="duplicate_block_id",
                            severity="error",
                            document=f"{base} ({lang})",
                            message=f"stable block id '{bid}' declared more than once",
                        )
                    )
                seen.add(bid)
        # set equality across languages
        if len(lang_map) >= 2:
            langs = sorted(lang_map)
            sets = {lg: set(_BLOCK_ID_RE.findall(lang_map[lg])) for lg in langs}
            reference = sets[langs[0]]
            for lg in langs[1:]:
                missing = reference - sets[lg]
                extra = sets[lg] - reference
                for bid in sorted(missing):
                    issues.append(
                        LintIssue(
                            rule="block_id_set_mismatch",
                            severity="error",
                            document=f"{base} ({lg})",
                            message=(
                                f"stable block id '{bid}' present in "
                                f"{langs[0]} but missing in {lg}"
                            ),
                        )
                    )
                for bid in sorted(extra):
                    issues.append(
                        LintIssue(
                            rule="block_id_set_mismatch",
                            severity="error",
                            document=f"{base} ({lg})",
                            message=(
                                f"stable block id '{bid}' present in {lg} "
                                f"but missing in {langs[0]}"
                            ),
                        )
                    )


def _check_dispositions(
    doc_model: "DocumentationModel | None",
    planned_pages: set[str],
    issues: list[LintIssue],
) -> None:
    """A5 — disposition cross-references (mechanical only)."""
    if doc_model is None:
        return
    dispositions = list(getattr(doc_model, "interface_dispositions", []) or [])
    gaps = {g.id for g in (getattr(doc_model, "documentation_gaps", []) or [])}
    seen_ops: dict[str, int] = {}
    for d in dispositions:
        seen_ops[d.operation_id] = seen_ops.get(d.operation_id, 0) + 1
        if d.disposition in ("documented", "grouped"):
            if d.page_id and d.page_id not in planned_pages:
                issues.append(
                    LintIssue(
                        rule="disposition_unknown_page",
                        severity="error",
                        document=f"disposition:{d.operation_id}",
                        message=(
                            f"disposition page_id '{d.page_id}' is not a planned "
                            "DocumentationPlan page"
                        ),
                    )
                )
        if d.disposition == "unresolved" and d.gap_id and d.gap_id not in gaps:
            issues.append(
                LintIssue(
                    rule="disposition_unknown_gap",
                    severity="error",
                    document=f"disposition:{d.operation_id}",
                    message=(
                        f"unresolved disposition cites gap_id '{d.gap_id}' which "
                        "does not exist in documentation_gaps"
                    ),
                )
            )
    for op, n in sorted(seen_ops.items()):
        if n > 1:
            issues.append(
                LintIssue(
                    rule="disposition_duplicate_operation",
                    severity="error",
                    document=f"disposition:{op}",
                    message=f"operation '{op}' has {n} disposition entries",
                )
            )


def _check_plan_drafts(
    wiki_dir: Path,
    planned_pages: set[str],
    languages: set[str],
    issues: list[LintIssue],
) -> None:
    """A6 — every planned page must have a draft file per declared language."""
    for page in sorted(planned_pages):
        for lang in sorted(languages):
            if lang == "en":
                candidate = wiki_dir / f"{page}.md"
            else:
                candidate = wiki_dir / f"{page}.{lang}.md"
            if not candidate.is_file():
                issues.append(
                    LintIssue(
                        rule="planned_page_missing_draft",
                        severity="error",
                        document=page,
                        message=(
                            f"planned page '{page}' has no assembled draft for "
                            f"language '{lang}'"
                        ),
                    )
                )


def run_draft_lint(
    wiki_dir: Path,
    plan: "DocumentationPlan | None",
    page_specs: list[PageSpec],
    doc_model: "DocumentationModel | None" = None,
    languages: list[str] | None = None,
) -> list[LintIssue]:
    """Run every mechanical draft-hygiene check; return all issues.

    Pure and deterministic. Blocking (severity ``error``) issues mean the
    Integration output is incomplete and Final Verification must not start.
    ``plan`` may be ``None`` (plan artifact absent or schema-invalid): the
    structural checks still run; the plan-derived cross-checks are skipped
    because their reference sets would be empty guesses — Python never
    fabricates a plan.
    """
    wiki_dir = Path(wiki_dir).resolve()
    issues: list[LintIssue] = []

    planned_pages: set[str] = set()
    if plan is not None:
        planned_pages = set(getattr(plan, "pages", []) or [])
        for section in getattr(plan, "sections", []) or []:
            planned_pages.update(section.pages)
    # The plan schema carries no languages field; callers pass the declared
    # language set (the SitePresentationPlan / config languages). Default to
    # the en+zh-CN V3 pair when unspecified.
    langs = set(languages) if languages else {"en", "zh-CN"}

    # per-document contents
    docs_by_base: dict[str, dict[str, str]] = {}
    for rel, path in _iter_docs(wiki_dir):
        content = path.read_text(encoding="utf-8", errors="replace")
        base = _base_of(rel)
        docs_by_base.setdefault(base, {})[_lang_of(rel)] = content
        _check_frontmatter(rel, content, issues)
        _check_artifact_paths(rel, content, issues)
        _check_sections(rel, content, {s.page_id: s for s in page_specs}, base, issues)

    _check_block_ids(docs_by_base, wiki_dir, issues)
    _check_dispositions(doc_model, planned_pages, issues)
    _check_plan_drafts(wiki_dir, planned_pages, langs, issues)

    # plan ↔ spec cross-reference (existing helper, unchanged semantics);
    # only meaningful when a schema-valid plan exists.
    if plan is not None:
        from makewiki_skills.model.documentation_plan import plan_page_consistency_errors

        for err in plan_page_consistency_errors(plan, page_specs):
            issues.append(
                LintIssue(
                    rule="plan_spec_consistency",
                    severity="error",
                    document="",
                    message=err,
                )
            )

    return issues
