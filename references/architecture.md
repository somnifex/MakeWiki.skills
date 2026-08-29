# Architecture: Subagent-First Multi-Agent Collaboration

## Core Philosophy

MakeWiki is designed on a **Subagent-First Cognitive Paradigm**:
- **Cognitive & Analytical Tasks**: Delegated exclusively to autonomous LLM Subagents (Scouts, ReBattle debate team, native Writers, Auditor).
- **Deterministic Plumbing**: Scripts are strictly limited to mechanical operations (HTML SPA bundling, EPUB zip packaging, and payload formatting).

```yaml
system_topology:
  orchestrator:
    agent: "Main Agent (Orchestrator & Chief Adjudicator)"
    responsibilities:
      - Assess project tier (S / M / L) and allocate dynamic subagent budget
      - Dispatch autonomous subagents with standardized role prompts
      - Arbitrate ReBattle cross-examination disputes
      - Compile unified SemanticModel (single source of truth)

  cognitive_phases:
    phase_1_recon:
      subagents: ["Scout-Structure", "Scout-Surface"]
      tools: ["Glob", "Grep", "Read"]
      artifact: "evidence_bundle.json"

    phase_2_rebattle:
      subagents: ["Agent Red (User/DX)", "Agent Blue (Code AST)", "Agent Green (Ops)"]
      interaction: "3-way adversarial cross-examination debate"
      artifact: "semantic_model.json"

    phase_3_writers:
      subagents: ["English Writer", "Chinese Writer", "Other Language Writers"]
      execution: "Parallel native generation directly from SemanticModel"
      artifact: "*.md documentation files"

    phase_4_review:
      subagents: ["Auditor Subagent"]
      responsibilities: ["Code block parity", "Grounding check", "Anti-AI-cliché audit", "In-place self-healing"]

  mechanical_plumbing:
    phase_5_site: "SiteCompiler (run_toolkit.py build-site) -> makewiki/site/index.html"
    export: "DocExporter (run_toolkit.py export) -> Single-file PDF HTML & EPUB"
    sync: "SyncEngine (run_toolkit.py sync) -> Confluence & Notion API bundles"
```

## Subagent Specialization

1. **`Scout-Structure`**: Autonomous inspection of manifests, build targets, Docker, CI/CD, directory tree.
2. **`Scout-Surface`**: Autonomous extraction of CLI flags, REST route endpoints, config templates.
3. **`Agent Red` (User DX)**: User-first workflows, quickstart guides, expected terminal outputs.
4. **`Agent Blue` (Code AST)**: Code-first AST auditing, argument verification, objection formulation.
5. **`Agent Green` (Ops)**: Environment matrix, deployment dependencies, error log runbooks.
6. **`Main Agent / Judge`**: Arbitrates disputes and compiles authoritative `SemanticModel`.
7. **`Language Writers`**: Parallel native authoring directly from `SemanticModel`.
8. **`Auditor`**: Side-by-side cross-language code block parity check, anti-AI-cliché audit, and in-place self-healing.