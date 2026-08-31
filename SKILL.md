---
name: makewiki
description: "Generate evidence-backed multilingual wiki documentation and an offline static website for a software project using autonomous collaborative LLM subagents and ReBattle competitive verification. Use when: user asks to generate wiki, docs, documentation, enterprise delivery manuals, or multilingual docs for a project."
version: "2.0.0"
argument-hint: "[--lang <code>...] [--output <dir>] [--theme <auto|light|dark>]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Write Edit Glob Grep WebFetch
---
# MakeWiki v2 - LLM-First, Evidence-Backed Documentation Compiler

MakeWiki is an **LLM-first, evidence-backed, multi-agent documentation compiler**.
The LLM (Skill layer) decides what the repository means; Python (toolkit layer)
proves what can be mechanically proven. Documentation is evidence-backed with
layered automated verification (L0 - L5) and a single Quality Gate.

This file binds skill `2.0.0` to toolkit `2.0.0`. The bootstrap script pins
the matching tag via `MAKEWIKI_TOOLKIT_VERSION`, the Git identity via
`MAKEWIKI_TOOLKIT_COMMIT` (Git install) and the archive integrity checksum via
`MAKEWIKI_TOOLKIT_ARCHIVE_SHA256` (Archive install).

---

## 1. Two-Plane Architecture (双平面拓扑)

MakeWiki runs on **two strict planes** separated by a hard boundary. The
cognitive plane owns meaning; the mechanical plane owns proof.

```yaml
two_plane_topology:

  cognitive_plane:
    role: "LLM (Skill + Subagents) decides what the repository means"
    owns:
      - Project comprehension and intent
      - FAQ, troubleshooting, usage examples, workflows, personas
      - Diátaxis structure and narrative voice
      - Hedging language and uncertainty expression
      - Cross-examination (ReBattle) adjudication
    forbidden_at_runtime:
      - "Inventing content based on regex heuristics"
      - "Filling semantic gaps with default prose"
      - "Trusting Python heuristics over LLM judgment"

  mechanical_plane:
    role: "Python toolkit proves what can be mechanically proven"
    owns:
      - Repository fact census (traits, file counts, languages, manifests)
      - Evidence extraction (commands, configs, paths, versions, env vars)
      - AST / CLI / config / manifest parsing
      - L0 syntax, L1 existence, L2 interface, L4 exact-block parity
      - Static site, export, sync-bundle, validate
      - Quality Gate aggregation and CI exit code
    forbidden_at_runtime:
      - "Returning any content the LLM should have produced"
      - "Guessing when a check is unprovable (returns UNKNOWN instead)"

  bridge:
    - Skill calls Python only for mechanical steps
    - Python returns structured facts, never interpretations
    - Quality Gate aggregates layer statuses; Main Agent decides workflow progression
```

### Cognitive Authority Boundary

LLM Agents are the authoritative decision makers for semantic work. Python
tooling MUST NOT invent semantic conclusions. When deterministic tooling
cannot mechanically establish a fact, it MUST return UNKNOWN rather than
guess. Python-generated semantic conclusions MUST NOT override LLM Agent
adjudication in the authoritative `/makewiki` path.

**LLM = sole runtime orchestrator & judge of truth. Python = auditable mechanical evidence channel.**

- Python is an auditable evidence channel, not an infallible authority. If
  Python evidence conflicts with direct source inspection, the Main Agent
  must investigate directly via inspection tools (`Glob`, `Grep`, `Read`) and
  adjudicate based on direct codebase reality.
- Python MUST NOT invent semantic conclusions (FAQ, troubleshooting, usage,
  workflows, personas, install steps, verify commands). When Python cannot
  prove something it returns `UNKNOWN` and leaves the slot empty for the LLM
  to fill via the Skill layer.
- Mechanical tool failures (e.g. AST parsing errors or unhandled file formats)
  produce degraded mechanical verification (`pending_mechanical_verification`),
  never cognitive failure; the Main Agent may spawn a Recovery Scout for direct
  codebase inspection.
- The Quality Gate aggregates verification status and reports CI exit codes;
  the Main Agent decides whether to iterate revisions, accept pending items,
  or ship.

### Mechanical UNKNOWN, Never Guess

When Python cannot mechanically prove a field, the slot is left empty and an
`UNKNOWN` marker is emitted so the LLM (or a human reviewer) can fill it. The
default scaffolding never invents install steps, verify commands, or FAQ
content — that work belongs to the LLM.

---

## 2. Authoritative Pipeline (LLM-Orchestrated, Subtask-First)

