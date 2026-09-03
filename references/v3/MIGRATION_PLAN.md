# MakeWiki V3 Migration Plan — Status Document




> **Live status, not a todo list.** This file describes the V3 migration state
> represented by the **checked-out repository revision**, so a local agent does
> **not** re-run already-completed V3 migration tasks. It is not pinned to any one
> commit: when auditing implementation status, the **checked-out source and tests
> are authoritative** — judge each phase against `src/` and `tests/`, not against
> this file's prose.
>
> STATUS vocabulary:
> - `DONE` — implemented and verified against current source
> - `PARTIAL` — some but not all of the phase is implemented
> - `TODO` — not started
>
> Each phase lists `IMPLEMENTED` (what is really present now), `REMAINING`
> (what is still missing), and `ACCEPTANCE` (when the phase counts as complete).
> Status is judged from `src/` and the authoritative `SKILL.md` / `tasks/`, **not**
> from this plan's older text.

## Strategy

Original direction: build the new path first, then switch the authoritative
flow, then clean up legacy descriptions. Do not rewrite the root `SKILL.md`
first. (This has now been completed through Phase M/P; see per-phase status.)

---

## Phase A — Design authority

**STATUS: DONE**

**IMPLEMENTED:**
- `references/v3/` is committed and populated: `ARCHITECTURE.md`,
  `COGNITIVE_BOUNDARY.md`, `MIGRATION_PLAN.md`, `LOCAL_AGENT_RULES.md`,
  `MULTI_AGENT_PROTOCOL.md`, `SUBTASK_PROTOCOL.md`, `ARTIFACT_CONTRACTS.md`,
  `PAGE_SPEC.md`, `API_REFERENCE.md`, `DOCUMENTATION_MODEL.md`,
  `QUALITY_POLICY.md`, `PHASE_PROMPTS.md`, `BASELINE.md`, `README.md`,
  `config-migration.md`.
- Baseline commit is recorded (the V2-design baseline at `fda0ebf`).
- Local agent can build per the spec (one Micro Task at a time).

**REMAINING:** none.

**ACCEPTANCE:** V3 architecture frozen before implementation — met.

---

## Phase B — Add V3 cognitive tasks without switching V2

**STATUS: DONE**

**IMPLEMENTED:** all V3 task files exist:
`tasks/orient.md`, `tasks/investigate.md`, `tasks/semantic.md`,
`tasks/document-model.md`, `tasks/plan-pages.md`, `tasks/write-page.md`,
`tasks/revise.md`, `tasks/integrate.md`.

**REMAINING:** none. Legacy `scan` / `write` task files were later **rewritten to
V3** (see the V3 legacy cleanup): `scan.md` now documents optional mechanical
fact assistance + Explorer-family recovery / blind-coverage focus variants;
`write.md` now documents the one-`PageSpec`-×-one-language writer contract. `tasks/rebattle.md`
was already V3-hardened (escalation); `tasks/review.md` is V3.

**ACCEPTANCE:** V3 task prompt contracts present, V2 flow not yet switched — met.

---

## Phase C — Artifact validation layer

**STATUS: DONE**

**IMPLEMENTED:**
- `src/makewiki_skills/model/v3_artifacts.py` defines `RepositoryBrief`,
  `InvestigationPlan`, `SubtaskSpec`, `ClaimBundle`, `ReviewFindings`.
- `src/makewiki_skills/model/documentation_model.py` defines `DocumentationModel`
  (and `InterfaceReference` / `HttpOperationReference`, see Phase H).
- `src/makewiki_skills/model/page_spec.py` defines `PageSpec`.
- Models are schema/serialization-only (Pydantic), LLM-authored, docstringed.

**REMAINING:** none.

**ACCEPTANCE:** minimal schema/serialization for V3 artifacts, Python only
validates/serializes — met.

---

## Phase D — OrchestrationState V3 compatibility

**STATUS: DONE**

**IMPLEMENTED:** `src/makewiki_skills/model/orchestration_state.py` now carries
every V3 handoff artifact as an **actual typed Pydantic model** (not free dicts):

- `repository_brief: RepositoryBrief | None`,
  `investigation_plan: InvestigationPlan | None`,
  `subtasks: list[SubtaskSpec]`;
- `documentation_model: DocumentationModel | None` (Phase G / H model);
- `documentation_plan: DocumentationPlan | None` — coerced by pydantic from a
  legacy `persona` / `from` dict fixture (Phase K model);
- `page_specs: list[PageSpec]` (Phase I model).

