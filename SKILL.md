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

## 2. Authoritative Pipeline (LLM-Orchestrated)

The `Main Agent` orchestrates the authoritative pipeline. Subagents are LLM
agents; Python is invoked between phases as mechanical proof tooling.

```yaml
authoritative_pipeline:

  phase_0_census_and_state_init:
    cognitive: "Main Agent (initializes Orchestration State & plans dynamic search)"
    mechanical: "python run_toolkit.py census <target>  # raw verifiable repository facts"
    output: "Repository Fact Census (traits, file counts, langs, manifests) + Orchestration State"

  phase_1_dynamic_search:
    cognitive_subagents:
      - "Dynamic scouts synthesized from Census needs (Structure, Runtime/CLI, Config, Tests, Deployment, etc.)"
      - "Recovery Scout (dispatched on tool failure, coverage gaps, or conflicting evidence)"
      - "Blind Coverage Reviewer (independent unconditioned re-exploration for complex/polyglot repos)"
    mechanical: "python run_toolkit.py evidence <target>  # facts extraction"
    output: "Scout Search Ledgers (<search_ledger>) + updated Orchestration State"

  phase_2_rebattle:
    cognitive_subagents: "Dynamic dispute-derived debater archetypes (Fork Provenance, Runtime Truth, Ops, etc.)"
    mechanical: "python run_toolkit.py rebattle-diff <claim-files>  # dispute organizer"
    interaction: "Targeted adversarial cross-examination (Immediate Consensus Path if no disputes; dynamic convergence)"
    output: "adjudicated SemanticModel + LLM-authored ClaimSet"

  phase_3_writers_and_ia:
    cognitive: "Main Agent designs bespoke Information Architecture (IA) and authors the SitePresentationPlan; dispatches Per-Language Native Writers"
    mechanical: "python run_toolkit.py parity <target> --lang ...  # exact block parity"
    constraints:
      - "100% code-block (stable IDs) and section marker parity across languages"
      - "Independent generation from SemanticModel — never machine-translated"
      - "SitePresentationPlan (site IA + visual direction) is LLM-authored and persisted; Python never infers it from filenames"

  phase_4_audit_and_revise:
    cognitive_subagents: "Auditor (LLM) — L3 behavior review, L4 prose parity, L5 over-assertion, emits SemanticAuditBundle"
    mechanical: "python run_toolkit.py verify-docs <target> --semantic-audit <file>  # L0-L5 unified run"
    revision_loop: "Auditor edits Markdown in place until Quality Gate passes"

  phase_5_site_and_delivery:
    cognitive: "Main Agent decides final delivery condition based on audit, coverage, and user goal; it has already authored the SitePresentationPlan (site IA) in Phase 3"
    mechanical:
      - "python run_toolkit.py build-site <wiki_dir>  # consumes SitePresentationPlan; pending/unavailable without it — never fabricated IA"
      - "python run_toolkit.py export <wiki_dir> --format html|epub|all  # pdf rejected"
      - "python run_toolkit.py sync-bundle <wiki_dir> --target confluence|notion  # bundle-prep only, no publish"
```

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
  sequence — Scout → Red → Blue → Green → Judge → per-language writers → Auditor.
  No MakeWiki semantics are lost; only wall-clock changes.

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

In **Phase 4** and in the review subskill, after reasoning over L0 - L5, the
Auditor writes a `SemanticAuditBundle` JSON (see the Auditor prompt in Section
6). Each semantic verdict is recorded per review item; a layer or item the
Auditor does not mention simply remains `pending` at the Quality Gate *by
absence* — never by an explicit value.

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
must therefore emit the bundle **last**, after all in-place edits, so its
`documents_digest` matches the final markdown set on disk.

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

## 6. Subagent Dispatch Prompts (Archetype Library)

#### 1. Dynamic Scout Prompt Archetype

The Main Agent synthesizes scouts dynamically based on Census findings.
Each scout **directly inspects the repository** with `Glob` / `Grep` / `Read` / `Bash`
and terminates by outputting a structured `<search_ledger>` block.

```markdown
You are the {role} Scout for project '{project_name}'.
Assigned focus: {assigned_focus_scope}
Task: Directly inspect the repository using Glob, Grep, Read, and filesystem tools.
1. Trace relevant source directories, build manifests, entrypoints, and schemas.
2. For each key claim, cite concrete file paths and line ranges.
3. Explicitly surface (do not hide) any conflict or discrepancy between docs and code.
4. Output your findings strictly inside a `<search_ledger>` block:

<search_ledger>
# Role: {role}
**Confidence:** [0.0 - 1.0]

## Searched Areas
- [Architectural component inspected]

## Paths Inspected
- `path/to/inspected_file.ext`

## Claims & Evidence
1. **[claim_id]**: [Discovered fact]
   - *Evidence*: `file.ext:L10-20`

## Unresolved
- [Ambiguous topics or missing definitions]

## Unexplored
- [Paths or topics observed but not inspected]

## Recommended Follow-ups
- [Specific recommendations for subsequent scouts]
</search_ledger>
```

