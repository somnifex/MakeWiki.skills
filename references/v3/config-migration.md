# MakeWiki V3 — Config Migration Note

> **Design + implementation record.** This document designs and records the
>
> accepted and its Micro Tasks (M-L1a..d, §6) are **implemented**: the additive
>
> (M-L1b / M-L1c) and are exposed in the default YAMLs, the audience fields are
>
> documented (M-L1d). Sections 1–5 record the design; §6 records the implemented
>

## 1. Purpose & scope

V3 replaces "one coarse audience string decides all documentation" with
persona-based modeling carried by the LLM artifacts:

```text
DocumentationModel.personas        (who uses the software)
PageSpec.audience                  (which personas a page serves)
API reference operator controls    (operator/admin interface requirements)
Quality Gate / Review              (audience-fit review mode)
```

Today `makewiki.config.yaml` expresses audience as coarse single-string,
LLM-consumed knobs (`delivery.audience`, `documentation_policy.audience`) plus a
set of boolean delivery toggles. These predate V3 and must migrate **without**
breaking the two-plane consumption contract, the `extra="forbid"` strictness, or
existing config files.

This note covers five areas:

1. `delivery.audience`
2. `documentation_policy.audience`
3. operator persona
4. API reference controls
5. agent parallelism

## 2. Current state (as of this note)

Reference: `src/makewiki_skills/config.py`.

| Field                                                | Default          | Vocabulary  | Category    |
| ---------------------------------------------------- | ---------------- | ----------- | ----------- |
| `delivery.audience`                                  | `"dual"`         | `dual \     | end-user \  | enterprise` | LLM_ONLY |
| `delivery.include_deployment_runbook`                | `true`           | bool        | LLM_ONLY    |
| `delivery.include_compatibility_matrix`              | `true`           | bool        | LLM_ONLY    |
| `delivery.include_health_checks`                     | `true`           | bool        | LLM_ONLY    |
| `documentation_policy.audience`                      | `"end-user"`     | free string | LLM_ONLY    |
| `documentation_policy.structure_strategy`            | `"user-journey"` | free string | LLM_ONLY    |
| `documentation_policy.prefer_task_oriented_sections` | `true`           | bool        | LLM_ONLY    |
| `agent.max_subagents`                                | `10`             | int 1..20   | LLM_ONLY    |
| `agent.max_parallelism`                              | `10`             | int 1..50   | LLM_ONLY    |
| `agent.max_audit_rounds`                             | `3`              | int 1..10   | LLM_ONLY    |
| `agent.safety_max_rounds`                            | `3`              | int 1..10   | LLM_ONLY    |
| `review.enable_review_pair_generation`               | `true`           | bool        | PYTHON_ONLY |

All of the above are **LLM_ONLY** (read by the Skill orchestrator / writers,
never by Python) except `review.*`, which is PYTHON_ONLY. No field is SHARED.

### Two-plane consumption contract (hard constraint)

Every public config field must resolve to exactly one consumer category
(`PYTHON_ONLY | LLM_ONLY | SHARED`); an unresolvable field is a contract
violation (`tests/contracts/test_config_consumption_contract.py`). Every
LLM_ONLY field's attribute name must appear (word-boundary) in the
**authoritative Skill layer** (`SKILL.md` + all `tasks/*.md`), and no LLM_ONLY
field may have a Python read. `target_dir` is runtime-only, excluded from the
contract. `extra="forbid"` means an unknown key in the YAML fails loudly at load
time.

**Consequence for migration:** we cannot rename or delete an LLM_ONLY attribute
without simultaneously updating `SKILL.md` / the relevant `tasks/*.md` (or
moving it to runtime-only), or the contract test fails. Each step below is
therefore designed to be safe on its own and to state its companion doc edits.

## 3. Tension analysis

### 3.1 `delivery.audience` vs `documentation_policy.audience` (redundancy)

Two different audience strings exist on two different classes:

- `delivery.audience` — "dual | end-user | enterprise" — biases enterprise /

  commercial delivery structure.
- `documentation_policy.audience` — free string ("end-user", "developer",

  "operator", ...) — biases technical depth and persona.

They overlap, can disagree, and neither is normative in V3. The V3
`DocumentationModel` is explicit: it must **not** use a single `audience: dual`
string to decide audience (`DOCUMENTATION_MODEL.md` §9). The real audience
decision lives in `DocumentationModel.personas` + per-page `PageSpec.audience`.

**Design decision:** both fields become **seed hints** (a cheap first guess for
the Documentation Architect / Orientation), never authoritative and never a
gate. The authoritative audience statement is the LLM-authored
`DocumentationModel` and `PageSpec` artifacts.

### 3.2 Operator persona is under-modeled in config

