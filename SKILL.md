---
name: makewiki
description: "Generate evidence-backed multilingual wiki documentation and an offline static website for a software project using autonomous collaborative LLM subagents. Use when: user asks to generate wiki, docs, documentation, enterprise delivery manuals, or multilingual docs for a project."
version: "3.0.0"
license: MIT
---
# MakeWiki v3 - LLM-First, Evidence-Backed Documentation Compiler

MakeWiki is an **LLM-first, evidence-backed, multi-agent documentation compiler**.
The LLM (Skill layer) decides what the repository means; Python (toolkit layer)
proves what can be mechanically proven. Documentation is evidence-backed with
layered automated verification (L0 - L5) and a single Quality Gate.

This file binds skill `3.0.0` to toolkit `3.0.0`. The bootstrap script pins
the matching tag via `MAKEWIKI_TOOLKIT_VERSION`, the Git identity via
`MAKEWIKI_TOOLKIT_COMMIT` (Git install) and the archive integrity checksum via
`MAKEWIKI_TOOLKIT_ARCHIVE_SHA256` (Archive install).

> **Progressive disclosure.** SKILL.md keeps only the authoritative workflow the
> Main Agent must know immediately. Detailed protocols, schemas, and rubrics are
> resolved on demand from `references/v3/*` (contracts, architecture, quality
> policy, multi-agent protocol) and `tasks/*` (per-phase operational specs). Full
> artifact contracts live in `references/v3/ARTIFACT_CONTRACTS.md`; the V3
> architectural statement in `references/v3/ARCHITECTURE.md`.

---

## 1. Two-Plane Architecture

MakeWiki runs on **two strict planes** separated by the Cognitive Authority
Boundary. The cognitive plane owns meaning; the mechanical plane owns proof.

- **Cognitive plane (LLM)**: decides what the repository means — project
  intent, FAQ, troubleshooting, usage examples, workflows, personas, Diátaxis
  structure, hedging, and (only for genuinely hard disputes) ReBattle
  adjudication. It is **forbidden** from inventing content from regex heuristics
  or trusting a Python heuristic over direct code reality.
- **Mechanical plane (Python)**: proves what can be mechanically proven —
  census, evidence, AST/CLI/config/manifest parsing, L0/L1/L2/L4-exact, static
  site, export, sync-bundle, schema validation, Quality Gate aggregation,
  CI exit code. It is **forbidden** from inventing narrative content; when it
  cannot prove a slot it returns `UNKNOWN`.

### Cognitive Authority Boundary

LLM agents are the authoritative decision makers for semantic work. Python is
an **auditable mechanical evidence channel**, not an infallible authority:

- If Python evidence conflicts with direct source inspection, the Main Agent
  investigates directly (via `Glob` / `Grep` / `Read`) and adjudicates from
  codebase reality.
- Python must not invent semantic conclusions; unchecked facts return
  `UNKNOWN` and the slot is left empty for the Skill layer to fill.
- **Mechanical UNKNOWN, never guess**: scaffolding never invents install steps,
  verify commands, or FAQ content — that work belongs to the LLM.
- Mechanical tool failures produce degraded mechanical verification
  (`pending_mechanical_verification`), never cognitive failure; the Main Agent
  may spawn a Recovery Explorer for direct inspection.
- The Quality Gate aggregates verification and reports CI exit codes; the Main
  Agent decides whether to iterate, accept pending items, or ship.

See `references/v3/COGNITIVE_BOUNDARY.md` and `references/v3/ARCHITECTURE.md` §1.

---

## 2. Authoritative Pipeline (LLM-Orchestrated, Subtask-First)

The Main Agent orchestrates the authoritative V3 pipeline. Work is decomposed
into **subtasks** (`references/v3/SUBTASK_PROTOCOL.md`); subagents are LLM
agents; Python runs between phases as **optional mechanical proof tooling** —
`census` / `evidence` are supporting material, never a prerequisite or a
dictating authority. The authoritative order is:

```text
Repository Orientation
→ Investigation Subtasks                 (one coherent semantic domain each)
→ ClaimBundles
→ Semantic Synthesis                     (canonical SemanticModel)
→ Documentation Modeling                 (DocumentationModel)
→ Documentation Planning                 (DocumentationPlan + PageSpec[])  [Phase 5/6]
→ Writing Subtasks                       (drafts)
→ Independent Review Subtasks            (ReviewFindings)
→ Revision Subtasks (when needed)        (re-review)
→ Integration                            (SitePresentationPlan)
→ Verification + Final Semantic Audit    (SemanticAuditBundle)
→ Quality Gate
→ Site / Export / Delivery
```