A legacy `dict` authored against the older contract is still coerced into the
typed `DocumentationPlan`, so backward compatibility is preserved.

**REMAINING:** none. No Python scheduler was introduced (correct — Python only
serializes/validates; the Main Agent LLM owns scheduling).

**ACCEPTANCE:** V3 state fields exist as typed models, no Python scheduler — met.

---

## Phase E — ClaimBundle compatibility

**STATUS: DONE**

**IMPLEMENTED:** `src/makewiki_skills/model/search_ledger.py` provides a
`to_claim_bundle()` conversion to V3 `ClaimBundle`, preserving the legacy
`SearchLedger` parser.

**REMAINING:** none confirmed.

**ACCEPTANCE:** `SearchLedger -> ClaimBundle` compatibility conversion exists
without Python inferring visibility/abstraction — met.

---

## Phase F — Semantic synthesis task

**STATUS: DONE**

**IMPLEMENTED:** `tasks/semantic.md` is the V3 SemanticModel generation contract;
ReBattle is an **escalation** path (SKILL.md §2 / §9.3), not a fixed phase. Old
ReBattle CLI (`rebattle-diff`) retained as a deterministic organizer.

**REMAINING:** none.

**ACCEPTANCE:** `tasks/semantic.md` as V3 semantic contract; ReBattle = escalation — met.

---

## Phase G — DocumentationModel

**STATUS: DONE**

**IMPLEMENTED:** `documentation_model.py` `DocumentationModel` is a formal
Pydantic model modeling personas / capabilities / journeys / concepts /
references / interface_references / interface_dispositions / documentation_gaps.
It is typed onto `OrchestrationState.documentation_model` and consumed by the
Page-Planning / Writer cognitive chain. Old `SemanticModel` fields
(user_tasks/faq/troubleshooting) remain intact for compatibility.

**REMAINING:** none for this phase. Note (architecture boundary, not a gap): the
deterministic CLI loader/digest (`verify-model`) still covers `SemanticModel`
only — the LLM-authored DocumentationModel is validated on load by pydantic and
carried via OrchestrationState, never given a semantic digest by Python (Python
never computes semantic coverage).

**ACCEPTANCE:** new persona/capability/journey model present without deleting legacy
SemanticModel fields — met.

---

## Phase H — Operator/API Reference

**STATUS: DONE**

**IMPLEMENTED:** `documentation_model.py` models the full interface-reference
family, all first-class Pydantic models: `InterfaceReference` (by `kind` — HTTP
/ admin / management API, RPC, webhook, health, CLI, config) plus its
`HttpOperationReference`, `CliCommandReference`, `ConfigReference`,
`OperationalEndpointReference`, and the `InterfaceDisposition` contract
(recorded disposition per important interface operation: documented / grouped /
omitted / unresolved). `tasks/document-model.md` §7 / §10 require the Architect
to explicitly consider operator / management-API / API-reference surfaces where
evidence supports them.

**REMAINING:** none. No framework-specific extractors were added (correct;
content is LLM-authored).

**ACCEPTANCE:** interface/API schema contracts present across HTTP / CLI / config /
operational references; Architect prompt considers operator/API surfaces — met.

---

## Phase I — PageSpec-driven writing

**STATUS: DONE**

**IMPLEMENTED:** `page_spec.py` `PageSpec` is a formal Pydantic model, typed onto
`OrchestrationState.page_specs`, and consumed by the mechanical helper
`plan_page_consistency_errors()` in `documentation_plan.py` (cross-checks plan
page refs against the PageSpec set). `tasks/write-page.md` exists; SKILL.md
§9.6 defines each Writer as writing exactly **one page (`page_id`) × one language**
(no "one language writer writes the whole suite" default) from a single
**language-neutral** PageSpec (one canonical PageSpec per `page_id`, shared by all
languages). Stable block IDs, section markers, native multilingual writing,
anti-cliché policy retained.

**REMAINING:** none. (No `verify-model`-style digest for PageSpecs; like the
DocumentationModel, they are pydantic-validated and carried via
OrchestrationState / the plan-consistency helper — the semantic suitability of a
spec is LLM-owned.)

**ACCEPTANCE:** Writer granularity is one page × one language from the shared
language-neutral PageSpec — met.

---

## Phase J — Independent review

**STATUS: DONE**

**IMPLEMENTED:** `tasks/review.md` defines a **read-only Reviewer** (emits
`ReviewFindings`, does not edit pages); `tasks/revise.md` defines a separate
**Revision Agent**. SKILL.md §9.7 / §9.8 match this.

