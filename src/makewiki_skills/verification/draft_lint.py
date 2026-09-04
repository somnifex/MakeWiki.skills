"""Integration-time mechanical draft hygiene lint.

A deterministic pre-verification check belonging to the EXISTING Integration
step: it inspects the assembled deliverable markdown tree against the
DocumentationPlan / PageSpecs / DocumentationModel and reports mechanical,
provable defects before Final Verification runs. It is NOT a new pipeline
stage, NOT a new verification level, and it never judges page quality,
persona fit, or API semantics — those belong to the LLM Reviewer and the
L0-L5 layers.

Checks (each traceable to a defect class proven during RC verification):
- writer frontmatter leak (page_id/audience/page_type keys in deliverable md)
- internal artifact path leak (``.makewiki-artifacts/...`` in prose)
- section-marker grammar + PageSpec ``required_sections`` presence
- stable block-ID structure (duplicate ids in a doc; cross-language set
  equality over the declared languages)
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

from pydantic import BaseModel

from makewiki_skills.model.page_spec import PageSpec
from makewiki_skills.review.localized_filename import resolve_localized_filename
from makewiki_skills.review.section_parser import parse_document_sections

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
    issues: list[LintIssue],
) -> None:
    """A4 — duplicate [[id]] within one doc; cross-language block-ID SET equality.

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
    doc_model: DocumentationModel | None,
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
    default_language: str,
    issues: list[LintIssue],
) -> None:
    """A6 — every planned page must have a draft file per declared language."""
    for page in sorted(planned_pages):
        for lang in sorted(languages):
            suffix = "" if lang == default_language else f".{lang}"
            candidate = wiki_dir / f"{page}{suffix}.md"
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
    plan: DocumentationPlan | None,
    page_specs: list[PageSpec],
    doc_model: DocumentationModel | None = None,
    languages: list[str] | None = None,
    default_language: str = "en",
    structural_only: bool = False,
) -> list[LintIssue]:
    """Run every mechanical draft-hygiene check; return all issues.

    Pure and deterministic. Blocking (severity ``error``) issues mean the
    Integration output is incomplete and Final Verification must not start.

    ``structural_only=True`` runs ONLY the pure-Markdown checks (frontmatter
    leaks, artifact-path leaks, section-marker grammar, duplicate block IDs)
    and skips every artifact-backed check — plan↔PageSpec consistency,
    planned-draft completeness, PageSpec ``required_sections``, dispositions,
    and documentation-gaps. It is the explicit standalone scan mode; the full
    Integration lint is the caller's responsibility to invoke with real
    artifacts.

    In full mode ``plan`` may still be ``None`` (caller-managed degraded
    runs, e.g. unit tests): the plan-derived cross-checks are skipped because
    their reference sets would be empty guesses — Python never fabricates a
    plan.

    Language resolution priority: the canonical ``DocumentationPlan.languages``
    (non-empty) wins; otherwise the caller-declared ``languages``; only a
    legacy/standalone structural run with neither falls back to the V3
    ``en`` + ``zh-CN`` pair. ``default_language`` names the language carried
    by plain ``.md`` files (the filename contract: no suffix = default).
    """
    wiki_dir = Path(wiki_dir).resolve()
    issues: list[LintIssue] = []

    planned_pages: set[str] = set()
    plan_langs: list[str] = []
    if plan is not None:
        planned_pages = set(getattr(plan, "pages", []) or [])
        for section in getattr(plan, "sections", []) or []:
            planned_pages.update(section.pages)
        plan_langs = list(getattr(plan, "languages", []) or [])
    # Priority: canonical plan languages > caller-declared > legacy fallback.
    langs = set(plan_langs) or (set(languages) if languages else {"en", "zh-CN"})
    default_lang = default_language if default_language in langs else (plan_langs[0] if plan_langs else ("en" if "en" in langs else sorted(langs)[0]))

    # per-document contents
    docs_by_base: dict[str, dict[str, str]] = {}
    undeclared: set[str] = set()
    for rel, path in _iter_docs(wiki_dir):
        content = path.read_text(encoding="utf-8", errors="replace")
        resolved = resolve_localized_filename(rel, langs, default_lang)
        if not resolved.declared:
            # A ``.<x>.md`` suffix matching no declared language: no language
            # semantics are guessed. Structural checks still apply to the file
            # verbatim; it never joins a cross-language group.
            undeclared.add(rel)
        base = resolved.base_id
        docs_by_base.setdefault(base, {})[resolved.language] = content
        _check_frontmatter(rel, content, issues)
        _check_artifact_paths(rel, content, issues)
        _check_sections(
            rel,
            content,
            {} if structural_only else {s.page_id: s for s in page_specs},
            base,
            issues,
        )

    _check_block_ids(docs_by_base, issues)
    if structural_only:
        return issues

    _check_dispositions(doc_model, planned_pages, issues)
    _check_plan_drafts(wiki_dir, planned_pages, langs, default_lang, issues)

    # plan ↔ spec cross-reference via the existing helper.
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
