# Task: Autonomous Repo Fact Census & Dynamic Reconnaissance (代码库事实普查与动态勘探)

## Overview

Reconnaissance is Phase 0 & 1 of the MakeWiki pipeline. **Scout Subagents**
autonomously explore the repository structure, code paths, and developer interfaces,
returning structured **Search Ledgers**. The Python toolkit provides the mechanical
counterpart: `census` extracts raw verifiable repository traits (file counts, languages,
manifests, entrypoints, configs, tests, CI/infra, monorepo shape, ecosystems, tool warnings),
and `evidence` (alias `scan`) returns a facts-only JSON bundle.

The boundary is strict: Python measures **facts**; the LLM decides **meaning**.
Python is an auditable evidence channel, never an infallible authority: if Python evidence
conflicts with direct source inspection, the Main Agent investigates directly.

---

## 1. Repository Fact Census & Dynamic Subagent Planning (Phase 0)

In Phase 0, the Main Agent executes `makewiki census .` (or `python run_toolkit.py census .`)
to extract objective repository traits. The Main Agent then evaluates the repository shape
and dynamically synthesizes the Scout topology within configured upper bounds (`agent.max_subagents`, host `max_parallelism`):

- **Lightweight / Single-module Projects**: Consolidated scouts (e.g. Structure + Surface)
- **Standard Multi-component Projects**: Dedicated scouts per domain (Structure, Runtime/CLI, Tests, Config)
- **Complex / Polyglot / Monorepos**: Parallel specialized scouts synthesized dynamically

---

## 2. Dynamic Scout Synthesis & Search Loop (Phase 1)

The Main Agent does not deploy a fixed list of 8 scouts. Instead, it drives an autonomous
**Search Loop** asking:
1. *What do I still not understand about the system?*
2. *What important repository areas are unexplored?*
3. *Which facts are single-source or lack sufficient corroboration?*
4. *Which tool failures need recovery?*
5. *Which claims conflict?*

Scouts are synthesized dynamically based on Census findings and ongoing investigation needs:
- **Structure Scout**: Explores package layouts, build systems, manifests, and monorepo boundaries.
- **Runtime / CLI Scout**: Traces process entrypoints, CLI parsers, subcommands, and flags.
- **Config & Env Scout**: Analyzes configuration schemas, env vars, defaults, and priority overrides.
- **Test & Behavior Scout**: Inspects test fixtures, assertions, and operational behaviors.
- **Deployment / CI Scout**: Analyzes workflows, Dockerfiles, Kubernetes manifests, and cloud deploy steps.
- **Domain Specialists**: Synthesized on-demand (e.g., `FFI Bindings Scout`, `Plugin Ecosystem Scout`, `Fork Provenance Scout`, `Migration Scout`).

---

## 3. Scout Deliverable: Structured Search Ledger

Every Scout directly inspects the codebase using `Glob`, `Grep`, `Read`, and `Bash`
(`ls` / `find` / `git ls-files`) and terminates its investigation by outputting a structured
`<search_ledger>` block:

```markdown
<search_ledger>
# Role: [Synthesized Scout Role Name]
**Confidence:** [0.0 - 1.0]

## Searched Areas
- [Architectural component or module inspected]

## Paths Inspected
- `path/to/inspected_file.py`

## Claims & Evidence
1. **[claim_id]**: [Concrete factual assertion discovered]
   - *Evidence*: `path/to/file.py:L10-L25`
2. **[claim_id]** **[CONFLICT]**: [Assertion that contradicts another source, e.g. README vs code]
   - *Evidence*: `README.md:L5`, `src/config.py:L40`

## Unresolved
- [Unclear behaviors, missing definitions, or ambiguous configurations]

## Unexplored
- [Directories or subsystems observed but left for follow-up inspection]

## Recommended Follow-ups
- [Specific areas or specialized scouts recommended for subsequent exploration]
</search_ledger>
```

---

## 4. Recovery Scout Protocol

When mechanical extraction encounters errors or degraded coverage, the Main Agent
dynamically spawns a **Recovery Scout**:

- **Trigger Conditions**:
  - Mechanical tool throws AST parsing error, syntax error, or unhandled file format.
  - Scanner returns 0 facts or skips a known critical directory.
  - A Scout returns `confidence < 0.7` or flags critical paths in `unresolved`.
  - Conflicting evidence between doc comments and implementation.
- **Recovery Mandate**:
  - Recovery Scout relies exclusively on direct cognitive codebase inspection (`Glob`, `Grep`, `Read`).
  - Directly reads raw source files, extracts ground-truth symbols/schemas/entrypoints, and resolves ambiguities.
  - Emits a definitive Search Ledger to unblock subsequent phases.

---

## 5. Blind Coverage Reviewer Protocol

For complex, large, or polyglot repositories, the Main Agent deploys an independent
**Blind Coverage Reviewer** before moving to ReBattle or Writing:

- **Blind Independence**:
  - The Blind Coverage Reviewer is **NOT** given the Search Ledgers of previous Scouts or any generated drafts.
  - It receives only the raw repository path and Census traits.
- **Objective**:
  - Independently re-explores the codebase to identify hidden entrypoints, forgotten sub-packages, undeclared plugins, config overrides, or missing workflows.
- **Discrepancy Loop**:
  - The Main Agent compares the Blind Reviewer's findings with the existing claims pool.
  - If unexpected core subsystems were missed or placed in `unexplored`, the Main Agent updates its search plan and dispatches targeted scouts before proceeding.