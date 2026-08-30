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
      - Sizing and source file census (Tier S / M / L)
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
    - Quality Gate is the only cross-plane decision point
```

### Cognitive Authority Boundary

LLM Agents are the authoritative decision makers for semantic work. Python
tooling MUST NOT invent semantic conclusions. When deterministic tooling
cannot mechanically establish a fact, it MUST return UNKNOWN rather than
guess. Python-generated semantic conclusions MUST NOT override LLM Agent
adjudication in the authoritative `/makewiki` path.

**LLM = final judge of truth. Python = final judge of mechanical proof.**

- Python MUST NOT invent semantic conclusions (FAQ, troubleshooting, usage,
  workflows, personas, install steps, verify commands). When Python cannot
  prove something it returns `UNKNOWN` and leaves the slot empty for the LLM
  to fill via the Skill layer.
- LLM MUST NOT bypass Python for steps Python can prove mechanically (file
  existence, CLI flag names, env var keys, code-block parity across languages,
  schema validity). The LLM reads Python's evidence and trusts it; the LLM
  only adds semantic interpretation.
- The Quality Gate is the one place where the two planes meet to produce an
  honest four-state verdict — `passed`, `pending_semantic_review`,
  `pending_mechanical_verification`, or `failed` — mapped to the CI exit
  policy (see Section 3).

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

  phase_0_sizing:
    cognitive: "Main Agent (orchestrator)"
    mechanical: "python run_toolkit.py sizing <target>  # Tier S / M / L"
    output: "tier + subagent budget"

  phase_1_scout:
    cognitive_subagents:
      - "Scout-Structure: manifests, build scripts, CI, top-level layout"
      - "Scout-Surface: CLI entrypoints, flags, routes, .env.example"
      - "Dynamic specialized scouts (FFI, monorepo, plugins, etc.)"
    mechanical: "python run_toolkit.py evidence <target>  # fact extraction"
    output: "evidence_bundle.json + LLM-supplemented semantic observations"

  phase_2_rebattle:
    cognitive_subagents:
      - "Agent Red (User / DX): onboarding, runnable commands, expected output"
      - "Agent Blue (Code AST / Truth): argument parsers, defaults, stubs"
      - "Agent Green (Ops): compatibility, env vars, error runbooks"
    mechanical: "python run_toolkit.py rebattle-diff <claim-files>  # dispute organizer"
    interaction: "3-way adversarial cross-examination with self-retraction"
    output: "adjudicated SemanticModel + LLM-authored ClaimSet"

  phase_3_writers:
    cognitive_subagents: "Per-language native writers (en, zh-CN, ja, ...)"
    mechanical: "python run_toolkit.py parity <target> --lang ...  # exact block parity"
    constraints:
      - "100% code-block and config-key parity across languages"
      - "Independent generation from SemanticModel — never machine-translated"

  phase_4_audit_and_revise:
    cognitive_subagents: "Auditor (LLM) — L3 behavior review, L4 prose parity, L5 over-assertion"
    mechanical: "python run_toolkit.py verify-docs <target>  # L0-L5 unified run"
    revision_loop: "Auditor edits Markdown in place until Quality Gate passes"

  phase_5_site:
    cognitive: "none"
    mechanical:
      - "python run_toolkit.py build-site <wiki_dir>"
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

The Main Agent **dynamically synthesizes subagent roles** within the tier
budget; the synthesis rule reads `agent.max_subagents` and `agent.tier_override`
from `makewiki.config.yaml` (LLM-consumed fields).

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
    action: "Synthesize Agent-Ecosystem focusing on hook registration and SDK interfaces"

elastic_budget_cap:
  hard_limit: 10
  policy: "Tier S (1-2), Tier M (3-5), Tier L (5-10 max)"
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

## 6. Subagent Dispatch Prompts with Embedded Reflection

#### 1. Role-Scoped Scout Prompts

Choose the scouts below per the tier allocation in `tasks/scan.md`
(Tier S: 1~2 consolidated; Tier M: 3; Tier L: up to 8 in parallel). Each scout
**directly inspects the repository** with `Glob` / `Grep` / `Read` /
`Bash` (`ls` / `find` / `git ls-files`) — never only the Python bundle. Run
**two-phase retrieval**: Round 1 Broad Scan (entrypoints, modules, key dirs,
configs, tests, deploy, docs leads), then Round 2 Targeted Deep Dive (trace
symbol definitions, callers, implementations, overrides, defaults, test
evidence, conflicting docs). Seek **two independent evidence sources** per key
fact (e.g. README + the real parser; manifest + the source that reads it).

```markdown
You are the {role} Scout for project '{project_name}'.
Search scope: {role_specific_scope}
Checklist: source, tests, examples, README/docs, manifests, CLI entrypoints,
API/routes, config/env files, Docker/Compose, Makefile/scripts, CI/CD,
deployment, migrations, plugins/extensions, monorepo packages,
generated-code boundaries — report which of these you covered vs. did not.
1. Round 1 Broad Scan: entrypoints, modules, key dirs, configs, tests, deploy, docs leads.
2. Round 2 Targeted Deep Dive: trace each lead to concrete definitions/callers/defaults/overrides.
3. For each key fact, seek at least TWO independent evidence sources and cite both.
Self-Reflection: verify every reported file path actually exists on disk;
surface (do not hide) any conflict between sources (e.g. stale README vs code).
End by listing UNEXPLORED / UNRESOLVED areas (dirs and topics you did not inspect).
Output a structured summary with verified file paths and line citations.
```


#### 3. Agent Red (User & DX Perspective) Prompt
```markdown
You are Agent Red (Developer & User Experience).
1. Formulate the 5-minute quickstart onboarding workflow from git clone to first run.
2. Extract primary CLI commands, required flags, and expected terminal outputs.
3. Map common daily usage scenarios.
Self-Reflection: Challenge your own tutorial — did you assume any implicit prerequisites or omit setup steps?
Label each claim: CONFIRMED_AST, DERIVED_CONFIG, HYPOTHESIS_HEDGED.
```

#### 4. Agent Blue (Code AST & Ground-Truth) Prompt
```markdown
You are Agent Blue (Code Implementation & AST Verifier).
1. Audit commands and flags proposed by Agent Red against actual argument parsers or route tables in source code.
2. Check default values, type constraints, and fallback logic directly in the codebase.
3. Identify unreleased features, stub functions, or deprecated parameters.
Self-Reflection: Ensure every objection you raise is backed by exact file line references.
Output verified implementation facts and explicit objection challenges against ungrounded user claims.
```

#### 5. Agent Green (Enterprise Deployment & Ops) Prompt
```markdown
You are Agent Green (Enterprise Delivery & Operations).
1. Compatibility matrix: Supported OS, runtime versions, database dependencies.
2. Configuration matrix: Environment variables, config files, required vs optional settings, default values, production recommendations.
3. Incident runbook: Error messages found in source code, root causes, log locations, and troubleshooting resolution steps.
Self-Reflection: Check if every error message symptom maps to a verified resolution.
Output deployment runbook facts and operational failure recovery steps.
```

#### 6. Language Writer Subagent Prompt
```markdown
You are the {language_name} Documentation Writer for project '{project_name}'.
Write the complete documentation suite in {language_name} using the unified SemanticModel provided.
Requirements:
1. Independent generation: Write native, high-quality technical {language_name} directly from the SemanticModel — NEVER translate from another language output.
2. Code block parity: All command code blocks, configuration keys, and parameter flags must remain 100% identical across all language versions.
3. Diátaxis structure: README.md, getting-started.md, installation.md, configuration.md, usage/*.md, faq.md, troubleshooting.md, index.md.
4. Self-Reflection: grounding, parity, anti-cliché, tone — natural engineer prose, no binary tropes, no buzzwords, no trailing colons.
Save all generated files under '{output_dir}/'.
```

#### 7. Reviewer & Quality Auditor Subagent Prompt
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

## 7. Subagent Budgeting & Sizing Tiers

The Main Agent automatically assesses project complexity in Phase 0 without
prompting the user.

| Project Tier | Sizing Criteria                              | Subagent Budget           | ReBattle Protocol                | Subagent Allocation                                  |
| :---         | :---                                         | :---                      | :---                             | :---                                                 |
| **Tier S**   | Source files < 15, single entrypoint         | **1 ~ 2 Subagents**       | Prompt-based self-review (0)     | Main Agent (Scout + Judge) + 1~2 Parallel Writers     |
| **Tier M**   | Source files 15 - 80, 5 - 15 commands        | **3 ~ 5 Subagents**       | Red vs Blue (1 debate round)     | 1 Scout + 2 ReBattle (Red, Blue) + 2 Writers         |
| **Tier L**   | Source files > 80, Monorepo / Multi-module   | **5 ~ 10 Subagents (Cap)** | Red + Blue + Green (2 rounds)    | 2 Scouts + 3 ReBattle + Parallel Writers + Reviewer  |

The Tier feeds `agent.tier_override` and `agent.max_subagents`. The Main Agent
honors the user's explicit override; otherwise it falls back to `sizing`.

---

## 8. Documentation Standards (Enterprise Delivery + Diátaxis)

Every generated documentation set must fulfill **two core requirements**:

1. **Developer Rapid Onboarding (Diátaxis Framework)** — Help developers
   understand the project in 5 minutes and perform daily tasks.
2. **Enterprise & Commercial Delivery Standard** — Provide rigorous
   deployment runbooks, compatibility matrices, configuration references, and
   incident recovery guides.

### Diátaxis & Enterprise Structure

See `references/diataxis_matrix.md` for the authoritative page-to-quadrant
mapping. Summary:

| Base Page             | Diátaxis Quadrant | Enterprise Delivery Equivalent | Core Content                                              |
| :---                  | :---              | :---                           | :---                                                      |
| `README.md`           | —                 | Delivery Overview              | One-sentence purpose, key capabilities, quick navigation  |
| `getting-started.md`  | **Tutorial**      | —                              | 5-minute zero-to-hero workflow                            |
| `installation.md`     | Reference         | **Deployment Runbook**         | Multi-platform setup, compatibility matrix, smoke test    |
| `configuration.md`    | **Reference**     | **Configuration Matrix**       | Every config key & env var                               |
| `usage/overview.md`   | **Explanation**   | Capability Map                 | Feature modules, workflow dependencies                    |
| `usage/<module>.md`   | **How-To**        | Operations Manual              | Step-by-step business tasks                               |
| `faq.md`              | —                 | Known Limits                   | Real issues, common pitfalls                              |
| `troubleshooting.md`  | —                 | **Incident Runbook**           | Symptom $\rightarrow$ Root cause $\rightarrow$ Resolution |
| `index.md`            | —                 | Multilingual Portal            | Language switcher + sitemap                               |

### Anti-AI Cliché & Natural Human Voice Rules

See `references/anti_ai_cliche.md`. Highlights:

1. No binary antitheses (`不是……而是……`, `不仅……而且……`).
2. No abstract buzzwords (`收敛`, `对齐`, `赋能`, `闭环`, `底层逻辑`).
3. No formulaic openings (`这是……`, `在本文档中我们将……`).
4. No trailing colons in headings or list items.
5. No unfounded praise (`powerful`, `robust`, `blazing-fast`, `seamless`)
   unless cited from verified benchmark evidence.

### Non-Negotiable Documentation Rules

1. **Independent generation, NEVER machine-translate** — write each language
   from the unified SemanticModel.
2. **Stable Code-Block IDs for Parity** — every technical fenced code block
   MUST carry a stable block ID marker `[[id:<slug>]]` immediately before the
   fence (or as the first line inside the fence body). An untagged technical
   block is an **L4a failure**. A block may be exempted from parity only with
   an explicit `[[parity:ignore reason="..."]]` marker. Parity and revision
   always match blocks by their stable ID — never by position.
3. **Stable H2 Section Markers** — for MULTILINGUAL output, every reviewable
   H2 MUST carry a stable section marker `<!-- makewiki:section=<slug> -->`
   immediately above it. A reviewable H2 with no marker is an **L4a failure**
   (without a stable ID, Python could only guess the cross-language
   correspondence by heading text or position, which is forbidden).
   Single-language output may omit markers. Duplicate section IDs and
   duplicate block IDs within one document are also L4a failures.
4. **Section ORDER may differ per language** — each language is written
   natively and independently, so section order is NOT required to match across
   languages. ALL cross-language parity and review (L4) is keyed on the stable
   block + section IDs, never on heading text or heading position. Two language
   versions may place the same `<slug>` section in different positions; they
   must only agree where they carry the same block/section ID.
5. **Code Block Parity** — 100% identical commands, flags, and config keys
   across all languages, for blocks carrying the same stable ID.
6. **Observable Behavior Only** — describe what users type and see; never
   expose internal source directory tours in user guides.
7. **Strict Hedging** — when evidence is indirect, explicitly hedge
   (*"The repository contains X, suggesting Y may be supported"*).
8. **No Invents-Unknowns** — Python returns `UNKNOWN` for unprovable slots;
   the LLM fills them or leaves them marked.

---

## 9. Seven-Phase LLM-Orchestrated Execution Workflow

### Arguments

Parse `$ARGUMENTS` for:
- `--lang <code>` (repeatable): Target language codes. Default: `en zh-CN`.
- `--output <dir>`: Output directory name. Default: `makewiki`.
- `--theme <auto|light|dark>`: Static site theme. Default: `auto`.

### Phase 0: Autonomous Project Sizing & Dynamic Subagent Synthesis

1. Run `python <makewiki_root>/scripts/run_toolkit.py sizing .` (or honor
   `agent.tier_override` from `makewiki.config.yaml`).
2. Assess Tier (S / M / L) and synthesize subagent roles per the project.

### Phase 1: Autonomous Codebase Reconnaissance

Launch the tier-scaled set of role-scoped Scouts (see `tasks/scan.md` §2):
- **Tier S**: 1~2 consolidated scouts (Structure + Surface).
- **Tier M**: 3 scouts (Structure; Runtime/Entrypoint + CLI/API + Config
  consolidated; Tests/Behavior).
- **Tier L**: up to 8 in parallel — Structure, Runtime/Entrypoint,
  CLI/API, Config, Tests/Behavior, Deployment/CI, Docs/Examples,
  Dependency/Monorepo.

Each scout **directly inspects the repository** with `Glob` / `Grep` /
`Read` / `Bash` (`ls` / `find` / `git ls-files`) — never only the Python
bundle — using two-phase retrieval (Round 1 Broad Scan, Round 2 Targeted
Deep Dive) and seeking two independent evidence sources per key fact.

After scouts return, run:
`python <makewiki_root>/scripts/run_toolkit.py evidence .` (deterministic
fact bundle) and `python <makewiki_root>/scripts/run_toolkit.py coverage .`
(mechanical coverage: discovered vs inspected vs skipped vs ignored,
uncovered categories, low-confidence facts). Scouts augment facts with
semantic observations; Python never invents them.

### Phase 1.5: Coverage Gate (before Judge)

1. Reconcile every scout's `unexplored` / `unresolved` areas against the
   `coverage` report's `uncovered_categories` and `low_confidence_facts`.
2. For each entry, **resolve it** (dispatch a targeted deep-dive) or
   **explicitly accept it** with a written reason.
3. **If still-unchecked important directories or categories remain, do NOT
   enter the Judge stage** — the gaps must be closed or consciously accepted
   first.

### Phase 2: ReBattle Adversarial Cross-Examination & Adjudication

The ReBattle runs `agent.rebattle_rounds` cross-examination rounds (default
2). Each season the adversarial agents re-derive the *stable* SemanticModel
and ClaimSet before writing — it is the LLM-owned provenance step that guards
the Mechanical Facts.

#### Blind extraction with self-reflection (Round 1)
- **Agent Red** extracts runnable CLI commands, onboarding paths, expected
  outputs.
- **Agent Blue** inspects source functions, exports, handlers, stub warnings.
- **Agent Green** extracts compatibility matrices, env vars, health checks,
  error runbooks.

#### Cross-examination & debate (Round 2)
Subagents challenge each other's claims using AST evidence.

#### Adjudication & unified Semantic Model (Round 3)
The Main Agent acts as Judge, compiles the authoritative `SemanticModel` and
the LLM-authored ClaimSet. Optional mechanical helper:
`python <makewiki_root>/scripts/run_toolkit.py rebattle-diff <claim-files>`
produces a deterministic dispute matrix.

### Phase 3: Parallel Multilingual Writers

For each target language spawn an independent Language Writer Subagent. Each
writer:
- receives the same adjudicated SemanticModel and ClaimSet,
- writes the complete native Markdown set into `<output_dir>/`,
- honors `content_depth.*` bounds (``max_faq_items`` / ``max_usage_examples`` /
  ``max_troubleshooting_items`` / ``mode``) when deciding how much FAQ, usage
  example, and troubleshooting material to author per page,
- emits the delivery pages (deployment runbook / compatibility matrix /
  health checks on the installation page) only when `delivery.*` enables them,
- runs the 4-dimensional self-reflection loop,
- honors 100% code-block parity across languages.

After writers return, run `python <makewiki_root>/scripts/run_toolkit.py parity <target> --lang ...`
to extract exact block parity checks (L4 mechanical half). The Auditor reasons
over any deltas.

### Phase 4: Adversarial Audit, Quality Gate & Autonomous Self-Healing

1. Run `python <makewiki_root>/scripts/run_toolkit.py verify-docs <target>` —
   this drives the `VerificationOrchestrator` across L0 - L5 and feeds the
   `QualityGateResult` back to the Skill layer.
2. The Auditor Subagent reads the Quality Gate output:
   - Resolves failed mechanical layers (L0 / L1 / L2 / L4a) by editing
     the Markdown in place.
   - Resolves pending LLM-judged layers (L3 / L4b / L5) by reasoning
     over the evidence list Python provided, and **emits a machine-readable
     `SemanticAuditBundle`** JSON with each semantic verdict (see Section 3A).
3. Re-run `verify-docs` — now with `--semantic-audit <file>` (and
   `--semantic-model <file>` when the bundle declares a `semantic_model_digest`)
   to consume the Auditor's bundle — until the gate is `passed` or `failed`
   or until `agent.max_audit_rounds` is exhausted. Pending LLM layers exit 0 when
   `quality.allow_pending_llm_layers` is true:
   ```bash
   python <makewiki_root>/scripts/run_toolkit.py verify-docs <target> --semantic-audit <output_dir>/semantic_audit.json --semantic-model <output_dir>/semantic_model.json
   ```
   The bundle must be emitted after all in-place edits so its `documents_digest`
   matches the final markdown set; a stale bundle (digest mismatch) is rejected
   and the affected semantic layers stay `pending` until a fresh audit.
   Human output renders the Quality Gate verdict as an honest four-state result
   and breaks the checks into separate sections — **Failed Checks**, **Pending
   Semantic Reviews**, **Unknown / Insufficient Evidence**, **Warnings** — so
   pending / unknown items are never shown as "Failed".

### Phase 5: Offline Static Site Compilation (Mechanical)

```bash
python <makewiki_root>/scripts/run_toolkit.py build-site <output_dir> --theme auto
```

Generates `<output_dir>/site/index.html`: multilingual switcher, light / dark
toggle, client-side full-text search, 1-click code copy.

### Phase 6: Export & Knowledge-Base Bundle (Mechanical)

```bash
python <makewiki_root>/scripts/run_toolkit.py export <wiki_dir> --format html|epub|all --lang <code>
python <makewiki_root>/scripts/run_toolkit.py sync-bundle <wiki_dir> --target confluence|notion --lang <code>
```

`export` rejects `--format pdf`. `sync-bundle` only **prepares** bundles on
disk; it does NOT publish.

### Phase 7: Ephemeral Cleanup & Final Report

1. Clean up temporary scratch logs.
2. Present the completion report including:
   - Project Tier & subagents deployed (with host-fallback mode)
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
| `sizing`                 | —            | Tier (S / M / L) + subagent budget                           |
| `evidence`               | `scan`       | Emit deterministic evidence facts (JSON / human)             |
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
| `legacy-generate`        | `generate`   | Mechanical scaffold only (deprecated) — **NOT** the authoritative flow |

Backward-compat aliases (`scan`, `verify`, `sync`, `generate`) remain so
existing scripts keep working. `generate` is the deprecated alias of
`legacy-generate` (the non-authoritative mechanical scaffold). The
authoritative flow is `/makewiki`. `review` is a standalone command, not an
alias of `parity`.

### Config Consumption Contract

Every field in `makewiki.config.yaml` maps to exactly one consumer category —
Python-only, LLM-only, Shared, or Legacy-only. The contract test
`tests/contracts/test_config_consumption_contract.py` enforces that no field is
dead or ambiguous:

- **Shared** (read by Python for mechanical enforcement AND by the LLM writer
  as guidance): `documentation_policy.forbid_unfounded_praise` and
  `documentation_policy.banned_descriptors`. Python reads them in
  `renderer/validator.py` to enforce the no-unfounded-praise / no-banned-word
  rule mechanically; the writer also consults them so it never produces such
  descriptors in the first place.
- **LLM-only**: `agent.*` (incl. `max_audit_rounds`, the authoritative
  Auditor-loop budget in Phase 4, and `rebattle_rounds`, the ReBattle budget in
  Phase 2), `delivery.*` (Phase 3 writer page emission), `content_depth.*`
  (Phase 3 writer authoring bounds), `language_profiles.*`, and the other
  `documentation_policy.*` fields (`audience`, `structure_strategy`,
  `prefer_task_oriented_sections`, `include_architecture_analysis`,
  `include_directory_overview`, `include_source_walkthroughs`) — read by Skill
  / writers, NOT by Python. The contract's behavioral test asserts each
  LLM-only field is actually referenced in the authoritative Skill layer
  (`SKILL.md` / `tasks/`), and its negative test asserts no LLM-only field has
  a Python read.
- **Python-only**: `scan.*`, `review.*` (incl. the mechanical
  `enable_review_pair_generation`, which only gates the `semantic-review`
  preparation command — it never closes the authoritative LLM semantic audit),
  `site.*`, `quality.*`, `output_dir`, `languages`, `default_language`,
  `target_dir`. These are the fields the authoritative mechanical CLI actually
  reads (`verify-docs`, `parity`, `review`, `build-site`).
- **Legacy-only**: `emit_uncertainty_notes`, `generate_*`, `strict_grounding`,
  `overwrite`, `delete_stale_files`, and the whole `revision.*` block. The
  legacy revision round budget never bounds the authoritative `/makewiki`
  Auditor loop — that is `agent.max_audit_rounds`. These SEMANTIC scaffolding
  decisions (whether to emit faq/troubleshooting/env-vars
  pages, whether to attach uncertainty hedges, revision rounds) are consumed
  ONLY by the deprecated `legacy-generate` / `generate` scaffold — the legacy
  deterministic renderer, the legacy pipeline, and its mechanical repair
  loop. They are never treated as authoritative Python "mechanical
  enforcement": in the authoritative `/makewiki` flow the LLM Auditor edits
  Markdown in place and the LLM writers decide page composition and hedging.

See `tests/contracts/test_config_consumption_contract.py`.

---

## 11. Working Notes

- **Autonomous execution**: Complete all phases end-to-end without pausing
  for intermediate confirmation.
- **Subagent budget**: Tier S (1-2), Tier M (3-5), Tier L (5-10 max).
- **ReBattle cross-examination** before writing; mechanical dispute organizer
  (`rebattle-diff`) is optional.
- **Natural human engineer tone**: ban binary tropes, buzzwords, formulaic
  openings, trailing colons. See `references/anti_ai_cliche.md`.
- **Independent generation per language** from the SemanticModel; no machine
  translation.
- **100% code-block parity** across languages.
- **Ephemeral execution**: clean up temporary artifacts after each phase.
- **Version binding**: skill version (`2.0.0`) ↔ toolkit version (`2.0.0`)
  via the bootstrap script.