The `Main Agent` orchestrates the authoritative V3 pipeline. Work is decomposed
into **subtasks** (see `references/v3/SUBTASK_PROTOCOL.md`); subagents are LLM
agents; Python is invoked between phases as **optional mechanical proof
tooling** — its `census` / `evidence` output is supporting material, never a
prerequisite or a dictating authority.

```yaml
authoritative_pipeline:

  orientation:
    cognitive: "Main Agent conducts Repository Orientation — reads high-information entries, forms an initial hypothesis, identifies personas & major domains, authors RepositoryBrief + InvestigationPlan"
    mechanical: "python run_toolkit.py census <target>  # OPTIONAL supporting evidence (raw traits); never a prerequisite"
    output: "RepositoryBrief + InvestigationPlan (subtask-first)"

  investigation:
    cognitive_subagents: "Investigation (Explorer) subtasks — one coherent semantic domain per subtask per the InvestigationPlan; each returns an evidence-backed ClaimBundle"
    mechanical: "python run_toolkit.py evidence <target>  # OPTIONAL supporting facts extraction"
    output: "per-domain ClaimBundles"

  semantic_synthesis:
    cognitive_subagents: "Semantic Analyst reconciles RepositoryBrief + InvestigationPlan + ClaimBundles into the canonical SemanticModel"
    interaction: "Targeted conflict_resolution subtask, then optional ReBattle escalation, only for genuinely hard disputes — not the default for every disagreement"
    mechanical: "python run_toolkit.py rebattle-diff <claim-files>  # deterministic dispute ORGANIZER only; never decides truth"
    output: "adjudicated SemanticModel"

  documentation_modeling:
    cognitive_subagents: "Documentation Architect translates SemanticModel (what the software is) into DocumentationModel (who, for which goals: personas, capabilities, journeys, concepts, references)"
    output: "DocumentationModel"

  page_planning:
    cognitive_subagents: "Documentation Architect decides what documented intents exist and groups them into pages; emits DocumentationPlan + one PageSpec per page"
    output: "DocumentationPlan + PageSpec[]"

  writing:
    cognitive_subagents: "Parallel Language Writer subtasks — each writes exactly one PageSpec × one language directly from its semantic slice (never machine-translated)"
    mechanical: "python run_toolkit.py parity <target> --lang ...  # mechanical exact block-parity support"
    constraints:
      - "100% code-block (stable [[id:...]] IDs) and section marker parity across languages"
      - "Independent generation from SemanticModel — never machine-translated"

  review_and_revision:
    cognitive_subagents:
      - "Reviewer (READ-ONLY) — grounding, documentation fitness, audience fit, api_contract, cross-language, epistemic; emits ReviewFindings; does NOT edit pages in place"
      - "Revision Agent — implements ONLY the flagged pages; a fresh re-review decides completion (max 2 rounds, then escalate to Orchestrator)"
      - "Auditor — L3 behavior, L4b prose-parity, L5 epistemic review; emits the SemanticAuditBundle (preserved)"
    mechanical: "python run_toolkit.py verify-docs <target> --semantic-audit <file>  # L0-L5 unified run + Quality Gate"

  integration:
    cognitive: "Site Designer / Integrator (Main Agent or delegated subagent) authors the SitePresentationPlan from the DocumentationPlan + passed reviewed drafts only — never re-researches the source"
    mechanical: "python run_toolkit.py build-site <wiki_dir>  # consumes SitePresentationPlan; pending/unavailable without it — never fabricated IA"

  verify_and_deliver:
    mechanical:
      - "python run_toolkit.py verify-docs <target> --semantic-audit <file>  # final Quality Gate re-run"
      - "python run_toolkit.py export <wiki_dir> --format html|epub|all  # pdf rejected"
      - "python run_toolkit.py sync-bundle <wiki_dir> --target confluence|notion  # bundle-prep only, no publish"
    cognitive: "Main Agent decides final delivery condition based on audit, coverage, and user goal"
```

Python never performs semantic repair: the corrective loop is a Reviewer +
separate Revision Agent (cognitive), not mechanical in-place editing.

### Host Capability Fallback

MakeWiki runs on three classes of host. The Main Agent inspects host capability
before dispatching and adapts the topology without losing the cognitive plane's
authority.

| Capability                                   | parallel        | sequential       | solo (no subagents) |
| :---                                         | :---            | :---             | :---                |
| `supports_subagents`                         | yes             | yes              | no                  |
| `supports_parallel_subagents`                | yes             | no               | no                  |
| `max_parallelism`                            | host-reported   | 1                | 1                   |
| `supports_file_write`                        | yes             | yes              | host-dependent      |
| `supports_web`                               | yes             | yes              | host-dependent      |

Strategy:

