# Task: Parallel Multilingual Writing with Subagent Self-Reflection (多语言自反思撰写)

## Overview

Writing is Phase 3 of MakeWiki. Parallel Language Writer subagents generate
native documentation for each target language directly from the unified
`SemanticModel`, followed by a mandatory internal self-reflection pass. The
SemanticModel itself is the LLM's responsibility; Python only contributes
the mechanical identity, command surface, and configuration keys. Where the
LLM leaves a semantic section empty (`faq`, `troubleshooting`,
`usage_examples`, `command_groups`, `user_tasks`, `platform_notes`,
`compatibility_matrix`, `health_checks`, `deployment_notes`), the template
renders an `UNKNOWN` marker — it never invents prose.

---

## 1. Core Principles

1. **Independent Generation, NEVER Machine-Translate**: Each language version is drafted from the `SemanticModel`. Never translate an English output to Chinese or vice versa.
2. **100% Code Block & Config Key Parity (keyed on stable IDs)**:
   - Every technical fenced code block MUST carry a stable block ID marker

     `[[id:<slug>]]` immediately before the fence (or as the first line inside
     the fence body); an untagged technical block is an **L4a failure**. A
     block may be exempted only with an explicit
     `[[parity:ignore reason="..."]]` marker.
   - For multilingual output, every REVIEWABLE H2 MUST carry a stable section

     marker `<!-- makewiki:section=<slug> -->` immediately above it.
     Locate headings can be freely translated / reworded and sections may be
     reordered per language, but the SECTION ID must never change and must be
     present on every reviewable H2.
   - Commands, flags, options, and code samples must match identically across

     all languages for blocks carrying the same stable ID.
   - Configuration key names, env var keys, and default values must match

     identically across all languages.
   - Section ORDER may differ per language (native independent writing); all

     cross-language parity and review is keyed on stable block + section IDs,
     never on heading text or heading position.
   - The Python `parity` command enforces exact block-ID parity; the Auditor

     judges prose parity from `semantic-review` output.
3. **Subagent 4-Dimensional Self-Reflection Pass**:
   - *Grounding*: Check that every command is backed by `SemanticModel`.
   - *Parity*: Ensure no omitted flags or drifted commands compared to the English baseline.
   - *Anti-AI Cliché*: Purge binary tropes ("不是……而是……"), buzzwords ("收敛", "赋能"), and redundant colons.
   - *Tone*: Deliver direct, professional engineer prose.

---

## 2. Diátaxis Document Set Structure

Every language version outputs the following pages into `<output_dir>/`.
Sections whose `SemanticModel` slot is empty render `UNKNOWN`, never
fabricated content.

- `README.<lang>.md` — Overview, quick links, core capabilities.
- `getting-started.<lang>.md` — 5-minute zero-to-hero tutorial.
- `installation.<lang>.md` — Multi-platform deployment runbook, compatibility matrix, smoke test. `verify_command` is `UNKNOWN` unless a Claim proves it.
- `configuration.<lang>.md` — Configuration reference matrix (types, defaults, production advice).
- `usage/overview.<lang>.md` — Module map and functional workflow explanation.
- `usage/<slug>.<lang>.md` — Step-by-step how-to operational guides.
- `faq.<lang>.md` — Known limits, common pitfalls. Empty → `UNKNOWN`.
- `troubleshooting.<lang>.md` — Incident runbook: Error symptom → Root cause → Fix steps. Empty → `UNKNOWN`.
- `index.md` — Root multilingual index and navigation map.