# Task: Repository Orientation & Investigation Planning (代码库快速定位与调查规划)

## Overview

Repository Orientation is the initial cognitive entrypoint of the MakeWiki V3 pipeline.
The **Main Agent (Orchestrator)** directly conducts a rapid, high-information-density survey of the codebase to formulate an initial project hypothesis, identify likely user personas, map major semantic domains, surface critical uncertainties, and synthesize concrete **Investigation Subtasks**.

Orientation does **NOT** attempt exhaustive repository comprehension. Its sole mission is to gather sufficient architectural signal to emit a grounded `RepositoryBrief` and a structured `InvestigationPlan`.

---

## 1. Cognitive vs. Mechanical Boundary

- **Cognitive Authority (LLM / Main Agent)**:
  - Establishes the initial project hypothesis (name, core purpose, software archetype).
  - Identifies preliminary personas and likely user journeys.
  - Deconstructs the system into coherent, domain-driven semantic areas.
  - Distinguishes high-signal entrypoints from peripheral implementation details.
  - Authors the authoritative `RepositoryBrief` and `InvestigationPlan`.
  - Synthesizes modular `SubtaskSpec` definitions for subsequent investigation.
- **Mechanical Plane (Python Toolkit - Optional)**:
  - CLI tools (e.g., `python scripts/run_toolkit.py census .` or `evidence`) serve strictly as **optional supporting evidence** (raw file counts, manifest lists, language breakdowns).
  - Python mechanical output MUST NOT dictate canonical semantic domains, project intent, or documentation structure.

---

## 2. Orientation Protocol (High-Information Sources)

The Main Agent directly inspects the repository using file and search tools (`Glob`, `Grep`, `Read`, `ListDir`), prioritizing high-information-density locations:

1. **Project Manifests & Metadata**: `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `pom.xml`, `CMakeLists.txt`, etc.
2. **Top-Level Readmes & Existing Docs**: `README.md`, `CONTRIBUTING.md`, `docs/`, `mkdocs.yml`, architecture notes. Evaluate their standing (`current`, `possibly_stale`, `unknown`).
3. **Core Entrypoints & Public Interfaces**: CLI definitions, server main functions, route registrations, exported modules, SDK root files.
4. **Configuration Surfaces & Environments**: Default configs, example env files, container definitions (`Dockerfile`, `docker-compose.yml`), CI workflows.
5. **Directory Topology**: Top-level directory tree to understand modularity, monorepo boundaries, or sub-packages.

> **Principle**: Stop reading when high-level structure and primary domains are clear. Do not read every file or trace internal algorithms during this phase.

---

## 3. Deliverable 1: `RepositoryBrief` Contract

The Main Agent synthesizes its orientation findings into a structured `RepositoryBrief` (saved to `.makewiki/repository_brief.yaml` or retained in orchestration state):

```yaml
repository_brief:
  project_hypothesis:
    name: "<project-name>"
    purpose: "<concise statement of core purpose and problem solved>"
    type: "<cli | library | service | full-stack | framework | plugin | monorepo | other>"
    confidence: high | medium | low

  likely_users:
    - persona_hint: "<e.g., end-user | developer | operator | administrator | platform-admin>"
      reason: "<evidence or rationale why this persona exists>"

  major_areas:
    - id: "<domain-slug, e.g., auth | channel-routing | management-api | storage-engine>"
      meaning_hypothesis: "<what this subsystem appears to do>"
      likely_paths:
        - "<path/to/module/>"
      confidence: high | medium | low

  high_information_sources:
    - path: "<path/to/key_file.ext>"
      reason: "<why this file is critical for understanding the architecture>"

  existing_documentation:
    - path_or_url: "<path/to/docs/>"
      standing: current | possibly_stale | unknown

  important_unknowns:
    - "<critical architectural question or ambiguous behavior to be investigated>"

  orientation_notes:
    - "<high-level observations, monorepo nuances, or potential traps>"
