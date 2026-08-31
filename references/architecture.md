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
    tool_failure_rule: "Mechanical tool failure -> degraded mechanical verification (pending_mechanical_verification), never cognitive failure; spawn a Recovery Explorer (Explorer-family focus variant) for direct inspection"

  rule_3:
    statement: "Quality Gate is the only cross-plane aggregation point"
    ownership: "mechanical_plane aggregates status, Main Agent decides workflow transitions (ship, revise, recover, accept)"
```

## Authoritative Pipeline (LLM-Orchestrated, Subtask-First)

```yaml
authoritative_pipeline:

  phase_0_orientation:
    cognitive: "Main Agent - Repository Orientation (reads high-information entries, forms an initial hypothesis, identifies personas & major domains)"
    mechanical: "run_toolkit.py census <target>  # OPTIONAL supporting raw traits; never a prerequisite or authority"
    output: "RepositoryBrief + InvestigationPlan (subtask-first)"

  phase_1_investigation:
    cognitive_subagents: "Investigation (Explorer) subtasks - one coherent semantic domain per subtask per the InvestigationPlan; each returns an evidence-backed ClaimBundle"
    mechanical: "run_toolkit.py evidence <target>  # OPTIONAL supporting fact extraction"
    output: "per-domain ClaimBundles"

  phase_2_semantic_synthesis:
    cognitive_subagents: "Semantic Analyst reconciles RepositoryBrief + InvestigationPlan + ClaimBundles into the canonical SemanticModel"
    interaction: "Targeted conflict_resolution subtask, then optional adversarial ReBattle escalation only for genuinely hard disputes (not the default)"
    mechanical_helper: "run_toolkit.py rebattle-diff <claim-files>  # deterministic dispute organizer only; never decides truth"
    output: "adjudicated SemanticModel"

  phase_3_documentation_modeling:
    cognitive_subagents: "Documentation Architect translates SemanticModel (what the software is) into DocumentationModel (who, for which goals: personas, capabilities, journeys, concepts, references, interface references)"
    output: "DocumentationModel"

  phase_4_documentation_planning:
    cognitive_subagents: "Documentation Architect decides what documented intents exist and groups them into pages; emits DocumentationPlan + one PageSpec per page"
    output: "DocumentationPlan + PageSpec[]"

  phase_5_writers:
    cognitive_subagents: "Parallel Language Writer subtasks - each writes exactly one PageSpec x one language directly from its semantic slice (never machine-translated)"
    mechanical_helper: "run_toolkit.py parity <target> --lang ..."
    constraints:
      - "100% code-block (stable [[id:...]] IDs) and section marker parity"
      - "Independent generation from SemanticModel"

  phase_6_review_and_revision:
    cognitive_subagents:
      - "Reviewer (READ-ONLY) - grounding, documentation fitness, audience fit, api_contract, cross-language, epistemic; emits ReviewFindings; does NOT edit pages in place"
      - "Revision Agent - implements ONLY the flagged pages"
      - "Auditor - L3 behavior, L4b prose-parity, L5 epistemic review; emits the SemanticAuditBundle (preserved)"
    mechanical_helper: "run_toolkit.py verify-docs <target> --semantic-audit <file>  # L0-L5 unified run + Quality Gate"
    revision_loop: "A separate Revision Agent implements ReviewFindings; a fresh read-only re-review decides completion (bounded by agent.max_audit_rounds, max 2 rounds per page)"
    anti_cliche: "Anti-cliché prose rewriting is the LLM Writer/Revision Agent's job, never a mechanical rewrite"

  phase_7_integration:
    cognitive_main_agent: "Site Designer / Integrator authors SitePresentationPlan from DocumentationPlan + passed reviewed drafts only; never re-researches the source"
    mechanical:
      - "build-site consumes SitePresentationPlan and renders nav/order/hierarchy/routes verbatim; no plan -> pending/unavailable, never fabricated IA"
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
      strategy: "Run Explorer (investigation subtask) and Writer subagents concurrently within budget"
    sequential:
      when: "supports_subagents AND NOT supports_parallel_subagents"
      strategy: "Run subagents one after another; budget identical, wall-clock linear"
    solo:
      when: "NOT supports_subagents"
      strategy: "Main Agent assumes each role in sequence - Orientation -> Investigation -> Semantic Synthesis -> Documentation Modeling -> Page Planning -> Writing -> Review -> Revision -> Integration -> Verify -> Deliver (no semantics lost, only wall-clock)"

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