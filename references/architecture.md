# Architecture: LLM-First, Evidence-Backed, Multi-Agent Documentation Compiler

## Core Philosophy

MakeWiki runs on **two strict planes** separated by a hard boundary:

- **Cognitive Plane** (LLM / Skill layer) decides what the repository means.
- **Mechanical Plane** (Python toolkit) proves what can be mechanically

  proven.

The Quality Gate is the single place where the two planes meet to produce an
honest four-state decision (`passed` / `pending_semantic_review` /
`pending_mechanical_verification` / `failed`). Everything else is strict
ownership.

```yaml
two_plane_architecture:

  cognitive_plane:
    owner: "LLM (Skill + Subagents)"
    decisions:
      - "What the project does and who it serves"
      - "FAQ, troubleshooting, usage examples, workflows, personas"
      - "Diátaxis structure, narrative voice, hedging language"
      - "ReBattle adjudication and Quality Gate remediation"
    disallowed_at_runtime:
      - "Inventing content based on regex heuristics"
      - "Filling semantic gaps with default prose"
      - "Re-doing mechanical proof Python already produced"

  mechanical_plane:
    owner: "Python toolkit"
    responsibilities:
      - "Repository fact census (traits, file counts, languages, manifests, entrypoints)"
      - "Evidence extraction (commands, configs, paths, versions, env vars)"
      - "AST / CLI / config / manifest parsing"
      - "L0 syntax, L1 existence, L2 interface, L4 exact-block parity"
      - "Schema validation (SemanticModel, ClaimSet, EvidenceBundle)"
      - "Static site, export, sync-bundle, validate"
      - "Quality Gate aggregation and CI exit code"
    disallowed_at_runtime:
      - "Returning any narrative content the LLM should produce"
      - "Guessing when a check is unprovable (returns UNKNOWN instead)"

  bridge:
    - "Skill calls Python only for mechanical proof steps"
    - "Python returns structured facts, never interpretations"
    - "Quality Gate aggregates layer statuses; Main Agent decides workflow progression"
```

## Cognitive Authority Boundary

LLM Agents are the authoritative decision makers for semantic work. Python
tooling MUST NOT invent semantic conclusions. When deterministic tooling
cannot mechanically establish a fact, it MUST return UNKNOWN rather than
guess. Python-generated semantic conclusions MUST NOT override LLM Agent
adjudication in the authoritative `/makewiki` path.

Main Agent LLM is the sole runtime orchestrator. Python is an auditable
evidence channel, not an infallible authority.

```yaml
cognitive_authority_boundary:

  rule_1:
    statement: "Python MUST NOT invent semantic conclusions"
    examples_forbidden:
      - "Synthesized FAQ answers without LLM-authored content"
      - "Default install steps with no source confirmation"
      - "Heuristic-generated troubleshooting causality"
      - "Regex-derived workflows or task inference"
    fallback: "Return UNKNOWN; emit an explicit UNKNOWN marker in the scaffold"

  rule_2:
    statement: "Python is an auditable evidence channel, not an infallible authority"
    clarification: "If Python evidence conflicts with direct source inspection, the Main Agent must investigate directly via Glob/Grep/Read"
    tool_failure_rule: "Mechanical tool failure -> degraded mechanical verification (pending_mechanical_verification), never cognitive failure; spawn Recovery Scout"

  rule_3:
    statement: "Quality Gate is the only cross-plane aggregation point"
    ownership: "mechanical_plane aggregates status, Main Agent decides workflow transitions (ship, revise, recover, accept)"
```

## Authoritative Pipeline (LLM-Orchestrated)

```yaml
authoritative_pipeline:

  phase_0_census:
    cognitive: "Main Agent (orchestrator: dynamic topology & subagent planning)"
    mechanical: "run_toolkit.py census <target>  # raw repository facts"
    output: "Repository Fact Census + dynamic subagent topology plan"

  phase_1_scout:
    cognitive_subagents:
      - "Dynamic scouts synthesized from Archetype Library (Structure, Runtime, CLI, Config, Tests, Deploy, Docs, Deps)"
      - "Recovery Scout dispatched on tool failure or degraded output"
      - "Dynamic specialized scouts (Fork Scout, Plugin Scout, ABI/FFI Scout)"
    mechanical: "run_toolkit.py evidence <target>  # fact extraction only"
    output: "evidence_bundle.json + LLM semantic observations"

  phase_2_rebattle:
    cognitive_subagents: "Targeted debater archetypes (DX, AST Truth, Ops) focusing on disputed semantic_keys"
    mechanical_helper: "run_toolkit.py rebattle-diff <claim-files>"
    interaction: "0-round fast path on consensus; dynamic convergence bounded by safety_max_rounds"
    output: "adjudicated SemanticModel + LLM-authored ClaimSet"

  phase_3_writers:
    cognitive_subagents: "Per-language native writers (en, zh-CN, ja, ...)"
    mechanical_helper: "run_toolkit.py parity <target> --lang ..."
    constraints:
      - "100% code-block and config-key parity"
      - "Independent generation from SemanticModel"

  phase_4_audit_and_revise:
    cognitive_subagents: "Auditor (LLM) — L3, L4-prose, L5"
    mechanical_helper: "run_toolkit.py verify-docs <target>"
    revision_loop: "Auditor edits Markdown in place until Quality Gate passes (bounded by agent.max_audit_rounds)"
    anti_cliche: "Anti-cliché prose rewriting is the LLM Auditor's job, never a mechanical rewrite"

  phase_5_site:
    cognitive: "none"
    mechanical:
      - "run_toolkit.py build-site <wiki_dir>"
      - "run_toolkit.py export <wiki_dir> --format html|epub|all  # pdf rejected"
      - "run_toolkit.py sync-bundle <wiki_dir> --target confluence|notion  # bundle-prep only"
```

