# Task: Parallel Multilingual Writing & Information Architecture (信息架构与多语言原生撰写)

## Overview

Writing is Phase 3 of MakeWiki. The Main Agent synthesizes a bespoke **Information
Architecture (IA)** tailored to the repository and user goals, and dispatches parallel
Language Writer subagents to author native documentation directly from the unified
`SemanticModel`.

Diátaxis serves strictly as a **cognitive rubric** (Tutorials, How-To Guides, Technical Reference, Architecture Explanations) rather than a rigid list of mandatory filenames. The Main Agent owns all IA planning and writer division of labor.

---

## 1. Information Architecture (IA) Owned by Main Agent

The Main Agent evaluates the repository shape, target audience, and project goals to design the document hierarchy:

- **Bespoke Page Synthesis**:
  - Main Agent determines the exact page set, naming, directory nesting, and depth.
  - No mandatory page templates: an API library might output `README.md`, `quickstart.md`, `api/reference.md`, and `architecture.md`, while an enterprise server might require extensive `operations/runbook.md`, `configuration.md`, and `deployment/kubernetes.md`.
- **Diátaxis as a Quality Rubric**:
  - Ensure documentation addresses all four core user needs: Learning-oriented (Tutorials), Task-oriented (How-to), Information-oriented (Reference), and Understanding-oriented (Explanation).
- **Writer Division of Labor**:
  - Main Agent dispatches Writer subagents dynamically by language and/or domain subsystem.

---

## 2. Core Principles of Native Multilingual Writing

1. **Independent Generation, NEVER Machine-Translate**:
   - Each language version is authored independently from the canonical `SemanticModel`.
   - Native technical phrasing, idioms, and natural sentence structures are used for each language (e.g. natural Chinese / Japanese / English engineer prose).
2. **100% Code Block & Config Key Parity (keyed on stable IDs)**:
   - **Stable Block IDs**: Every technical fenced code block MUST carry a stable block ID marker `[[id:<slug>]]` immediately before the fence (or inside the first line of the block). An untagged technical block is an **L4a failure**. Exemption is only granted via `[[parity:ignore reason="..."]]`.
   - **Stable Section Markers**: For multilingual output, every REVIEWABLE H2 section MUST carry a stable section marker `<!-- makewiki:section=<slug> -->` immediately above the heading.
   - **Flexible Section Order**: Section order and heading phrasing may vary per language to optimize reading flow; parity is keyed on stable block and section IDs, never on heading strings or linear positions.
   - **Parameter & Key Consistency**: Commands, arguments, options, config keys, and env vars must match identically across all languages for blocks sharing the same stable ID.
3. **Subagent 4-Dimensional Self-Reflection Pass**:
   - *Grounding*: Check that every command, flag, and configuration key is backed by the `SemanticModel`.
   - *Parity*: Ensure code blocks match character-for-character with the model.
   - *Anti-AI Cliché*: Purge binary tropes ("不是……而是……"), buzzwords ("收敛", "赋能"), and redundant trailing colons.
   - *Tone*: Deliver direct, concise, professional engineer documentation.

---

## 3. Configuration Knobs (LLM-Consumed Knobs)

Each Language Writer reads the following configuration from `makewiki.config.yaml` to guide authoring:

- **`documentation_policy.audience`** and **`documentation_policy.structure_strategy`**:
  - `documentation_policy.audience` is a **seed persona hint** only (e.g. `end-user`, `developer`, `operator`, `dual`). The authoritative audience decision lives in `DocumentationModel.personas` and per-page `PageSpec.audience`; the Writer follows those artifacts, not this coarse string.
  - `structure_strategy` informs high-level structure (`user-journey`, `component-oriented`).
- **`documentation_policy.prefer_task_oriented_sections`**:
  - When true, prioritizes practical how-to workflows over static parameter enumeration.
- **`documentation_policy.include_operator_persona`** (seed switch, default `false`):
  - When true, the Documentation Architect explicitly runs the operator checklist (`tasks/document-model.md` §10) and considers an operator/admin reference. Still evidence-gated: operator docs are produced only where the source supports them.
- **`documentation_policy.include_api_reference`** (seed switch, default `false`):
  - When true, Page Planning explicitly looks for public-API and/or management-API surfaces and, where proven, emits `api_reference` PageSpecs (`tasks/plan-pages.md` §4). No surface, no page, even with the flag on.
- **`language_profiles.<lang>.tone`**:
  - Per-language writer tone override (e.g., concise, formal, detailed).
- **`content_depth.*`**:
  - Guidelines on depth bounds (`max_faq_items`, `max_usage_examples`, `max_troubleshooting_items`, `split_usage_threshold`). Empty sections render `UNKNOWN` rather than invented content.
- **`delivery.*`**:
  - `delivery.audience` is a **delivery-structure bias** (`dual | end-user | enterprise`) only — it does NOT decide general audience (that lives in the artifacts).
  - Dictates inclusion of production deployment runbooks (`include_deployment_runbook`), compatibility matrix (`include_compatibility_matrix`), and health check guides (`include_health_checks`) — each only where **evidence supports it**, never forcing content into a page without source support.