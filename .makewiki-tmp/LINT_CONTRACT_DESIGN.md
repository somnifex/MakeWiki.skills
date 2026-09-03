# Integration Mechanical Draft Lint — Contract Design

TASK: V3-CONVERGE-LINT-01 (design only — no code changes)

## Purpose

One deterministic pre-verification check inside the EXISTING Integration step.
It is not a new pipeline stage, not a new verification level, not a new agent.
It runs after assembly of the deliverable markdown tree and before Final
Verification (L0-L5), and reports mechanical, provable defects only.

Inputs (all already exist):
- assembled deliverable markdown tree (wiki dir)
- PageSpec set (`required_sections` per page)
- DocumentationPlan (planned page set via `plan_page_consistency_errors`)
- DocumentationModel (`interface_dispositions`, `documentation_gaps`)

## LINT RULES

### A. Integration lint (mechanical, new — blocks Final Verification entry)

A1. **Writer frontmatter leak** — a deliverable `.md` whose body begins with a
    YAML `---` block containing `page_id:` / `page_type:` / `audience:`
    writer-echo keys. NOTE the distinction: the SiteCompiler/renderer now
    strips a leading frontmatter block at render time, so frontmatter is not a
    rendering hazard by itself; but Writer-emitted frontmatter in DRAFTS was
    proven to leak (en 10 of 32 pages) and it is contract noise. Rule: flag
    any frontmatter that carries `page_id`/`audience`/`page_type` keys in a
    deliverable draft. (If a future contract adds legitimate site metadata,
    it must use different keys — this rule keys on the writer-echo keys, not
    on `---` itself.)
    Severity: error (blocks).

A2. **Internal artifact path leak** — deliverable prose mentions
    `.makewiki-artifacts/` or `12-drafts/` / `14-revision-results/` (internal
    orchestration paths). Mechanical string scan over prose (skip code fences
    that quote them as examples? NO — benchmark showed the leak was prose
    links; scanning fenced blocks too is safe and mechanical).
    Severity: error (blocks).

A3. **Section-marker grammar** — per the section parser's existing contract:
    marker immediately followed by a heading; no orphan markers; no duplicate
    section IDs; every PageSpec `required_sections` id present in the draft
    (this last one is the NEW cross-check to PageSpec; the grammar parts reuse
    `parse_document_sections`).
    Severity: error (blocks).

A4. **Stable block-ID structure** — no duplicate `[[id:...]]` within one
    document; per-language block-ID sets for a page pair are comparable
    (the full L4a byte-parity stays in L4; the lint only checks SET equality
    of block IDs en↔zh and single-doc uniqueness, reusing
    `pair_blocks_by_section_id`).
    Severity: error (blocks).

A5. **Disposition / plan / page cross-check** — every `documented|grouped`
    `InterfaceDisposition.page_id` must exist in the planned page set
    (`plan.pages` + all `section.pages`); no duplicate `operation_id` entries;
    `unresolved.gap_id` must exist in `documentation_gaps`. (Mechanical
    cross-reference only — Python does not judge importance, coverage, or
    omission reasonableness.)
    Severity: error (blocks).

A6. **Plan/spec/draft drift** — reuse existing
    `plan_page_consistency_errors(plan, page_specs)` output unchanged, plus
    one new mechanical check: every planned page has ≥1 assembled draft file
    per declared language.
    Severity: error (blocks).

### B. Final L0-L5 continues to own

- L0: heading hierarchy, H1, broken doc-relative links, empty pages.
- L1: existence of paths/commands/config keys (with Phase-1 evidence gating).
- L2: CLI/AST interface probes.
- L3/L4b/L5: semantic layers (LLM-audited).
- L4a: full byte-parity of block bodies (the lint checks SET equality only;

  body-hash parity remains L4's job — cheaper check first, deeper check after).

### C. LLM Reviewer continues to own

- Page quality, persona fit, prose correctness, API semantic correctness,

  completeness, anti-cliché voice — everything not mechanically decidable.

## REUSED EXISTING CHECKS

- `parse_document_sections` (section grammar, duplicate IDs, orphan markers) — A3.
- `pair_blocks_by_section_id` / `_scan_blocks` (block-ID pairing) — A4.
- `plan_page_consistency_errors` (plan↔spec cross-reference) — A6.
- `PageSpec.required_sections` — A3 cross-check.
- `InterfaceDisposition` self-consistency validator (already schema-enforced) —

  A5 adds only the cross-artifact page_id/gap_id existence checks.

## NEW MINIMAL CHECKS

- A1 writer-frontmatter key scan.
- A2 internal-artifact-path scan.
- A3-cross `required_sections` presence per draft.
- A4 block-ID set equality across language pairs + duplicate-ID-in-doc.
- A5 disposition page_id ∈ plan set; duplicate operation_id; gap_id ∈ gaps.
- A6 planned-page-has-draft-per-language.

All checks are pure functions over (markdown tree, PageSpec set, plan,
documentation model). No project keywords, no semantic judgment.

## FILES TO MODIFY (implementation phase, V3-CONVERGE-LINT-02/03)

- NEW `src/makewiki_skills/verification/draft_lint.py` — one module, one

  public entry `run_draft_lint(wiki_dir, plan, page_specs, doc_model) -> list[LintIssue]`.
- `src/makewiki_skills/cli.py` — expose as `lint-drafts <wiki_dir>` toolkit

  command (mechanical-only; exit 1 on blocking issues). Wiring into the
  Integration task contract happens in the tasks doc, not the pipeline.
- `tasks/integrate.md` — add a "## 8. Draft hygiene lint (mechanical)" section:

  run `lint-drafts` after assembly; blocking issues = Integration incomplete.
- Tests: NEW `tests/unit/verification/test_draft_lint.py`.

## TEST PLAN

- clean draft set → no issues.
- frontmatter with page_id/audience keys → A1 error.
- frontmatter WITHOUT writer-echo keys (e.g. only `title:`) → allowed (not a

  writer echo; renderer strips it).
- prose linking `.makewiki-artifacts/04-claim-bundles/...` → A2 error.
- missing one required_sections marker → A3 error; orphan marker → A3; dup

  section id → A3.
- en has `[[id:x]]`, zh lacks it → A4 error; duplicate id in one doc → A4.
- disposition page_id `reference/api/token` not in plan → A5 error

  (the exact benchmark defect); duplicate operation_id → A5; omitted+reason →
  pass; unresolved+existing gap → pass; unresolved+unknown gap → error.
- planned page without zh draft → A6 error.
- plan_page_consistency_errors still reported through the same channel.

## EXPLICITLY OUT OF SCOPE

- Page quality / persona / completeness / API semantics (LLM Reviewer).
- L4a body-hash parity (stays in L4).
- Any new Quality Gate state (lint failure = Integration incomplete, gate

  untouched).