#### 2. Recovery Scout Prompt Archetype (Tool Failure Fallback)
```markdown
You are the Recovery Scout for project '{project_name}'.
Trigger: Mechanical tooling encountered errors or degraded verification on scope: {failed_scope}.
Task: Directly explore and inspect the codebase using LLM tools (`Glob`, `Grep`, `Read`) to extract ground truth facts.
1. Inspect the relevant source directories and files that mechanical tooling skipped or failed to parse.
2. Extract verified entrypoints, CLI parameters, configuration schemas, or runtime behaviors directly from code lines.
3. Record exact file paths and line number citations.
4. Output a verified fact bundle inside `<search_ledger>` and resolve any ungrounded assumptions.
```

#### 3. Blind Coverage Reviewer Prompt Archetype (Complex Repositories)
```markdown
You are the Blind Coverage Reviewer for project '{project_name}'.
Task: Without referencing any prior scout notes or draft documents, independently inspect the repository to identify the core runtime surfaces, critical entrypoints, configuration hierarchies, and major sub-packages.
1. Directly inspect the repository tree, root configs, entrypoints, and workflows.
2. Identify any overlooked subsystems, hidden entrypoints, or undeclared plugins.
3. Output your findings strictly inside a `<search_ledger>` block.
```

#### 4. Dispute-Derived Debater Prompt Archetype
```markdown
You are the {synthesized_debater_role} Debater for project '{project_name}'.
Disputed Topic: {disputed_semantic_key}
Competing Assertions: {competing_claims}
Task: Defend or cross-examine the disputed assertion using direct codebase citations (`Glob`, `Grep`, `Read`).
1. Verify whether the asserted behavior, parameter, or default value is proven in the AST/source code.
2. Check priority overrides (e.g. ENV vars vs CLI flags vs config files) or upstream fork differences.
3. If code contradicts your prior assumption, concede immediately and provide the corrected fact.
4. If code proves your claim, cite the exact file path and line numbers.
```

#### 5. Language Writer Subagent Prompt
```markdown
You are the {language_name} Documentation Writer for project '{project_name}'.
Write the complete documentation suite in {language_name} following the bespoke Information Architecture (IA) and unified SemanticModel provided by the Main Agent.
Requirements:
1. Independent generation: Write native, high-quality technical {language_name} directly from the SemanticModel — NEVER translate from another language output.
2. Code block parity: Every technical code block MUST carry its stable block ID marker `[[id:<slug>]]` and match character-for-character with the SemanticModel.
3. Section markers: In multilingual output, every reviewable H2 section MUST carry `<!-- makewiki:section=<slug> -->`. Section ordering may be adapted for native reading flow.
4. Self-Reflection: grounding, parity, anti-cliché, tone — natural engineer prose, no binary tropes, no buzzwords, no trailing colons.
Save all generated files under '{output_dir}/'.
```

#### 6. Reviewer & Quality Auditor Subagent Prompt
```markdown
You are the Quality Auditor and Reviewer for the generated documentation in '{output_dir}/'.
1. Run codebase grounding verification to confirm all mentioned commands, config keys, and file paths exist.
2. Run cross-language consistency review: every code block and parameter in English matches every other language 1:1, keyed on stable block IDs (`[[id:...]]`), never on position.
3. Scan for broken Markdown links and AI clichés.
4. Read the Quality Gate result from 'python run_toolkit.py verify-docs {output_dir}' and resolve any failed or pending layers in place.
5. Autonomous Self-Healing: if discrepancies, typos, or missing commands are found, edit the Markdown files in place immediately.
6. Emit a machine-readable `SemanticAuditBundle` JSON capturing your L3 / L4b / L5 semantic verdicts (see Section 3A). After every in-place edit, re-run the bundle so its `documents_digest` matches the final audited markdown set — never emit a bundle whose digest is stale against the files on disk. Save it as `<output_dir>/semantic_audit.json`.
```

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

## 9. Seven-Phase LLM-Orchestrated Execution Workflow

### Arguments

Parse `$ARGUMENTS` for:
- `--lang <code>` (repeatable): Target language codes. Default: `en zh-CN`.
- `--output <dir>`: Output directory name. Default: `makewiki`.
- `--theme <auto|light|dark>`: Static site theme. Default: `auto`.

### Phase 0: Repo Fact Census & Orchestration State Initialization

1. Run `python <makewiki_root>/scripts/run_toolkit.py census .` to gather raw repository traits.
2. Main Agent initializes `OrchestrationState` with user goals, initial repository understanding, and search plan.