- **parallel**: launch scout and writer subagents concurrently within budget.
- **sequential** (subagents but no parallelism): Main Agent runs subagents
  one after another; budget is identical but wall-clock is linear.
- **solo** (no subagent API at all): the Main Agent assumes each role in
  sequence — Orientation → Investigation → Semantic Synthesis → Documentation
  Modeling → Page Planning → Writing → Review → Revision → Integration → Verify
  → Deliver. No MakeWiki semantics are lost; only wall-clock changes.

The fallback is automatic and documented in the run report. "No subagent API"
is not "MakeWiki cannot run" — it is "MakeWiki runs sequentially on one agent."

---

## 3. Quality Gate (统一质量门)

The Quality Gate is the **honest four-state verdict** over all verification
layers — it is not a single PASS / FAIL. The verdict is one of:

- `passed` — every layer adjudicated and non-blocking (`passed == (verdict ==
  "passed")` strictly; a pending gate is never reported as passed).
- `pending_semantic_review` — the LLM layer (L3 / L4b / L5) has pending items.
- `pending_mechanical_verification` — a mechanical layer (L0 / L1 / L2 / L4a)
  is still pending.
- `failed` — any layer explicitly failed.

The Skill's audit step consults it before shipping; CI maps the verdict to an
exit code via the exit policy:

| Verdict                          | CI exit code |
| :------------------------------- | :----------- |
| `passed`                         | 0            |
| `failed`                         | 1            |
| `pending_semantic_review`        | 0 (when `allow_pending_llm_layers`, else 2) |
| `pending_mechanical_verification`| 3            |

```yaml
quality_gate:
  verdict_source: "evaluate_quality_gate(report, cfg)"
  result_schema: "QualityGateResult"
  fields:
    passed: bool
    verdict: passed | pending_semantic_review | pending_mechanical_verification | failed
    syntax_passed: bool               # L0
    existence_passed: bool            # L1
    interface_passed: bool            # L2
    behavior_passed: bool             # L3 (LLM-judged; may be pending)
    cross_language_passed: bool       # L4 (Python exact + LLM prose)
    epistemic_passed: bool            # L5 (LLM over-assertion review)
    grounding_score: float            # 0.0 .. 1.0
    unresolved_critical: int
    unresolved_major: int
    unresolved_minor: int
    revision_rounds: int
    details: dict
  ci_exit_code: "0 passed | 1 failed | 0/2 pending_semantic_review (0 granted by quality.allow_pending_llm_layers, else 2) | 3 pending_mechanical_verification"
  config:
    quality.min_grounding_score: 1.0  # float 0.0..1.0; the sole Quality Gate threshold
    quality.allow_pending_llm_layers: true  # EXIT POLICY ONLY: verdict stays PENDING; when true, pending_semantic_review exits 0, else honest base 2. Never turns pending into failed.
```

Layer ownership:

- **L0 / L1 / L2 / L4-exact**: Python (mechanical).
- **L3 / L4-prose / L5**: LLM-judged. Python provides the evidence list (low-
  confidence commands, ungrounded claims, paired passages); the Skill's
  Auditor reasons over it.
- The Gate surfaces every layer status. `pending` means "evidence available,
  judgment still owed" — never silently hidden.

Layer status semantics (honest contract, matches `verification/report.py`):

- `passed` — a verifier actually executed and proved the layer.
- `failed` — a verifier ran and found a contradiction.
- `pending` — no verifier ran / not yet proven (LLM-judged layers: L3
  behavior, L4 prose-parity, L5 epistemic, plus un-resolved claims).
- `unknown` — insufficient evidence to decide either way.
- `not_applicable` — genuinely irrelevant (e.g. L4 cross-language parity for a
  single-language project).
- `warning` — advisory; does not fail the gate.

Python never marks a layer `passed` without actually proving it; the Quality
Gate reports LLM-judged `pending` layers transparently rather than auto-
adjudicating semantics.

---

## 3A. SemanticAuditBundle (Auditor Output, L3 / L4b / L5)

The semantic layers — L3 behavior meaning, L4b prose parity, L5 epistemic
standing — are decided by the LLM Auditor, not by mechanical code. The
Auditor persists its verdicts into a **machine-readable `SemanticAuditBundle`**
JSON that the toolkit consumes without re-judging the semantics.

The bundle is **ITEM-LEVEL**: each `SemanticAuditVerdict` targets exactly one
`review_item_id` (e.g. `L3:README.md:make build`, `L4b:README:build`,
`L5:README.md:make build`). The merge maps each verdict to exactly one
verification check; review items the Auditor does NOT mention REMAIN PENDING.
A verdict for an unknown `review_item_id` (matching no expected review item)
REJECTS the whole bundle — it is never silently ignored.

### The Auditor MUST emit the bundle