V3 treats operator as a **first-class persona** (`DOCUMENTATION_MODEL.md` §10),
with a mandatory operator checklist (deployment, config precedence, secrets,
health/readiness, metrics, logs, admin/management interfaces, maintenance,
upgrade/migration, backup/restore, failure recovery, capacity, dependencies),
and operator-specific API reference controls (`API_REFERENCE.md` §8-§10).
Today config has no operator-aware knob except the free-form
`documentation_policy.audience` and the `delivery.include_*` booleans. Operator
coverage is better decided by the Documentation Architect from evidence + the
SemanticModel, not by a config flag.

**Design decision:** do not add a `config.operator.*` block. Operator persona
is synthesized in `DocumentationModel` from the semantic evidence; config only
needs a light **seed flag** (see §4.3) so a user can opt operator documentation
in or out without scripting prose.

### 3.3 API reference controls belong to PageSpec, not config

V3 models `api_reference` as a `PageSpec.page_type`, whose `audience` list and
API-reference requirements are LLM-authored (`PAGE_SPEC.md`, `API_REFERENCE.md`).
Config today has no API-reference controls at all; the writer inferred depth
from `documentation_policy.audience`. A coarse string is a poor control for
"is there an operator/admin reference, a public-API developer reference, or
neither?"

**Design decision:** keep config minimal — a boolean **seed switch**
(`documentation_policy.include_api_reference`) that merely tells the
Documentation Architect whether to *look* for API/interface surfaces; the actual
page set/audience is decided in Page Planning from evidence. No new
config-carried API schema.

### 3.4 Agent parallelism knobs are already V3-correct

`agent.*` are already the V3 **budget / safety ceilings**: the Main Agent (the
sole runtime orchestrator) synthesizes subtasks within
`max_subagents` / `max_parallelism` and is bounded by `max_total_agent_calls`,
`cost_budget`, `max_audit_rounds`, `safety_max_rounds`. `max_audit_rounds`
already budgets the review/revision loop; the contract even asserts
`revision.max_rounds` must NOT appear (the loop is budgeted by
`agent.max_audit_rounds`, not by a separate revision config).

**Design decision:** no structural change to `agent.*`. The only migration note
is documentation: `agent.max_parallelism` maps to the host concurrency ceiling
(never a wall-clock or semantic promise), and V3 `SubtaskSpec` parallelism is
expressed per-subtask (see `references/v3/SUBTASK_PROTOCOL.md`) rather than by a
config flag. Keep `agent.max_subagents` as the cap on concurrently synthesized
subtasks.

## 4. Compatible migration design

Guiding principles:

- **No dead fields, no ambiguous fields.** Every field stays classified exactly

  once; we never add a field Python stops short of reading or the LLM stops
  short of referencing.
- **Config stays loadable.** Existing `makewiki.config.yaml` files with the

  current keys keep loading unchanged; we only re-document semantics and add
  defaults, never make an existing key an error.
- **Hint, don't gate.** Audience / operator / API-reference intent becomes a

  seed hint to the cognitive plane; the authoritative decision stays in the
  LLM artifacts (`RepositoryBrief`, `DocumentationModel`, `PageSpec`).
- **Micro-Task ready.** Each numbered step is small enough to be its own

  Micro Task, and each states the companion `SKILL.md` / `tasks/*.md` edit that
  keeps the LLM-referencing contract green.

### 4.1 Re-document `documentation_policy.audience` as a seed persona

- Keep the attribute (do not rename — the LLM-referencing contract requires

  `audience` to keep appearing in the Skill layer).
- Re-document its role: an **initial persona seed** for Repository Orientation /

  the Documentation Architect. Accepted loose vocabulary
  (`end-user`, `developer`, `operator`, `dual`) stays; unknown strings remain
  allowed (it is a hint, and the Architect confirms from evidence).
- Companion doc edit: `tasks/write.md` §3 already lists

  `documentation_policy.audience`; amend its wording to "seed persona hint —
  the authoritative audience lives in `DocumentationModel.personas` /
  `PageSpec.audience`". Required to keep the reference honest, not to satisfy
  the test (the string already appears).

### 4.2 Re-document `delivery.audience` and gate it to delivery structure only

- Keep the attribute (LLM_ONLY). Constrain its meaning to *delivery-structure

  bias* (does the user want enterprise-grade delivery pages: deployment
  runbook, compatibility matrix, health checks), **not** general audience.
- `dual | end-user | enterprise` stays as the seed; the Architect still

  confirms operator coverage from evidence.
- Companion doc edit: `tasks/write.md` §3 `delivery.*` bullet — clarify that

  the three `include_*` toggles "include production runbooks/matrix/health
  checks where **evidence supports them**", never force content into a page
  without source support (UNKNOWN stays empty).

### 4.3 Add an operator seed switch (additive, default preserves behavior)

- New LLM_ONLY field: `documentation_policy.include_operator_persona: bool =

  false`. Default `false` preserves current end-user bias, so no existing
  config changes meaning; users who need operator docs flip it on.
- It is a **seed** for the Documentation Architect: when true, the

  `DocumentationModel` must explicitly run the operator checklist
  (`DOCUMENTATION_MODEL.md` §10) and consider an operator/admin reference; when
  false, operator coverage is still synthesized if the evidence strongly
  implies an operator surface (the hint lowers the threshold, it does not gate).