## Host Capability Fallback

```yaml
host_capability_fallback:

  capabilities:
    - "supports_subagents: bool"
    - "supports_parallel_subagents: bool"
    - "max_parallelism: int"
    - "supports_file_write: bool"
    - "supports_web: bool"

  modes:
    parallel:
      when: "supports_subagents AND supports_parallel_subagents"
      strategy: "Run scout and writer subagents concurrently within budget"
    sequential:
      when: "supports_subagents AND NOT supports_parallel_subagents"
      strategy: "Run subagents one after another; budget identical, wall-clock linear"
    solo:
      when: "NOT supports_subagents"
      strategy: "Main Agent assumes Census/Scout -> Discrepancy Evaluation -> (Optional Debate) -> Judge Synthesis -> per-language writers -> Auditor sequentially"

  invariant: "No MakeWiki semantics are lost on fallback; only wall-clock changes."
```

## Quality Gate

```yaml
quality_gate:
  verdict_source: "evaluate_quality_gate(report, cfg) -> QualityGateResult"
  fields:
    passed: bool                    # strictly (verdict == "passed"); a pending gate is never passed
    verdict: "passed | pending_semantic_review | pending_mechanical_verification | failed"
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
  ci_exit_code: "passed -> 0, failed -> 1, pending_semantic_review -> 0 (when quality.allow_pending_llm_layers) else 2, pending_mechanical_verification -> 3"
  config:
    quality.min_grounding_score: 1.0  # sole Quality Gate grounding threshold
    quality.allow_pending_llm_layers: true  # EXIT POLICY ONLY; never changes the truth verdict
  layer_ownership:
    mechanical: ["L0", "L1", "L2", "L4-exact"]
    llm_judged: ["L3", "L4-prose", "L5"]
    rule: "pending means 'evidence available, judgment still owed'; never silently hidden"
```

## Mechanical UNKNOWN, Never Guess

```yaml
mechanical_unknown_contract:

  rule: "When Python cannot mechanically prove a slot, leave it empty and emit an UNKNOWN marker"

  examples:
    installation.verify_command:
      proven: "from Makefile, pyproject, or README smoke test"
      unproven: "emit UNKNOWN; do not invent 'make test' or similar"
    installation.steps:
      proven: "extracted from build scripts (Makefile / package.json scripts / pyproject)"
      unproven: "do not inject canned 'clone the repository' or default install steps"
    faq / troubleshooting / usage_examples:
      proven: "LLM-authored through ClaimSet"
      unproven: "do not synthesize via regex heuristics"
    user_tasks / command_groups:
      proven: "LLM-authored from adjudicated SemanticModel"
      unproven: "do not synthesize via TaskInferenceEngine or similar heuristics"

  scaffold_output:
    contains_only: "What Python can prove + UNKNOWN markers for the rest"
    never_contains: "Invented FAQ / troubleshooting / usage / install defaults"
```

## Subagent Self-Reflection Invariants

1. **Grounding Invariant**: No undocumented or unreferenced commands allowed.
2. **Parity Invariant**: 100% parameter, key, and code-block equivalence across languages.
3. **Anti-Cliché Invariant**: Zero tolerance for `不是……而是……`, `不仅……而且……`,

   `收敛`, `赋能`, and trailing colons in headings.
4. **Adversarial Invariant**: Unprovable claims must be hedged or retracted during ReBattle.

## Topological Comparison: Before vs After

```yaml
architecture_before:
  python_path: "extract -> heuristic builders (FAQ / troubleshooting / usage / command-groups) -> TaskInferenceEngine regex -> Jinja2 full Markdown"
  skill_path: "Sizing -> Scout -> ReBattle -> Writers -> Review -> Site"
  problem: "Split-brain: code path the docs never mention; Python owns cognitive decisions via regex / keyword heuristics"

architecture_after:
  python_role: "Mechanical proof + scaffolding with UNKNOWN markers"
  skill_role: "Authoritative orchestrator over LLM cognitive plane"
  bridge: "Quality Gate aggregates layer results into an honest four-state verdict (passed / pending_semantic_review / pending_mechanical_verification / failed)"
  rule: "Python proves what can be mechanically proven; LLM decides what the repository means"
```