In the **Verify** step (and in the review subskill), after reasoning over L0 - L5, the
Auditor writes a `SemanticAuditBundle` JSON (dispatched per Section 6; spec lives
in `tasks/review.md` / `tasks/revise.md` and this section). Each semantic verdict
is recorded per review item; a layer or item the Auditor does not mention simply
remains `pending` at the Quality Gate *by absence* — never by an explicit value.

### Review item registry

After mechanical verification, the report exposes `review_items` — the
expected semantic review items for L3 / L4b / L5 that need LLM adjudication.
The registry is built from the pending semantic checks (each with a
deterministic `review_item_id`). The bundle can only adjudicate items that
exist in this registry; a verdict for any `review_item_id` not in the registry
rejects the whole bundle.

The bundle schema (`SemanticAuditBundle`, see
`src/makewiki_skills/verification/semantic_audit.py`) is:

```yaml
schema_version: 1                       # bundle schema version
documents_digest: "sha256:<hex>"        # sha256 over the audited markdown doc set
semantic_model_digest: "sha256:<hex>"   # optional; binds to the SemanticModel snapshot
auditor: "llm_auditor"                  # auditor identity
audited_at: "<UTC ISO-8601>"            # when the audit was performed
verdicts:                               # list of semantic verdicts
  - review_item_id: "L3:README.md:make build"   # exactly one review item per verdict
    layer: "L3"                         # one of L3 | L4b | L5
    status: "passed"                    # one of passed | failed
    rationale_summary: "..."            # why the Auditor judged this way
    evidence_refs: ["src/app/cli.py:120-148"]   # optional source citations
    confidence: "medium"                # one of high | medium | low
```

`documents_digest` includes document identity: it hashes each file as
`relative_path + NUL + byte_length + NUL + file_bytes + NUL`, sorted by
normalized relative path — so the digest changes on content edit, rename,
delete, add, and file split, and is stable across machines (no absolute paths
are hashed); it binds the audit to the exact document revision it was performed
against.

`semantic_model_digest` (optional) is the canonical SHA256 of the SEPARATE
authoritative SemanticModel the bundle claims to have been audited against. It
is proven by supplying the current model via `verify-docs --semantic-model
<file>`; the digest uses sorted keys and compact separators so it is stable.

### Staleness rule

If the documents (or the optional semantic model snapshot) change **after** the
bundle was produced, the bundle's digest no longer matches, so the bundle is
**stale and must be rejected and re-audited**. The toolkit raises a stale-audit
error rather than silently trusting an audit of an older revision. The Auditor
must therefore emit the bundle **last**, after all revisions (Review / Revision
are settled), so its `documents_digest` matches the final markdown set on disk.

### Consumption boundary

Python validates the bundle's schema and digests and aggregates the verdicts
ITEM-LEVEL into the Quality Gate, but it **never re-judges the semantic
verdicts**: it does not decide whether a `passed`/`failed` verdict is
reasonable, and it never overrides the Auditor's adjudication. Each verdict
maps to exactly one check by its `review_item_id`; a layer the Auditor did not
mention, or a `review_item_id` it did not adjudicate, stays `pending`. Merged
checks carry `verification_source = "semantic_audit_bundle"` as a formal
source, plus the verdict's `review_item_id` and the Auditor's structured
provenance (`check.provenance`: auditor, rationale_summary, evidence_refs,
confidence, audited_at).

### `verify-docs --semantic-audit <file>` and `--semantic-model <file>`

The Auditor's bundle is machine-consumed by `verify-docs` via the
`--semantic-audit <file>` flag, and the current SemanticModel is supplied via
`--semantic-model <file>` (both flags on the existing `verify-docs` command,
not separate commands):

```bash
python run_toolkit.py verify-docs <target> \
  --semantic-audit <output_dir>/semantic_audit.json \
  --semantic-model <output_dir>/semantic_model.json
```

`verify-docs --semantic-audit <file>`:

1. loads and schema-validates the bundle;
2. verifies `documents_digest` against the current documents — a
   mismatched (stale) bundle is **rejected** and the affected layers remain
   `pending`, signaling that a re-audit is required;
3. builds the review-item registry from the pending L3 / L4b / L5 checks, then
   merges the Auditor's verdicts ITEM-LEVEL by `review_item_id` — each verdict
   adjudicates exactly one check; unmentioned pending items stay `pending`; a
   verdict for an unknown `review_item_id` REJECTS the whole bundle (never
   silently ignored);
4. never re-judges the semantics — it only validates schema/digests and
   aggregates.