- Companion docs: add `documentation_policy.include_operator_persona` to

  `tasks/document-model.md` (operator checklist gating) and to the
  LLM-consumed list in `tasks/write.md` §3. These edits are mandatory in the
  implementing Micro Task so the LLM-referencing contract sees the new
  attribute name.
- **No `config.operator.*` sub-block** — see §3.2.

### 4.4 Add an API-reference seed switch (additive)

- New LLM_ONLY field: `documentation_policy.include_api_reference: bool =

  false`. Default `false` preserves current behavior (no forced API reference).
- Seed meaning: when true, Page Planning must *look for* public-API and/or

  operator/management-API surfaces and, where proven, emit an
  `api_reference` PageSpec (with `audience` list and the operator controls in
  `API_REFERENCE.md` §8-§10). Still evidence-gated: no surface, no page, even
  with the flag on.
- Companion docs: reference it in `tasks/plan-pages.md` (api_reference page

  consideration) and `tasks/write-page.md` / `tasks/write.md` as a seed.
  Implementing Micro Task must add the attribute name to the Skill layer.

### 4.5 Agent parallelism: document, don't restructure

- Keep `agent.*` exactly as-is (already V3-ceilings).
- Re-document in `SKILL.md` §4 and `references/v3/SUBTASK_PROTOCOL.md` that:
  - `max_subagents` = cap on concurrently synthesized subtasks;
  - `max_parallelism` = host concurrency ceiling (never a promise of

    parallelism / wall-clock);
  - `max_audit_rounds` = budget for the review↔revision loop (must remain the

    only audit-loop budget; never introduce `revision.max_rounds`).
- No new config field. Optional future: a `solo`/`sequential` hint is **not**

  a config field — it is detected at runtime from host capability
  (`SKILL.md` §2 Host Capability Fallback).

## 5. Backward/forward compatibility summary

| Item                                            | Change                                   | Config-file impact                                                  | Contract impact                         |
| ----------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------- | --------------------------------------- |
| `documentation_policy.audience`                 | re-documented as seed persona            | none (same key)                                                     | none (still referenced)                 |
| `delivery.audience`                             | re-documented as delivery-structure bias | none                                                                | none (still referenced)                 |
| `documentation_policy.include_operator_persona` | **added**, default `false`               | none (extra=forbid only errors on unknown YAML keys, default fills) | LLM_ONLY; must reference in Skill layer |
| `documentation_policy.include_api_reference`    | **added**, default `false`               | none                                                                | LLM_ONLY; must reference in Skill layer |
| `agent.*`                                       | unchanged (docs only)                    | none                                                                | none                                    |

`extra="forbid"` note: the two new fields are **model defaults**, not YAML keys
users must write, so existing config files load unchanged. As implemented
(M-L1b / M-L1c), both are listed in
`DocumentationPolicyConfig._LLM_CONSUMED_FIELDS` and referenced in the
authoritative Skill layer in the same change (the LLM-referencing contract test
fails otherwise).

## 6. Sequencing (independent Micro Tasks, implementation status)

Each Micro Task below is **implemented** as of the V3 refactor (all four landed;
see MIGRATION_PLAN.md Phase M, STATUS: DONE). They are recorded here in advisory
order (semantics before additive fields so the contract stays green at every
commit); each was independent and small, and none required the next.

1. **M-L1a** — *DONE.* Re-documented `documentation_policy.audience` +

   `delivery.audience` as seed hints (config.py docstrings + SKILL.md "seed
   hints" wording; no config.py field change).
2. **M-L1b** — *DONE.* Added `documentation_policy.include_operator_persona`

   (config.py + `_LLM_CONSUMED_FIELDS` + `tasks/document-model.md` +
   `tasks/write.md` + default YAMLs).
3. **M-L1c** — *DONE.* Added `documentation_policy.include_api_reference`

   (config.py + `_LLM_CONSUMED_FIELDS` + `tasks/plan-pages.md` +
   `tasks/write*.md` + default YAMLs).
4. **M-L1d** — *DONE.* Documented `agent.*` parallelism semantics (SKILL.md §2 /

   §4 / SUBTASK_PROTOCOL; no config.py change).

## 7. Guardrails / non-goals

- **No Python read of any LLM_ONLY field.** New fields stay LLM_ONLY; Python

  never reads `documentation_policy.*` or `delivery.*` or `agent.*`.
- **No `config.operator.*` or `config.api.*` blocks** — operator/API decisions

  are LLM-authored artifacts, not config.
- **No `revision.max_rounds`** — the audit loop is budgeted by

  `agent.max_audit_rounds` only.
- **No forced content.** Audience/operator/API seeds must never manufacture a

  page or prose without evidence; `UNKNOWN` / absence remains the honest answer.
- **Do not delete `target_dir` handling** (runtime-only) and do not make any

  existing key an `extra="forbid"` error.