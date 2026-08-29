# Architecture: Autonomous Self-Reflecting Subagent System

## Core Philosophy

MakeWiki operates on a **Subagent-First Cognitive Paradigm with Embedded Self-Reflection**:
- **Cognitive & Analytical Tasks**: Delegated to autonomous LLM Subagents with internal 4-dimensional self-critique loops.
- **Dynamic Role Synthesis**: The Orchestrator dynamically configures specialized Subagent roles based on repository characteristics (monorepos, FFI bindings, plugin ecosystems).
- **Deterministic Plumbing**: Python scripts are strictly limited to mechanical operations (HTML SPA bundling, EPUB zip packaging, and payload formatting).

```yaml
system_topology:
  orchestrator:
    agent: "Main Agent (Orchestrator & Chief Adjudicator)"
    responsibilities:
      - Dynamic project sizing, role synthesis, and elastic budgeting (capped at 10)
      - Dispatch autonomous subagents with standardized role prompts
      - Arbitrate ReBattle cross-examination disputes
      - Compile unified SemanticModel (single source of truth)

  cognitive_phases:
    phase_1_recon:
      subagents: ["Scout-Structure", "Scout-Surface", "Dynamic Specialized Scouts"]
      tools: ["Glob", "Grep", "Read"]
      reflection: "Self-check file paths and source citations before submission"
      artifact: "evidence_bundle.json"

    phase_2_rebattle:
      subagents: ["Agent Red (User/DX)", "Agent Blue (Code AST)", "Agent Green (Ops)"]
      interaction: "3-way adversarial cross-examination debate with self-reflection & claim retraction"
      artifact: "semantic_model.json"

    phase_3_writers:
      subagents: ["English Writer", "Chinese Writer", "Other Language Writers"]
      execution: "Parallel native generation directly from SemanticModel with anti-cliché self-critique"
      artifact: "*.md documentation files"

    phase_4_review:
      subagents: ["Auditor Subagent"]
      responsibilities: ["Code block parity", "Grounding check", "Anti-AI-cliché audit", "In-place self-healing"]

  mechanical_plumbing:
    phase_5_site: "SiteCompiler (run_toolkit.py build-site) -> makewiki/site/index.html"
    export: "DocExporter (run_toolkit.py export) -> Single-file PDF HTML & EPUB"
    sync: "SyncEngine (run_toolkit.py sync) -> Confluence & Notion API bundles"
```

## Subagent Self-Reflection Invariants

1. **Grounding Invariant**: No undocumented or unreferenced commands allowed.
2. **Parity Invariant**: 100% parameter, key, and code block equivalence across languages.
3. **Anti-Cliché Invariant**: Zero tolerance for "不是……而是……", "不仅……而且……", "收敛", "赋能", and trailing colons in headings.
4. **Adversarial Invariant**: Unprovable claims must be hedged or retracted during ReBattle.