`--semantic-model <file>` supplies the current SemanticModel; its canonical
SHA256 (sorted keys, compact separators) proves the bundle's
`semantic_model_digest`. If the bundle declares a `semantic_model_digest` but
no `--semantic-model` is given, the model binding is **UNPROVEN** and L3 / L4b
/ L5 stay `pending` (the bundle is never silently trusted); a digest mismatch
is **STALE** and the bundle is rejected.

---

## 4. Dynamic Self-Configuration & Subagent Synthesis

The Main Agent **dynamically synthesizes subagent roles** from an open
**Archetype Library**; the planning reads `agent.max_subagents`,
`agent.max_parallelism`, and `agent.safety_max_rounds` from `makewiki.config.yaml`
(LLM-consumed upper bounds and safety ceilings).

```yaml
dynamic_synthesis_rules:
  monorepo_or_microservices:
    trigger: "Multiple services, workspaces, or sub-packages detected"
    action: "Spawn dedicated Scout/Writer subagents per major service module"
  native_or_ffi_bindings:
    trigger: "C/C++, Rust FFI, WebAssembly, or Python C-extensions detected"
    action: "Synthesize Scout-ABI-Bindings to inspect header files and exported ABI"
  plugin_or_sdk_ecosystem:
    trigger: "Extensible plugin architecture or public client SDK detected"
    action: "Synthesize Scout-Ecosystem focusing on hook registration and SDK interfaces"
  git_fork_or_divergence:
    trigger: "Upstream fork or active divergence tracking detected"
    action: "Synthesize Scout-Fork to inspect patch sets and upstream diffs"
  version_migration_breakages:
    trigger: "Major version bumps, deprecated APIs, or changelog migrations detected"
    action: "Synthesize Scout-Migration to inspect breaking changes and upgrade paths"
  mechanical_tool_failure:
    trigger: "Python scanner/parser fails, throws AST syntax errors, or returns degraded facts"
    action: "Synthesize Recovery-Scout for direct cognitive codebase traversal and file inspection"

resource_limits_and_safety_caps:
  max_subagents: 10          # Upper bound on concurrently synthesized subagents
  max_parallelism: 10        # Host concurrency ceiling
  safety_max_rounds: 3       # Safety ceiling for debate / ReBattle convergence loops
```

---

## 5. Mandatory 4-Dimensional Self-Reflection Loop

Every Subagent runs a mandatory **4-dimensional self-reflection pass** before
submitting claims or writing documents. The loop is purely cognitive — it is
not enforced by Python.

```yaml
self_reflection_checklist:
  1_grounding_critique:
    question: "Is every command, argument flag, config key, and file path directly cited with actual code lines?"
    remedy: "Strip or explicitly hedge any speculative assertion as INFERRED / UNCONFIRMED."
  2_parity_critique:
    question: "Does my code sample, config snippet, or CLI invocation match 100% with the canonical SemanticModel?"
    remedy: "Synchronize parameter names and command syntax character-for-character."
  3_anti_ai_cliche_critique:
    question: "Did I generate binary tropes ('不是……而是……', '不仅……而且……'), empty buzzwords ('收敛', '赋能', '对齐'), or colon-stuffed headings?"
    remedy: "Rewrite in direct, natural, active engineer prose."
  4_adversarial_defense_critique:
    question: "If an opposing agent challenges this assertion with AST evidence, will this claim withstand inspection?"
    remedy: "Refine claim confidence: CONFIRMED_AST, DERIVED_CONFIG, HYPOTHESIS_HEDGED."
```

---

## 6. Subagent Dispatch (progressive disclosure)

The Main Agent dispatches subagent roles by **progressive disclosure**: SKILL.md
keeps a short pointer for each role; the full prompt contract lives in the
canonical `tasks/*.md` and `references/v3/` docs. SKILL.md does **not** re-embed a
fixed prompt by hand. Roles synthesize dynamically; on a solo host the Main Agent
assumes each role in sequence (no semantics are lost, only wall-clock).

| Role / trigger                                | Canonical spec                               | Output / verdict |
| :---                                          | :---                                         | :---             |
| Investigation / Explorer (one semantic domain) | `tasks/investigate.md`                       | `ClaimBundle`    |
| Recovery (mechanical-tool failure)            | `tasks/scan.md` §4                           | direct-inspection facts |
| Blind coverage (complex / large repos)        | `tasks/scan.md` §5                           | independent re-exploration |
| Debater (hard-conflict escalation only)       | `tasks/rebattle.md`                          | adjudicated dispute → Semantic Synthesis |
| Language Writer (one `PageSpec` × one language) | `tasks/write.md`, `tasks/write-page.md`     | native draft page (stable `[[id:...]]` + section markers) |
| Reviewer (read-only)                          | `tasks/review.md`, `tasks/revise.md`         | `ReviewFindings` → revised draft → re-review |
| Auditor (L3 / L4b / L5)                       | §3A `SemanticAuditBundle`                    | `semantic_audit.json` |