### Phase 1: Dynamic Reconnaissance Loop & Search Ledgers

1. Main Agent dynamically spawns synthesized Scouts based on Census findings.
2. Scouts inspect the repository directly and return `<search_ledger>` deliverables.
3. If mechanical tools fail or confidence is low, spawn a **Recovery Scout**.
4. For large/complex repos, dispatch a **Blind Coverage Reviewer** before ReBattle.
5. Run `python <makewiki_root>/scripts/run_toolkit.py coverage .` to inspect mechanical fact discovery vs skipped paths.
6. Main Agent reflects on the 5 loop questions, reconciles coverage gaps, and updates Orchestration State.

### Phase 2: Dispute-Driven Dynamic ReBattle

1. Main Agent inspects Scout claims with `python run_toolkit.py rebattle-diff <claim-files>` to identify conflicts.
2. **Immediate Consensus Path**: If no disputes exist, skip debate and compile `SemanticModel` directly.
3. If conflicts exist, synthesize dispute-specific debater roles (e.g., `Fork Provenance`, `Runtime Truth`, `Config Hierarchy`).
4. Main Agent monitors convergence and terminates debate dynamically when facts stabilize, acting as Judge to synthesize the authoritative `SemanticModel`.

### Phase 3: Information Architecture & Native Multilingual Writing

1. Main Agent designs bespoke Information Architecture (IA) and page hierarchy.
2. Dispatches independent native Writer Subagents per target language.
3. Writers author native documentation adhering to stable block IDs (`[[id:<slug>]]`) and section markers (`<!-- makewiki:section=<slug> -->`).
4. Python runs `python <makewiki_root>/scripts/run_toolkit.py parity <target> --lang ...` for mechanical exact block-ID validation.

### Phase 4: LLM Semantic Audit & Quality Gate Verification

1. Python runs `python <makewiki_root>/scripts/run_toolkit.py verify-docs <target>` to compute mechanical layers and list pending semantic review items.
2. LLM Auditor evaluates behavioral meaning (L3), semantic prose parity (L4b), and epistemic accuracy (L5), performing in-place edits where needed.
3. LLM Auditor emits authoritative `SemanticAuditBundle` (`semantic_audit.json`).
4. Re-run `verify-docs --semantic-audit <output_dir>/semantic_audit.json` to verify Quality Gate:
   ```bash
   python <makewiki_root>/scripts/run_toolkit.py verify-docs <target> --semantic-audit <output_dir>/semantic_audit.json --semantic-model <output_dir>/semantic_model.json
   ```

### Phase 5: Offline Static Site Compilation (Mechanical)

The **Main Agent (or a dispatched Site Designer subagent)** authored
`SitePresentationPlan` to `site_presentation.json` during Phase 3. The site
compiler consumes that plan and renders its navigation, ordering, hierarchy,
routes, and localized titles verbatim — it never derives an Information
Architecture from filenames. Without a plan the build reports
pending/unavailable (never fabricated IA, never blocks cognition).

```bash
python <makewiki_root>/scripts/run_toolkit.py build-site <output_dir> --theme auto
```

### Phase 6: Export & Sync Bundles (Mechanical)

```bash
python <makewiki_root>/scripts/run_toolkit.py export <wiki_dir> --format html|epub|all --lang <code>
python <makewiki_root>/scripts/run_toolkit.py sync-bundle <wiki_dir> --target confluence|notion --lang <code>
```

`export` rejects `--format pdf`. `sync-bundle` only **prepares** bundles on disk; it does NOT publish.

### Phase 7: Delivery Decision & Completion Report

1. Clean up temporary scratch logs.
2. Main Agent evaluates Quality Gate verdict, coverage completeness, and user requirements, deciding final delivery.
3. Present the completion report including:
   - Repository Census traits & subagents deployed (with host-fallback mode)
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
  `delivery.*` (Phase 3 writer page emission), `content_depth.*`
  (Phase 3 writer authoring bounds), `language_profiles.*`, and all
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
- **Dynamic subagent planning**: Main Agent synthesizes scouts and debaters
  dynamically from the Archetype Library within `agent.max_subagents` and
  host `max_parallelism`.
- **ReBattle cross-examination**: Main Agent triggers debate on real conflict;
  mechanical dispute organizer (`rebattle-diff`) is optional.
- **Natural human engineer tone**: ban binary tropes, buzzwords, formulaic
  openings, trailing colons. See `references/anti_ai_cliche.md`.
- **Independent generation per language** from the SemanticModel; no machine
  translation.
- **100% code-block parity** across languages.
- **Ephemeral execution**: clean up temporary artifacts after each phase.
- **Version binding**: skill version (`2.0.0`) ↔ toolkit version (`2.0.0`)
  via the bootstrap script.