The detailed per-phase cognitive/mechanical responsibilities are in
`references/v3/ARCHITECTURE.md` §2 - §19 and the operational plan in §9 below.

### Stable roles, one level of delegation, host-neutral

The workflow uses **stable role families** — Explorer (Investigation),
Semantic Analyst, Documentation Architect, Writer, Reviewer, Integrator (Main
Agent = Orchestrator). The Main Agent **dynamically synthesizes SubtaskSpecs,
never new architecture-level role families**. Delegation is one level deep by
default; subagents do not keep spawning agents.

MakeWiki is **host-neutral** (see `references/v3/MULTI_AGENT_PROTOCOL.md`). It
delegates each cognitive phase to an **isolated subagent / delegated subtask**
via the **native host mechanism** when supported, runs independent subtasks **in
parallel when supported**, and falls back to **sequential** or **solo**
execution otherwise:

- **parallel** — launch investigation/Writer subagents concurrently within budget.
- **sequential** — subagents but no parallelism; budgets identical, wall-clock linear.
- **solo** (no subagent API) — the Main Agent assumes each role in sequence; no
  semantics are lost, only wall-clock.

"No subagent API" is not "MakeWiki cannot run". The fallback is automatic and
recorded in the run report.

### `agent.*` budgets (ceilings, never promises)

`agent.*` fields are **upper-bound budgets / safety ceilings**, not prescriptive
execution plans: `max_subagents` caps concurrently synthesized subtasks;
`max_parallelism` is the host concurrency ceiling; `max_total_agent_calls` and
`cost_budget` cap total work/spend; `max_audit_rounds` budgets the
review↔revision loop (the **only** audit-loop budget — never introduce a
separate revision-rounds knob); `safety_max_rounds` caps escalation. Subtask-level
parallelism is expressed per `SubtaskSpec`, and `solo`/`sequential` is detected
from host capability, never configured.

---

## 3. Quality Gate (统一质量门)

The Quality Gate is the **honest four-state verdict** over all verification
layers — not a single PASS/FAIL. The verdict is one of:

- `passed` — every layer adjudicated and non-blocking.
- `pending_semantic_review` — an LLM layer (L3 / L4b / L5) is pending.
- `pending_mechanical_verification` — a mechanical layer (L0 / L1 / L2 / L4a) is pending.
- `failed` — any layer explicitly failed.

Layer ownership: **L0 / L1 / L2 / L4-exact** are Python (mechanical);
**L3 / L4-prose / L5** are LLM-judged. The Gate surfaces every layer status;
`pending` means "evidence available, judgment still owed" — never silently
hidden, never auto-adjudicated by Python. Layer status semantics (`passed`,
`failed`, `pending`, `unknown`, `not_applicable`, `warning`) match
`verification/report.py` exactly.

CI maps the verdict to an exit code via the exit policy:

| Verdict                          | CI exit code |
| :------------------------------- | :----------- |
| `passed`                         | 0            |
| `failed`                         | 1            |
| `pending_semantic_review`        | 0 (when `quality.allow_pending_llm_layers`, else 2) |
| `pending_mechanical_verification`| 3            |

`allow_pending_llm_layers` is **exit-policy only**: it never turns pending into
failed. Full policy, the `QualityGateResult` schema, and exit-code details live
in `references/v3/QUALITY_POLICY.md` and `verification/report.py`.

---

## 4. SemanticAuditBundle (Auditor Output, L3 / L4b / L5)

The semantic layers — L3 behavior meaning, L4b prose parity, L5 epistemic
standing, cross-page semantic consistency — are decided by the **Final Semantic
Auditor** (LLM), not by mechanical code. In the **Verify** step, after reasoning
over L0 - L5, the Auditor writes a machine-readable **`SemanticAuditBundle`**
JSON that the toolkit consumes without re-judging the semantics.

- The bundle is **item-level**: each `SemanticAuditVerdict` targets exactly one
  `review_item_id`; the merge maps each verdict to exactly one verification
  check. A review item the Auditor does not mention **remains pending**; a
  verdict for an unknown `review_item_id` **rejects the whole bundle**.
- `documents_digest` (and optional `semantic_model_digest`) bind the audit to
  the exact revision audited; a mismatch means the bundle is **stale and
  rejected** and the affected layers stay pending. The Auditor must therefore
  emit the bundle **last**, after all revisions.