The legacy `SearchLedger` format (`<search_ledger>`) and its parser remain a
preserved V2 asset: `src/makewiki_skills/model/search_ledger.py` (
`SearchLedger` / `parse_search_ledger_markdown`) and
`src/makewiki_skills/evals/`. New V3 investigation work emits `ClaimBundle`
instead; the parser stays for backward compatibility.

---

## 7. Dynamic Subagent Planning & Search Loop

The Main Agent maintains the **Orchestration State** (`OrchestrationState`) and continuously iterates through the dynamic reflection loop:

```yaml
dynamic_search_loop:
  reflection_questions:
    1: "What do I still not understand about the system?"
    2: "What important repository areas are unexplored?"
    3: "Which facts are single-source or lack sufficient corroboration?"
    4: "Which tool failures need recovery?"
    5: "Which claims conflict?"
  scout_synthesis: "Synthesize targeted scouts from census needs within agent.max_subagents and max_parallelism"
  recovery_scout: "Spawned on mechanical tool failure or degraded fact extraction"
  blind_reviewer: "Dispatched on complex/large repos before ReBattle to catch missed entrypoints"
  termination_criteria: "Main Agent stops search when coverage gaps are closed and confidence is high"
```

---

## 8. Documentation Information Architecture (IA)

The Main Agent owns the **Information Architecture (IA)**. Diátaxis serves strictly as a **cognitive rubric** (Tutorials, How-To, Reference, Explanation), rather than a rigid list of mandatory filenames.

- **Bespoke Document Set**: The Main Agent designs the document hierarchy, page names, and nesting based on repository shape and user intent (no mandatory FAQ/Troubleshooting templates).
- **SitePresentationPlan (persisted)**: The Main Agent records the site's IA and visual direction as an LLM-authored `SitePresentationPlan` (written to `<wiki_dir>/site_presentation.json` or `.yaml`), covering project title/description, navigation (per-page `document_id`, `route`, localized `title`(s), `nav_group`, `ordering`, hierarchy), languages, and visual preferences. The static-site compiler consumes ONLY this plan — Python never derives navigation, page roles, ordering, or hierarchy from filenames or keywords. A Site Designer subagent may be dispatched by the Main Agent to author it.
- **Quality Standards**: Help developers understand the system quickly while providing comprehensive operational, configuration, and deployment runbooks where appropriate.
- **Stable Parity Keying**:
  - Technical fenced code blocks must carry `[[id:<slug>]]` (or `[[parity:ignore reason="..."]]`).
  - Multilingual reviewable H2 sections must carry `<!-- makewiki:section=<slug> -->`.
  - Parity is keyed on stable IDs; section order is flexible per language.
- **Anti-AI Cliché Rules**: Ban binary antitheses (`不是……而是……`), buzzwords (`收敛`, `赋能`), formulaic openings, and trailing colons. See `references/anti_ai_cliche.md`.

---

## 9. V3 LLM-Orchestrated Execution Workflow

### Arguments

Parse `$ARGUMENTS` for:
- `--lang <code>` (repeatable): Target language codes. Default: `en zh-CN`.
- `--output <dir>`: Output directory name. Default: `makewiki`.
- `--theme <auto|light|dark>`: Static site theme. Default: `auto`.

The authoritative flow is subtask-first and host-neutral: where the host
supports subagents, each cognitive phase below is delegated to a dedicated
subtask / subagent (see `tasks/*.md` and `references/v3/SUBTASK_PROTOCOL.md`);
on a solo host the Main Agent assumes each role in sequence. Python's `census`
/ `evidence` output is **optional** mechanical evidence, never a prerequisite.

### 1. Repository Orientation

1. The Main Agent conducts a rapid, high-information-density survey (see
   `tasks/orient.md`): read high-information entries, form an initial project
   hypothesis, identify personas and major semantic domains, surface
   uncertainties.
2. The Main Agent authors the `RepositoryBrief` and an `InvestigationPlan` of
   coherent semantic domains. Optionally run `census` / `evidence` for raw
   supporting facts; they are not mandatory and never dictate meaning.

### 2. Investigation

1. Decompose the `InvestigationPlan` into **SubtaskSpec** units — one coherent
   semantic domain per `type: investigation` subtask (see
   `tasks/investigate.md`).
2. Each Investigation subtask (child Explorer subagent, or Main Agent solo)
   returns an evidence-backed `ClaimBundle`. Ordinary ambiguity is resolved by
   re-checking primary evidence; only a genuine conflict escalates (below).