**REMAINING:** none.

**ACCEPTANCE:** Reviewer read-only, Revision separate — met. (The V2 "Auditor
edits Markdown in place" contract was replaced.)

---

## Phase K — Documentation planning and SitePresentationPlan

**STATUS: DONE**

**IMPLEMENTED:** `DocumentationPlan` is now a **formal Pydantic model** in
`documentation_plan.py` (`DocumentationSection` / `DocumentationRelation` /
`DocumentationPlan`, with plan↔PageSpec cross-check via
`plan_page_consistency_errors()`), typed onto `OrchestrationState.documentation_plan`
and described in `tasks/plan-pages.md`. The Integrator maps it to
`SitePresentationPlan` (`tasks/integrate.md`, SKILL.md §8 / §9.9). Python
`SiteCompiler` renders the plan only. Navigation is **recursive**:
`site_presentation.py` recurses `children` with no depth cap (a two-level
limitation was removed), verified by `test_site_presentation.py`.

**REMAINING:** none.

**ACCEPTANCE:** DocumentationPlan is a typed model; recursive navigation allowed;
renderer has no IA authority — met.

---

## Phase L — Switch authoritative SKILL

**STATUS: DONE**

**IMPLEMENTED:** root `SKILL.md` is switched to the V3 authoritative flow
(Orientation → Investigation → Semantic → DocumentationModel → PagePlan → Write →
Review → Revise → Integrate → Verify → Deliver; see SKILL.md §2 / §9). Census /
Evidence are optional mechanical assistance, never prerequisites. Legacy
`scan` / `write` / `rebattle` task files remain as compatibility references.
(Equivalent to the V3-K1 micro task.)

**REMAINING:** none. (`scan.md` / `write.md` were subsequently rewritten to V3 in
the V3 legacy cleanup; `rebattle.md` is the V3 escalation contract. The preserved
V2 `SearchLedger` parser in Python is backward-compat only.)

**ACCEPTANCE:** SKILL.md authoritative flow is V3; legacy tasks are compatibility — met.

---

## Phase M — Config cleanup

**STATUS: DONE**

**IMPLEMENTED:**
- `references/v3/config-migration.md` documents the design: audience re-scoped as
  **seed hints**, additive operator/API seed switches, and `agent.*` as
  budget/safety ceilings.
- `src/makewiki_skills/config.py` declares both
  `DocumentationPolicyConfig.include_operator_persona` and
  `include_api_reference` as LLM_ONLY additive seed switches (both present in
  `_LLM_CONSUMED_FIELDS`). No `config.operator.*` / `config.api.*` block was
  added (by design). Audience fields (`documentation_policy.audience`,
  `delivery.audience`) are documented as seed hints on the config model.
- The **default YAML exposes both seeds**: root `makewiki.config.yaml`, the
  `init-config` template (`subskills/init/templates/default.config.yaml`), and
  `templates/config.yaml` all list `include_operator_persona` /
  `include_api_reference` with explanatory comments.
- All four micro tasks landed:
  - **M-L1a** (re-document audience semantics as seed hints) — config.py
    docstrings + SKILL.md "seed hints" wording.
  - **M-L1b** (add `include_operator_persona`) — config.py + Skill layer
    (`tasks/document-model.md`).
  - **M-L1c** (add `include_api_reference`) — config.py + Skill layer
    (`tasks/plan-pages.md`, `tasks/write*.md`).
  - **M-L1d** (document `agent.*` parallelism semantics) — SKILL.md §2 / §5 and
    the config `AgentConfig` docstring (budgets/ceilings, never promises).
- `agent.max_parallelism` remains default `10`: the accepted design
  (config-migration.md §3.4 / §4.5) is *document, don't restructure*, so the
  earlier "re-baseline to a more conservative value" idea was superseded — it is
  **not** an open gap.

**REMAINING:** none.

**ACCEPTANCE:** audience fields re-documented as seed hints toward persona-aware
planning, and the additive operator/API seeds present in config + default YAML —
**met**.

---

## Phase N — Quality contracts

**STATUS: DONE**

**IMPLEMENTED:** L0–L5 preserved; an LLM **Documentation Fitness** review policy
exists in `references/v3/QUALITY_POLICY.md` (fitness dimensions, result, and
findings). Python does not compute semantic coverage; coverage opinion lives in
LLM-authored review artifacts, Python validates/records structure.

**REMAINING:** none confirmed.

**ACCEPTANCE:** L0–L5 retained, LLM Documentation Fitness policy added without
Python pretending to compute semantic coverage — met.

---

## Phase O — Eval

**STATUS: DONE**

**IMPLEMENTED:** `evals/newapi-v3/` benchmark scaffolding
(`README.md` run protocol + `benchmark-run-template.yaml`, full 18 dimensions:
persona separation, API/operator coverage, page granularity, implementation
leakage, etc.) — human/LLM rubric rated, not a Python scorer, and intentionally
kept out of the deterministic trap set (no root `rubric.yaml`). The original
deterministic grounding traps are preserved.

**REMAINING:** none (benchmark run reports are filled per-run by a judge; the
scaffolding is in place).

**ACCEPTANCE:** NewAPI-style documentation-quality eval added — met.

---

## Phase P — Documentation sync

**STATUS: DONE**

**IMPLEMENTED:**
- `README.md` and `README.en.md` were updated to the V3 authoritative pipeline
  (V3-A5 / V3-A6): main flow, CLI table, LLM-designed page hierarchy,
  persona/operator/API-reference mentions.
- `AGENTS.md` and `CLAUDE.md` were updated to the V3 pipeline (Phase 2,
  commit `4a59b0a`): authoritative flow, stable role families + dynamic
  `SubtaskSpec`, `Explorer` (not `Scout`), ReBattle = escalation, Recovery
  **Explorer**.
- `references/architecture.md` describes the V3 `authoritative_pipeline`
  (Investigation/Explorer, DocumentationModel, DocumentationPlan/PageSpecs,
  Reviewer / **Final Semantic Auditor**); the `architecture_before` block
  remains only as a labeled historical comparison.
- `CHANGELOG.md` current `[Unreleased]` section describes the V3 flow;
  historical released entries legitimately record the V2 flow.

**REMAINING:** none (V2 shadow authority tracked here has been resolved; see
the V3 legacy cleanup commit). CHANGELOG historical entries keep V2 wording as
accurate release history.

**ACCEPTANCE:** README/README.en/AGENTS/CLAUDE/CHANGELOG/references/architecture
all reflect only implemented capability — **met**.

---

## Full-suite checkpoints

The plan suggested full-suite runs at the ends of Phases C, D, G, J, L, N, P.
Given the above statuses, every designated phase is at `DONE`, and the contract
tests covering the authoritative flow / SKILL surface are green after each
doc-level change (V3 refactor complete through Phase M/P).

**Known boundary (not a gap in this refactor):** the deterministic CLI
loader/digest (`verify-model`) validates `SemanticModel` only. The V3
LLM-authored artifacts — `DocumentationModel`, `DocumentationPlan`, `PageSpecs`
— are pydantic-validated on load and carried on `OrchestrationState` (and, for
the plan, cross-checked by `plan_page_consistency_errors`), but Python
deliberately does not digest or score semantic/judgment content in them. This is
the documented two-plane boundary, not unimplemented work.

## Explicitly deferred

The following remain intentional non-goals (not required for this refactor):
live browser screenshots, runtime API probing, interactive Swagger Try-It,
framework-specific AST route generators, host-specific adapters, a Python
semantic scheduler, and a full OpenAPI emitter.

---

## Architecture Freeze (benchmark-driven optimization)

MakeWiki V3 has passed the full structure/contract gate
(`V3-FULL-CONTRACT-GATE` → **PASS — ARCHITECTURE FREEZE RECOMMENDED**) and now
enters **benchmark-driven optimization**. Until the real NewAPI benchmark runs,
the following architecture defaults are **frozen**:

- authoritative V3 pipeline
- stable role families
- SubtaskSpec
- RepositoryBrief
- InvestigationPlan
- ClaimBundle
- SemanticModel boundary
- DocumentationModel
- DocumentationPlan
- PageSpec
- Reviewer / Revision split
- InterfaceReference hierarchy
- L0 - L5
- SemanticAuditBundle
- SitePresentationPlan authority boundary

**Not allowed before the benchmark** (no "make it prettier" changes):
- adding a new Agent role family
- adding a new graph engine
- adding a host adapter
- adding a framework-specific scanner
- adding Python semantic inference
- restructuring the whole model hierarchy
- adding a new verification level

**Only the following evidence may lift the freeze:**
1. a reproducible problem in the benchmark;
2. an artifact cannot express real project semantics;
3. the current contract causes a definite error;
4. an explicit portability failure;
5. a performance trace showing an architecture-level bottleneck.

General prompt-wording issues should preferably be fixed in the task /
reference layer, not by changing the architecture.