- Python validates schema and digests and aggregates item-level — it **never
  re-judges** a `passed`/`failed` verdict.

Consumed by `verify-docs` (not a separate command):

```bash
python run_toolkit.py verify-docs <target> \
  --semantic-audit <output_dir>/semantic_audit.json \
  --semantic-model <output_dir>/semantic_model.json
```

Bundle schema, digest format, staleness rule, and the consumption-boundary steps
are in `references/v3/QUALITY_POLICY.md` §1A.

---

## 5. Stable Role Families + Dynamic SubtaskSpec

The workflow uses a small set of **stable role families** — Explorer (with
Recovery and Blind-coverage focus variants), Semantic Analyst, Documentation
Architect, Writer, Reviewer, Integrator. The Main Agent reads the `agent.*`
budgets from `makewiki.config.yaml` and decomposes the authored
`InvestigationPlan` / `DocumentationPlan` into concrete SubtaskSpecs that the
stable families carry out — it synthesizes **subtasks, not new roles**.

Focus variants are flavors of the Investigation/Explorer family (Recovery on
mechanical-tool failure; Blind coverage on complex/large repos). They are
evidence hints that shape *how* an Explorer investigates — they never let
census/evidence dictate investigation topology, and they never become new
architecture-level roles. Triggers, budgets, and the recovery/blind protocols
are detailed in `references/v3/SUBTASK_PROTOCOL.md` and `tasks/scan.md` §2 - §3.

---

## 6. Subagent Dispatch (progressive disclosure)

The Main Agent dispatches subagents by **progressive disclosure**: SKILL.md
keeps a short pointer per stable role family; the full prompt contract lives in
the canonical `tasks/*.md` and `references/v3/` docs. SKILL.md does not re-embed
a fixed prompt. SubtaskSpecs synthesize dynamically against the stable families;
on a solo host the Main Agent assumes each role in sequence.

| Role / trigger                                | Canonical spec                               | Output / verdict |
| :---                                          | :---                                         | :---             |
| Investigation / Explorer (one semantic domain) | `tasks/investigate.md`                      | `ClaimBundle`    |
| Recovery (mechanical-tool failure)            | `tasks/scan.md` §2                           | `ClaimBundle` via direct inspection |
| Blind coverage (complex / large repos)        | `tasks/scan.md` §3                           | independent re-exploration |
| Debater (hard-conflict escalation only)       | `tasks/rebattle.md`                          | adjudicated dispute → Semantic Synthesis |
| Language Writer (one page × one language)       | `tasks/write.md`, `tasks/write-page.md`    | native draft page (stable `[[id:...]]` + section markers) |
| Reviewer (read-only)                          | `tasks/review.md`, `tasks/revise.md`         | `ReviewFindings` → revised draft → re-review |
| Final Semantic Auditor (L3 / L4b / L5)        | §4, `tasks/review.md`                        | `semantic_audit.json` |

The legacy `SearchLedger` format and parser remain a preserved V2 asset
(`src/makewiki_skills/model/search_ledger.py`, `src/makewiki_skills/evals/`);
new V3 investigation emits `ClaimBundle` instead.

---

## 7. Mandatory Self-Reflection Loop

Every subagent runs a mandatory **4-dimensional self-reflection pass** before
submitting claims or writing documents (purely cognitive; not Python-enforced):

1. **Grounding** — every command, flag, config key, and path cited to actual
   code; speculative assertions hedged with `high / medium / low` confidence and
   recorded `uncertainty`.
2. **Parity** — code/config/CLI samples match the canonical SemanticModel 100%.
3. **Anti-AI-cliché** — purge binary tropes, buzzwords, formulaic openings, and
   trailing colons; write direct, natural, active engineer prose.
4. **Adversarial defense** — would the claim withstand an opposing agent's
   AST-evidence challenge? Refine confidence; evidence backs the claim, it is
   not itself a confidence level.

See `tasks/write.md` §2 and `references/anti_ai_cliche.md`.

---

## 8. Documentation Information Architecture (IA)

Documentation IA is a **cognitive, LLM-authored** structure, with authority
split so no single agent both plans and renders the site. Diátaxis serves
strictly as a **cognitive rubric** (Tutorials, How-To, Reference, Explanation),
never a rigid filename list.

- **Documentation Architect** owns `DocumentationModel` / `DocumentationPlan` /
  PageSpecs — personas, capabilities, journeys, and the exact page set, grouping,
  and nesting (see `tasks/document-model.md`, `tasks/plan-pages.md`). It emits
  **one language-neutral PageSpec per `page_id`**.