3. Optionally run `python <makewiki_root>/scripts/run_toolkit.py coverage .` to
   inspect mechanical fact discovery vs skipped paths; this is optional
   supporting evidence, never a semantic authority.

### 3. Semantic Synthesis

1. The Semantic Analyst reconciles the `RepositoryBrief`, `InvestigationPlan`,
   and `ClaimBundles` into the canonical **`SemanticModel`**
   (see `tasks/semantic.md`).
2. For a conflict that survives evidence re-check, spawn a targeted
   `conflict_resolution` subtask; only if it remains genuinely disputed, run an
   optional adversarial **ReBattle** (escalation, not the default — see
   `tasks/rebattle.md`). `rebattle-diff` is a deterministic organizer only.

### 4. Documentation Modeling

The Documentation Architect translates the `SemanticModel` (*what the software
is*) into the **`DocumentationModel`** (*who, for which goals*) — personas,
capabilities, journeys, concepts, references, interface references (see
`tasks/document-model.md`).

### 5. Page Planning

The Documentation Architect decides what documented intents exist and how they
are grouped into pages, emitting the **`DocumentationPlan`** and one
**`PageSpec`** per page (see `tasks/plan-pages.md`). Diátaxis is a cognitive
rubric, never a mandatory filename list.

### 6. Writing

1. Dispatch parallel Writer subtasks; each writes exactly **one `PageSpec` × one
   `language`** directly from its semantic slice (see `tasks/write.md`,
   `tasks/write-page.md`). Native generation only — never machine-translated.
2. Writers adhere to stable block IDs (`[[id:<slug>]]`) and section markers
   (`<!-- makewiki:section=<slug> -->`).
3. Python runs `python <makewiki_root>/scripts/run_toolkit.py parity <target>
   --lang ...` for mechanical exact block-ID support.

### 7. Review

1. A **read-only Reviewer** evaluates each drafted page against its evidence
   slice and the cross-language contract (see `tasks/review.md`), in one or
   more modes: `grounding`, `documentation_fitness`, `audience_fit`,
   `api_contract`, `cross_language`, `epistemic`.
2. The Reviewer emits a structured **`ReviewFindings`** artifact. It **does
   not** edit pages in place.

### 8. Revision

1. A separate **Revision Agent** implements `ReviewFindings` for only the
   flagged pages (see `tasks/revise.md`).
2. A fresh read-only re-review decides completion. The loop is bounded: **max 2
   revision rounds per page**; a page that still fails escalates to the
   Orchestrator (re-investigate or revise the `PageSpec` / `DocumentationModel`)
   rather than iterating indefinitely (QUALITY_POLICY §7).

### 9. Integration

The Site Designer / Integrator authors the **`SitePresentationPlan`** from the
`DocumentationPlan` and the passed reviewed drafts only (see
`tasks/integrate.md`), writing it to `<wiki_dir>/site_presentation.json` or
`.yaml`. The site compiler renders its navigation, ordering, hierarchy, routes,
and localized titles verbatim — it never derives an Information Architecture
from filenames. Without a plan the build reports pending/unavailable (never
fabricated IA, never blocks cognition).

```bash
python <makewiki_root>/scripts/run_toolkit.py build-site <output_dir> --theme auto
```

### 10. Verify

1. Python runs `python <makewiki_root>/scripts/run_toolkit.py verify-docs
   <target>` to compute the mechanical layers (L0 / L1 / L2 / L4a) and list
   pending semantic review items.
2. The Auditor performs the L3 behavior / L4b prose-parity / L5 epistemic
   review and emits the authoritative `SemanticAuditBundle`
   (`semantic_audit.json`) **last**, so its `documents_digest` matches the final
   audited markdown set.
3. Re-run `verify-docs --semantic-audit <output_dir>/semantic_audit.json` to
   verify the Quality Gate:
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
3. Main Agent evaluates the Quality Gate verdict, coverage completeness, and
   user requirements, deciding final delivery.
4. Present the completion report including:
   - Repository Census traits & subtasks/subagents deployed (with host-fallback mode)
   - Generated pages per language
   - Quality Gate verdict (four-state: passed / failed / pending_semantic_review / pending_mechanical_verification, CI exit code, grounding score)
   - L0 - L5 layer breakdown (passed / failed / pending counts)
   - Unresolved critical / major / minor items
   - Direct link to `makewiki/site/index.html`

---

## 10. Authoritative CLI Surface (Toolkit)

Python's CLI is **mechanical-only**. Each command either proves something or
returns `UNKNOWN`. None of them produce narrative content.

