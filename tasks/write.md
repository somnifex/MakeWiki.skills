# Task: Multilingual Page Writing (多语言页面撰写)


## Overview

Writing is Phase 6 of the V3 pipeline. Each **Language Writer** subagent authors
**exactly one `PageSpec` × one `language`** directly from its semantic slice —
the relevant portion of the `DocumentationModel` / `SemanticModel` the `PageSpec`
covers. Writers never machine-translate and never design the global IA.

**IA is not the Writer's job.** The authoritative page set, grouping, nesting, and
per-page intent come from the **Documentation Architect** via the
`DocumentationPlan` and each `PageSpec` (see `tasks/plan-pages.md`, `tasks/document-model.md`).
The **Main Agent orchestrates** writer dispatch within `agent.max_subagents` and host
`max_parallelism`; it does **not** directly invent the page hierarchy (SKILL §8).

Diátaxis serves strictly as a **cognitive rubric** (Tutorials, How-To Guides,
Technical Reference, Architecture Explanations) rather than a rigid list of mandatory
filenames — the `PageSpec`s already encode the page intent.

---

## 1. One `PageSpec` × One Language

- **Unit of work**: exactly one `PageSpec` × one language per Writer.
- **Source of truth**: the `PageSpec`'s `covers`, `required_sections`, and the
  underlying semantic slice (`DocumentationModel`/`SemanticModel`). The Writer
  follows the artifacts, not coarse config strings.
- **No machine translation**: each language is authored independently and natively.
- **No IA invention**: the Writer does not split, merge, or re-parent pages; it
  writes the page the `PageSpec` describes.

---

## 2. Core Principles of Native Multilingual Writing

1. **Independent Generation, NEVER Machine-Translate**:
   - Each language version is authored independently from the page's semantic slice.
   - Native technical phrasing, idioms, and natural sentence structures are used for
     each language (e.g. natural Chinese / Japanese / English engineer prose).
2. **100% Code Block & Config Key Parity (keyed on stable IDs)**:
   - **Stable Block IDs**: Every technical fenced code block MUST carry a stable block
     ID marker `[[id:<slug>]]` immediately before the fence (or inside the first line
     of the block). An untagged technical block is an **L4a failure**. Exemption is only
     granted via `[[parity:ignore reason="..."]]`.
   - **Stable Section Markers**: For multilingual output, every REVIEWABLE H2 section
     MUST carry a stable section marker `<!-- makewiki:section=<slug> -->` immediately
     above the heading.
   - **Flexible Section Order**: Section order and heading phrasing may vary per
     language to optimize reading flow; parity is keyed on stable block and section IDs,
     never on heading strings or linear positions.
   - **Parameter & Key Consistency**: Commands, arguments, options, config keys, and env
     vars must match identically across all languages for blocks sharing the same stable
     ID.
3. **Subagent 4-Dimensional Self-Reflection Pass**:
   - *Grounding*: Check that every command, flag, and configuration key is backed by the
     evidence/`SemanticModel`.
   - *Parity*: Ensure code blocks match character-for-character across languages.
   - *Anti-AI Cliché*: Purge binary tropes ("不是……而是……"), buzzwords ("收敛", "赋能"),
     and redundant trailing colons. See `references/anti_ai_cliche.md`.
   - *Tone*: Deliver direct, concise, professional engineer documentation.

---

## 3. Configuration Knobs (LLM-Consumed Knobs)

Each Language Writer reads the following configuration from `makewiki.config.yaml`
to guide authoring:

- **`documentation_policy.audience`** and **`documentation_policy.structure_strategy`**:
  - `documentation_policy.audience` is a **seed persona hint** only (e.g. `end-user`,
    `developer`, `operator`, `dual`). The authoritative audience decision lives in
    `DocumentationModel.personas` and per-page `PageSpec.audience`; the Writer follows
    those artifacts, not this coarse string.
  - `structure_strategy` informs high-level structure (`user-journey`, `component-oriented`).
- **`documentation_policy.prefer_task_oriented_sections`**:
  - When true, prioritizes practical how-to workflows over static parameter enumeration.
- **`documentation_policy.include_operator_persona`** (seed switch, default `false`):
  - When true, the Documentation Architect explicitly runs the operator checklist
    (`tasks/document-model.md` §10) and considers an operator/admin reference. Still
    evidence-gated: operator docs are produced only where the source supports them.
- **`documentation_policy.include_api_reference`** (seed switch, default `false`):
  - When true, Page Planning explicitly looks for public-API and/or management-API
    surfaces and, where proven, emits `api_reference` PageSpecs (`tasks/plan-pages.md` §4).
    No surface, no page, even with the flag on.
- **`language_profiles.<lang>.tone`**:
  - Per-language writer tone override (e.g., concise, formal, detailed).
- **`content_depth.*`**:
  - Guidelines on depth bounds (`max_faq_items`, `max_usage_examples`,
    `max_troubleshooting_items`, `split_usage_threshold`). Empty sections render
    `UNKNOWN` rather than invented content.
- **`delivery.*`**:
  - `delivery.audience` is a **delivery-structure bias** (`dual | end-user | enterprise`)
    only — it does NOT decide general audience (that lives in the artifacts).
  - Dictates inclusion of production deployment runbooks (`include_deployment_runbook`),
    compatibility matrix (`include_compatibility_matrix`), and health check guides
    (`include_health_checks`) — each only where **evidence supports it**, never forcing
    content into a page without source support.

---

## 4. Prohibitions & Strict Boundaries

During a writing subtask the Writer **MUST NOT**:
1. **Design the global IA** — no final page set, routes, or site hierarchy; the
   `PageSpec`/`DocumentationPlan` already decide page intent and nesting.
2. **Split or merge pages** — the Writer authors the page the `PageSpec` describes.
3. **Machine-translate** — each language is authored natively from its semantic slice.
4. **Invent facts** — unproven fields stay `UNKNOWN` / omitted; never pad from
   plausible-but-unverified content.
5. **Modify other pages or the semantic model** — the Writer only writes its assigned
   page (`page_id`) in its assigned language (from the shared language-neutral `PageSpec`).

---

## 5. Stop Conditions

The Writer **MUST STOP** when:
1. Its assigned page (`page_id`) in its assigned language is complete and coherent.
2. Every technical block and reviewable section carries a stable `[[id:...]]` /
   `<!-- makewiki:section=... -->` marker.
3. No IA was invented, no pages were split/merged, and no unproven content was added.
4. The page is written natively (not translated) from its semantic slice.

Terminate with a single explicit status (`completed`, `blocked`, or `needs_followup`)
and report the `artifact produced` (the page), `uncertainties`, and any points escalated
to the Reviewer.