- **Integrator** owns `SitePresentationPlan` assembly, written to
  `<wiki_dir>/site_presentation.json` or `.yaml` from the **approved**
  DocumentationPlan/PageSpecs and passed reviewed drafts only (see
  `tasks/integrate.md`) — title/description, navigation (per-page `route`,
  localized `title`s, `nav_group`, ordering, hierarchy), languages, visual
  preferences. It never re-invents IA for display convenience.
- **Main Agent (Orchestrator)** initiates planning subtasks and enforces gates;
  it does not directly invent the global IA, and keeps the final delivery
  decision (a gate, not an authorship role).
- **Python renders only**: the static-site compiler renders `SitePresentationPlan`
  verbatim; it never derives navigation, page roles, ordering, or hierarchy from
  filenames or keywords. Without a plan, `build-site` reports pending/unavailable
  — never fabricated IA.

**Stable parity keying**: technical fenced code blocks carry `[[id:<slug>]]`
(or `[[parity:ignore reason="..."]]`); multilingual reviewable H2 sections carry
`<!-- makewiki:section=<slug> -->`; parity keys on stable IDs, section order is
flexible per language. Anti-AI-cliché rules: see `references/anti_ai_cliche.md`.
The `SitePresentationPlan` schema lives in `references/v3/ARTIFACT_CONTRACTS.md`
§9 and `tasks/integrate.md`.

---

## 9. V3 LLM-Orchestrated Execution Workflow

### Arguments

Parse `$ARGUMENTS` for:
- `--lang <code>` (repeatable): Target language codes. Default: `en zh-CN`.
- `--output <dir>`: Output directory name. Default: `makewiki`.
- `--theme <auto|light|dark>`: Static site theme. Default: `auto`.

The authoritative flow is subtask-first and host-neutral: where the host
supports subagents, each cognitive phase below is delegated to a dedicated
subtask (see `tasks/*.md`, `references/v3/SUBTASK_PROTOCOL.md`); on a solo host
the Main Agent assumes each role in sequence. Python's `census` / `evidence` is
optional mechanical evidence, never a prerequisite.

### 1. Repository Orientation

The Main Agent conducts a high-information-density survey (`tasks/orient.md`):
read high-information entries, observe the tree, read existing docs, form a
project hypothesis, identify personas and major semantic domains, and record
uncertainty. It authors the **`RepositoryBrief`** and an **`InvestigationPlan`**
of coherent semantic domains. `census` / `evidence` are optional supporting
facts, never mandatory and never dictating meaning.

### 2. Investigation

Decompose the `InvestigationPlan` into **SubtaskSpec** units — one coherent
semantic domain per `type: investigation` subtask (`tasks/investigate.md`). Each
returns an evidence-backed **`ClaimBundle`**. Ordinary ambiguity is resolved by
re-checking primary evidence; only genuine conflicts escalate (below). Optionally
run `python <makewiki_root>/scripts/run_toolkit.py coverage .` for mechanical
fact discovery vs skipped paths — supporting evidence, never a semantic authority.

### 3. Semantic Synthesis

The Semantic Analyst reconciles the `RepositoryBrief`, `InvestigationPlan`, and
`ClaimBundles` into the canonical **`SemanticModel`** (`tasks/semantic.md`). For
a conflict that survives evidence re-check, spawn a targeted `conflict_resolution`
subtask; only if it remains genuinely disputed, run an optional adversarial
**ReBattle** (escalation, not the default — `tasks/rebattle.md`). `rebattle-diff`
is a deterministic organizer only, never decides truth.

### 4. Documentation Modeling

The Documentation Architect translates the `SemanticModel` (*what the software
is*) into the **`DocumentationModel`** (*who, for which goals*) — personas,
capabilities, journeys, concepts, references, interface references
(`tasks/document-model.md`). The operator persona is first-class where a
production surface exists.

### 5. Page Planning

The Documentation Architect decides what documented intents exist and how they
are grouped into pages, emitting the **`DocumentationPlan`** and one
**language-neutral `PageSpec`** per `page_id` (`tasks/plan-pages.md`). Diátaxis
is a cognitive rubric, never a mandatory filename list.

### 6. Writing

1. Dispatch parallel Writer subtasks; each writes exactly **one page (`page_id`) ×
   one `language`** from the shared language-neutral `PageSpec` (`tasks/write.md`,
   `tasks/write-page.md`). A single canonical PageSpec produces every language's
   draft via `PageSpec × target language × LanguageProfile → draft`. Native
   generation only — never machine-translated.