| Command                  | Alias        | Role                                                         |
| :---                     | :---         | :---                                                         |
| `census`                 | `sizing`     | Raw verifiable repository traits census (file counts, langs, manifests) |
| `evidence`               | `scan`       | Emit deterministic evidence facts (JSON / human)             |
| `coverage <target>`      | —            | Report discovery coverage: files/tests/configs/manifests discovered vs read, pruned (ignored) paths, mechanically-uncovered ecosystems, tool health |
| `verify-claim <json>`    | —            | Verify one or many Claims against the codebase               |
| `verify-model <json>`    | —            | Schema + evidence-ref validation for a SemanticModel         |
| `verify-docs <target>`   | `verify`     | Unified L0 - L5 verification + four-state Quality Gate + CI exit code; `--semantic-audit <file>` merges an LLM bundle item-level, `--semantic-model <file>` proves its model binding |
| `parity <target>`        | —            | L4 exact-block parity + aligned passages for LLM prose audit |
| `review <wiki_dir>`      | —            | Standalone cross-language review (runs `CrossLanguageReviewer`) |
| `semantic-review <dir>`  | —            | Prepare aligned passages for LLM cross-language review       |
| `validate <wiki_dir>`    | —            | Markdown structure & link validation (L0 helper)             |
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
Python-only, LLM-only, or Shared. The contract test
`tests/contracts/test_config_consumption_contract.py` enforces that no field is
dead or ambiguous:

- **Shared** (read by Python for mechanical enforcement AND by the LLM writer
  as guidance): none currently — the only formerly-shared fields
  (`documentation_policy.forbid_unfounded_praise`, `documentation_policy.
  banned_descriptors`) were relaxed to LLM-only once the mechanical prose
  checker was removed from `renderer/validator.py` (prose quality is cognitive
  judgment, so only the LLM writer consumes them now).
- **LLM-only**: `agent.*` (incl. `max_subagents`, `max_parallelism`,
  `max_total_agent_calls`, `cost_budget`, `max_audit_rounds`, `safety_max_rounds`),
  `delivery.*` (Writing-step writer page emission), `content_depth.*`
  (Writing-step writer authoring bounds), `language_profiles.*`, and all
  `documentation_policy.*` fields (`audience`, `structure_strategy`,
  `prefer_task_oriented_sections`, `include_architecture_analysis`,
  `include_directory_overview`, `include_source_walkthroughs`,
  `forbid_unfounded_praise`, `banned_descriptors`) — read by Skill
  / writers, NOT by Python. The contract's behavioral test asserts each
  LLM-only field is actually referenced in the authoritative Skill layer
  (`SKILL.md` / `tasks/`), and its negative test asserts no LLM-only field has
  a Python read.
- **Python-only**: `scan.*`, `review.*` (incl. the mechanical
  `enable_review_pair_generation`, which only gates the `semantic-review`
  preparation command — it never closes the authoritative LLM semantic audit),
  `quality.*`, `output_dir`, `languages`, `default_language`.
  These are the fields the authoritative mechanical CLI actually reads
  (`verify-docs`, `parity`, `review`, `build-site`, `export`, `sync-bundle`).
  `target_dir` is deliberately not listed: it is runtime state (the resolved
  run target) written by the config loader but never read back, so it is
  excluded from the consumption contract entirely (see `config.py`).

See `tests/contracts/test_config_consumption_contract.py`.

---

## 11. Working Notes

- **Autonomous execution**: Complete all phases end-to-end without pausing
  for intermediate confirmation.
- **Subtask-first (V3)**: decompose work into `SubtaskSpec` units; delegate
  each cognitive phase to a dedicated subtask / subagent where the host
  supports it (`references/v3/SUBTASK_PROTOCOL.md`); solo host assumes each
  role in sequence. `census` / `evidence` are optional mechanical evidence.
- **ReBattle = escalation**: resolve ordinary ambiguity by re-checking evidence
  or a targeted `conflict_resolution` subtask; only a genuinely hard dispute
  escalates to adversarial ReBattle. `rebattle-diff` is a deterministic
  organizer only and never decides truth (`tasks/rebattle.md`).
- **Review is read-only**: the Reviewer emits `ReviewFindings`; a separate
  Revision Agent implements flagged pages; a fresh re-review decides completion
  (`tasks/review.md`, `tasks/revise.md`).
- **Natural human engineer tone**: ban binary tropes, buzzwords, formulaic
  openings, trailing colons. See `references/anti_ai_cliche.md`.
- **Independent generation per language** from the SemanticModel; no machine
  translation.
- **100% code-block parity** across languages.
- **Ephemeral execution**: clean up temporary artifacts after each phase.
- **Version binding**: skill version (`2.0.0`) ↔ toolkit version (`2.0.0`)
  via the bootstrap script.
