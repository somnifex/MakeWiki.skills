# Task: Parallel Multilingual Writing with Subagent Self-Reflection (多语言自反思撰写)

## Overview

Writing is Phase 3 of MakeWiki. Parallel Language Writer subagents generate native documentation for each target language directly from the unified `SemanticModel`, followed by a mandatory internal self-reflection pass.

---

## 1. Core Principles

1. **Independent Generation, NEVER Machine-Translate**: Each language version is drafted from the `SemanticModel`. Never translate an English output to Chinese or vice versa.
2. **100% Code Block & Config Key Parity**:
   - Commands, flags, options, and code samples must match identically across all languages.
   - Configuration key names, env var keys, and default values must match identically across all languages.
3. **Subagent 4-Dimensional Self-Reflection Pass**:
   - *Grounding*: Check that every command is backed by `SemanticModel`.
   - *Parity*: Ensure no omitted flags or drifted commands compared to the English baseline.
   - *Anti-AI Cliché*: Purge binary tropes ("不是……而是……"), buzzwords ("收敛", "赋能"), and redundant colons.
   - *Tone*: Deliver direct, professional engineer prose.

---

## 2. Diátaxis Document Set Structure

Every language version outputs the following pages into `<output_dir>/`:

- `README.<lang>.md` — Overview, quick links, core capabilities.
- `getting-started.<lang>.md` — 5-minute zero-to-hero tutorial.
- `installation.<lang>.md` — Multi-platform deployment runbook, compatibility matrix, smoke test.
- `configuration.<lang>.md` — Configuration reference matrix (types, defaults, production advice).
- `usage/overview.<lang>.md` — Module map and functional workflow explanation.
- `usage/<slug>.<lang>.md` — Step-by-step how-to operational guides.
- `faq.<lang>.md` — Known limits, common pitfalls.
- `troubleshooting.<lang>.md` — Incident runbook: Error symptom $\rightarrow$ Root cause $\rightarrow$ Fix steps.
- `index.md` — Root multilingual index and navigation map.