2. Writers adhere to stable block IDs (`[[id:<slug>]]`) and section markers
   (`<!-- makewiki:section=<slug> -->`).
3. Python runs `python <makewiki_root>/scripts/run_toolkit.py parity <target>
   --lang ...` for mechanical exact block-ID support.

### 7. Review

A **read-only Page Reviewer** evaluates each drafted page for page-local fitness
and completeness against its evidence slice and the cross-language contract
(`tasks/review.md`): documentation fitness, audience fit, task completeness,
operator completeness, API contract completeness, obvious unsupported/grounding
defects, and page-local cross-language issues. It emits structured
**`ReviewFindings`** and does **not** edit pages in place. It may flag obvious
behavior/epistemic problems, but the authoritative L3 / L4b / L5 verdicts and the
`SemanticAuditBundle` are the **Final Semantic Auditor's** job (§4).

### 8. Revision

A separate **Revision Agent** implements `ReviewFindings` for only the flagged
pages (`tasks/revise.md`). A fresh read-only re-review decides completion. The
loop is bounded by the single authoritative budget **`agent.max_audit_rounds`**
(§2, `references/v3/QUALITY_POLICY.md` §7); a page still failing once the budget
is exhausted escalates to the Orchestrator (re-investigate or revise the
`PageSpec` / `DocumentationModel`) rather than iterating indefinitely.

### 9. Integration

The Integrator authors the **`SitePresentationPlan`** from the
`DocumentationPlan` and the passed reviewed drafts only (`tasks/integrate.md`),
writing it to `<wiki_dir>/site_presentation.json` or `.yaml`. The site compiler
renders its navigation, ordering, hierarchy, routes, and localized titles
verbatim — it never derives IA from filenames. Without a plan the build reports
pending/unavailable (never fabricated IA).

```bash
python <makewiki_root>/scripts/run_toolkit.py build-site <output_dir> --theme auto
```

### 10. Verify

1. Python runs `python <makewiki_root>/scripts/run_toolkit.py verify-docs
   <target>` to compute the mechanical layers (L0 / L1 / L2 / L4a) and list
   pending semantic review items.
2. The **Final Semantic Auditor** performs the L3 behavior verdicts / L4b
   cross-language semantic parity / L5 epistemic standing / cross-page semantic
   consistency review and emits the authoritative `SemanticAuditBundle`
   (`semantic_audit.json`) **last**, so its `documents_digest` matches the final
   audited markdown set. It does not re-run the earlier Documentation / Page
   Review stages (page splitting, persona IA soundness, how-to structure, or
   whether a PageSpec should exist feed in from those stages).
3. Re-run to verify the Quality Gate:
   ```bash
   python <makewiki_root>/scripts/run_toolkit.py verify-docs <target> --semantic-audit <output_dir>/semantic_audit.json --semantic-model <output_dir>/semantic_model.json
   ```

### 11. Deliver

1. Prepare delivery bundles (mechanical):
   ```bash
   python <makewiki_root>/scripts/run_toolkit.py export <wiki_dir> --format html|epub|all --lang <code>
   python <makewiki_root>/scripts/run_toolkit.py sync-bundle <wiki_dir> --target confluence|notion --lang <code>
   ```
   `export` rejects `--format pdf`. `sync-bundle` only **prepares** bundles on
   disk; it does NOT publish.
2. Clean up temporary scratch logs.
3. The Main Agent evaluates the Quality Gate verdict, coverage completeness, and
   user requirements, deciding final delivery.
4. Present the completion report: repo census traits & subtasks/subagents
   (with host-fallback mode); generated pages per language; the four-state
   Quality Gate verdict (CI exit code, grounding score); the L0 - L5 layer
   breakdown; unresolved critical / major / minor items; and the direct link to
   `makewiki/site/index.html`.

---

## 10. Authoritative CLI Surface (Toolkit)

Python's CLI is **mechanical-only**. Each command either proves something or
returns `UNKNOWN`; none produce narrative content.

