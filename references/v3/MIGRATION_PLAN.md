# MakeWiki V3 Migration Plan — Status Document

> **Live status, not a todo list.** This file records, per Phase, whether the
>
> local agent does **not** re-run already-completed V3 migration tasks.
>
> STATUS vocabulary: `DONE` (implemented and verified) / `PARTIAL` (some but not
>
> actually has), `REMAINING` (what is still missing), and `ACCEPTANCE` (the
>
> guessed.

## Strategy

Original direction: build the new path first, then switch the authoritative
flow, then clean up legacy descriptions. Do not rewrite the root `SKILL.md`
first. (This has now been completed through Phase L; see per-phase status.)

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

**REMAINING:** none. Legacy `scan` / `write` / `rebattle` / `review` task files
were intentionally retained (not deleted).

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

**STATUS: DONE** (with a structural note)

**IMPLEMENTED:** `src/makewiki_skills/model/orchestration_state.py` carries
`repository_brief`, `investigation_plan`, `documentation_model` (dict),
`page_specs` (list of dict).

**REMAINING:** `documentation_model` / `page_specs` are carried as free `dict`s;
there is no dedicated Pydantic model for them on `OrchestrationState` (they do
have dedicated models in `documentation_model.py` / `page_spec.py`). No Python
scheduler was introduced (correct — Python only serializes/validates).

**ACCEPTANCE:** V3 state fields exist, no Python scheduler — met.

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

**IMPLEMENTED:** `documentation_model.py` `DocumentationModel` models
personas / capabilities / journeys / concepts / references /
interface_references / documentation_gaps. Old `SemanticModel` fields
(user_tasks/faq/troubleshooting) remain readable for compatibility.

**REMAINING:** none.

**ACCEPTANCE:** new persona/capability/journey model present without deleting legacy
SemanticModel fields — met.

---

## Phase H — Operator/API Reference

**STATUS: DONE**

**IMPLEMENTED:** `InterfaceReference` + `HttpOperationReference` in
`documentation_model.py`; `tasks/document-model.md` §7 / §10 require the
Architect to explicitly consider operator / management-API / API-reference
surfaces where evidence supports them.

**REMAINING:** none. No framework-specific extractors were added (correct;
content is LLM-authored).

**ACCEPTANCE:** interface/API schema contracts present; Architect prompt
considers operator/API surfaces — met.

---

## Phase I — PageSpec-driven writing

**STATUS: DONE**

**IMPLEMENTED:** `page_spec.py` `PageSpec`; `tasks/write-page.md` exists; SKILL.md
§9.6 defines each Writer as writing exactly **one PageSpec × one language**
(no "one language writer writes the whole suite" default). Stable block IDs,
section markers, native multilingual writing, anti-cliché policy retained.

**REMAINING:** none.

**ACCEPTANCE:** Writer switched to `PageSpec × language` — met.

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

**IMPLEMENTED:** `DocumentationPlan` is the IA-upstream contract (YAML described
in `tasks/plan-pages.md`); the Integrator maps it to `SitePresentationPlan`
(`tasks/integrate.md`, SKILL.md §8 / §9.9). Python `SiteCompiler` renders the
plan only. Navigation is **recursive**: `site_presentation.py` recurses
`children` with no depth cap, and the two-level limitation was removed
(this session, V3-A3).

**REMAINING:** none. (`DocumentationPlan` has no dedicated Pydantic class — it is
an LLM-authored YAML contract; acceptable.)

**ACCEPTANCE:** recursive navigation allowed; renderer has no IA authority — met.

---

## Phase L — Switch authoritative SKILL

**STATUS: DONE**

**IMPLEMENTED:** root `SKILL.md` is switched to the V3 authoritative flow
(Orientation → Investigation → Semantic → DocumentationModel → PagePlan → Write →
Review → Revise → Integrate → Verify → Deliver; see SKILL.md §2 / §9). Census /
Evidence are optional mechanical assistance, never prerequisites. Legacy
`scan` / `write` / `rebattle` task files remain as compatibility references.
(Equivalent to the V3-K1 micro task.)

**REMAINING:** none.

**ACCEPTANCE:** SKILL.md authoritative flow is V3; legacy tasks are compatibility — met.

---

## Phase M — Config cleanup

**STATUS: PARTIAL**

**IMPLEMENTED:**
- `references/v3/config-migration.md` is a **design-only** note covering
  `delivery.audience`, `documentation_policy.audience`, operator persona, API
  reference controls, and agent parallelism — including the additive seed
  hints `documentation_policy.include_operator_persona` / `include_api_reference`
  and the independent M-L1a..d micro tasks.

**REMAINING:**
- `src/makewiki_skills/config.py` is **unchanged**: neither
  `include_operator_persona` nor `include_api_reference` is present
  (grep count = 0). The M-L1a..d micro tasks (re-document audience semantics;
  add the two seed fields; document `agent.*` parallelism) are **not**
  implemented.
- `agent.max_parallelism` default has not been re-baselined to a more
  conservative value.

**ACCEPTANCE:** audience fields re-documented / migrated toward persona-aware
planning and the additive operator/API seeds present — **not yet met**.

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

**STATUS: PARTIAL**

**IMPLEMENTED:**
- `README.md` and `README.en.md` were updated to the V3 authoritative pipeline
  (this session, V3-A5 / V3-A6): main flow, CLI table, LLM-designed page
  hierarchy, persona/operator/API-reference mentions.

**REMAINING:**
- `AGENTS.md`, `CLAUDE.md`, `CHANGELOG.md`, and `references/architecture.md`
  still describe the **V2 authoritative flow** (Census → Scout → ReBattle →
  Writer → Auditor). Per the Phase P rule "只有已经实现的能力才能写进去", these
  must be updated to the V3 flow once their edits are scheduled. Not changed by
  the Phase-A cleanup (out of its MODIFY-ONLY scope).

**ACCEPTANCE:** README/README.en/AGENTS/CLAUDE/CHANGELOG/references/architecture
all reflect only implemented capability — **not yet fully met**.

---

## Full-suite checkpoints

The plan suggested full-suite runs at the ends of Phases C, D, G, J, L, N, P.
Given the above statuses, all designated phases are at `DONE` or `PARTIAL`, and
the contract tests covering the authoritative flow/SKILL surface are green after
each doc-level change. When the Phase M / Phase P `REMAINING` items land, run the
full suite again.

## Explicitly deferred

The following remain intentional non-goals (not required for this refactor):
live browser screenshots, runtime API probing, interactive Swagger Try-It,
framework-specific AST route generators, host-specific adapters, a Python
semantic scheduler, and a full OpenAPI emitter.