```

---

## 4. Deliverable 2: `InvestigationPlan` Contract

Based on the `RepositoryBrief`, the Main Agent designs the `InvestigationPlan`, decomposing the codebase into modular semantic domains and discrete `SubtaskSpec` units:

```yaml
investigation_plan:
  project_hypothesis: "<reiterated or refined hypothesis>"

  domains:
    - id: "<domain-slug>"
      why_important: "<why this domain requires dedicated exploration>"
      goal: "<what the investigation must clarify>"
      scope_hint:
        - "<path/glob/patterns/>"
      related_domains:
        - "<other-domain-id>"

  subtasks:
    - id: "investigate.<domain-slug>"
      type: investigation
      goal: "<clear, bounded goal for the subtask>"
      context:
        repository_brief: ".makewiki/repository_brief.yaml"
      scope_hint:
        - "<path/patterns/>"
      questions:
        - "<specific cognitive question 1>"
        - "<specific cognitive question 2>"
      inputs:
        - "repository_brief"
      expected_output:
        type: ClaimBundle
        id: "claims.<domain-slug>"
      depends_on: []
      stop_conditions:
        - "core capabilities and interfaces of the domain identified"
        - "all assertions backed by concrete file/line evidence"
        - "important uncertainties explicitly recorded"

  coverage_questions:
    - "<high-level question ensuring no major subsystem is omitted>"

  known_uncertainties:
    - "<uncertainty to be resolved during domain investigations>"
```

---

## 5. Subtask Delegation & Execution Protocol

Once the `InvestigationPlan` is established, the Main Agent dispatches the investigation subtasks:

### 5.1 Mandatory Delegation

- When the host environment supports isolated subagents / delegated workers, independent domain investigations **MUST** be delegated to independent child subagents (`Explorer` role).
- The Main Agent **MUST NOT** monopolize all domain investigations in its own context when delegation is supported.

### 5.2 Concurrency & Parallelism

- Independent investigation subtasks (those with `depends_on: []` or satisfied dependencies) should be executed in **parallel** up to the configured `agent.max_parallelism` ceiling.
- Tasks with mutual dependencies must be sequenced accordingly.

### 5.3 Sequential Fallback

- If the host environment does not support subagents or parallelism (solo/single-agent mode):
  - The Main Agent executes the exact same `SubtaskSpec` definitions sequentially.
  - The artifact contracts (`RepositoryBrief`, `SubtaskSpec`, `ClaimBundle`), stage ordering, and semantic boundaries remain 100% identical.

### 5.4 Context Isolation & Delegation Depth

- **Delegation Depth = 1**: The Main Agent dispatches child subagents. Child subagents do not recursively spawn grandchildren. If a subagent identifies a new unexplored area, it records a `recommended_followup` for the Main Agent to evaluate.
- **Context Hygiene**: Pass only the necessary `SubtaskSpec`, `RepositoryBrief`, and specific input references to each subagent. Do NOT forward the entire unstructured chat history or unrelated domain artifacts.

---

## 6. Prohibitions & Strict Boundaries

During the Orientation phase, the Main Agent **MUST NOT**:
1. **Generate the final SemanticModel**: Orientation only formulates hypotheses and planning; synthesis occurs after investigation claim bundles are gathered.
2. **Design the final DocumentationModel or IA**: Do not predetermine final document pages, routes, or site hierarchies.
3. **Write final documentation drafts**: No end-user prose or markdown manual pages may be written.
4. **Trigger ReBattle debate**: ReBattle is an escalation path for hard conflicts during synthesis, not an orientation activity.
5. **Infer semantic facts via rigid AST/regex heuristics**: Do not treat path conventions (e.g. `controllers/ => API`, `admin/ => operator`) as canonical truth without evidence.
6. **Fabricate facts for unproven unknowns**: Mark unclear items as `important_unknowns` or `uncertainty: high/medium` rather than guessing.

---

## 7. Stop Conditions

The Main Agent **MUST STOP** Orientation and proceed immediately to Subtask Dispatch when all of the following conditions are met:

1. **Project Hypothesis Grounded**: The project's core purpose, software archetype, and technology stack are clearly identified with primary source evidence.
2. **Major Domains Identified**: All primary functional and operational domains are mapped to a degree sufficient to frame investigation boundaries.
3. **High-Risk Unknowns Recorded**: Ambiguities, architectural forks, or version discrepancies are noted in `important_unknowns`.
4. **Investigation Subtasks Synthesized**: Concrete, actionable `SubtaskSpec` definitions covering all identified domains are produced.

> **Warning**: Do not over-extend Orientation into deep code auditing. Once the `RepositoryBrief` and `InvestigationPlan` are formed, transition immediately to Phase 2 (Investigation).