| Command                  | Alias        | Role                                                         |
| :---                     | :---         | :---                                                         |
| `census`                 | `sizing`     | Raw verifiable repository traits census                       |
| `evidence`               | `scan`       | Emit deterministic evidence facts (JSON / human)             |
| `coverage <target>`      | —            | Discovery coverage report (files/tests/configs vs read)      |
| `verify-claim <json>`    | —            | Verify one or many Claims against the codebase               |
| `verify-model <json>`    | —            | Schema + evidence-ref validation for a SemanticModel         |
| `verify-docs <target>`   | `verify`     | Unified L0 - L5 + Quality Gate + exit code (see §4 flags)    |
| `parity <target>`        | —            | L4 exact-block parity + aligned passages for LLM prose audit |
| `review <wiki_dir>`      | —            | Standalone cross-language review                              |
| `semantic-review <dir>`  | —            | Prepare aligned passages for LLM cross-language review       |
| `validate <wiki_dir>`    | —            | Markdown structure & link validation (L0 helper)             |
| `lint-drafts <wiki_dir>` | —            | Integration-time mechanical draft hygiene lint (pre-verification) |
| `build-site <wiki_dir>`  | —            | Compile Markdown into offline SPA HTML site                  |
| `export <wiki_dir>`      | —            | `--format html|epub|all`; **rejects pdf**                   |
| `sync-bundle <wiki_dir>` | `sync`       | Prepare Confluence / Notion bundles; **does NOT publish**    |
| `init-config <target>`   | —            | Generate default `makewiki.config.yaml`                      |
| `rebattle-diff <files>`  | —            | Deterministic dispute organizer over multiple ClaimSets      |

Backward-compat aliases (`scan`, `verify`, `sync`, `sizing`) remain so existing
scripts keep working. `sizing` is the deprecated alias of `census`. The
authoritative flow is `/makewiki`. `review` is a standalone command, not an
alias of `parity`.

### Config Consumption Contract

Every field in `makewiki.config.yaml` maps to exactly one consumer category —
Python-only, LLM-only, or Shared. `tests/contracts/test_config_consumption_contract.py`
enforces that no field is dead or ambiguous:

- **Shared** (Python + LLM): none currently — the former shared prose-judgment
  fields (`documentation_policy.forbid_unfounded_praise`,
  `documentation_policy.banned_descriptors`) are **LLM-only** once the
  mechanical prose checker left the renderer (prose quality is cognitive).
- **LLM-only** (referenced by the Skill layer / writers, not Python):
  `agent.*` (`max_subagents`, `max_parallelism`, `max_total_agent_calls`,
  `cost_budget`, `max_audit_rounds`, `safety_max_rounds`); `delivery.*`;
  `content_depth.*`; `language_profiles.*`; and all `documentation_policy.*`
  (`audience`, `structure_strategy`, `prefer_task_oriented_sections`,
  `include_architecture_analysis`, `include_directory_overview`,
  `include_source_walkthroughs`, `include_operator_persona`,
  `include_api_reference`, `forbid_unfounded_praise`, `banned_descriptors`).
  `documentation_policy.audience` and `delivery.audience` are **seed hints**, not
  gates; `include_operator_persona` / `include_api_reference` are additive seed
  probes that never manufacture a page or prose without evidence.
- **Python-only**: `scan.*`, `review.*` (incl. mechanical
  `enable_review_pair_generation`), `quality.*`, `output_dir`, `languages`,
  `default_language`. `target_dir` is runtime state, written by the loader but
  never read back, so it is excluded from the contract (see `config.py`).

See `tests/contracts/test_config_consumption_contract.py`.

---

## 11. Working Notes

- **Autonomous execution**: complete all phases end-to-end without pausing for
  intermediate confirmation.
- **Subtask-first (V3)**: decompose into `SubtaskSpec` units; delegate each
  cognitive phase where the host supports it (`references/v3/SUBTASK_PROTOCOL.md`);
  solo host assumes each role in sequence. `census` / `evidence` are optional
  mechanical evidence.
- **ReBattle = escalation**: resolve ordinary ambiguity by re-checking evidence
  or a targeted `conflict_resolution` subtask; only a genuinely hard dispute
  escalates to adversarial ReBattle (`tasks/rebattle.md`).
- **Review is read-only**: Reviewer emits `ReviewFindings`; a separate Revision
  Agent implements flagged pages; a fresh re-review decides completion.
- **Natural human engineer tone**: ban binary tropes, buzzwords, formulaic
  openings, trailing colons (`references/anti_ai_cliche.md`).
- **Independent generation per language** from the SemanticModel; no machine
  translation.
- **100% code-block parity** across languages.
- **Ephemeral execution**: clean up temporary artifacts after each phase.
- **Version binding**: skill version (`3.0.0`) ↔ toolkit version (`3.0.0`) via
  the bootstrap script.
