# Task: Parallel Multilingual Writing (多语言独立撰写)

## Overview

Writing is Phase 3 of MakeWiki. Parallel Language Writer subagents generate native documentation for each target language directly from the unified `SemanticModel`.

---

## 1. Core Principles

1. **Independent Generation, NEVER Machine-Translate**: Each language version is drafted from the `SemanticModel`. Never translate an English output to Chinese or vice versa.
2. **100% Code Block & Config Key Parity**:
   - Commands, flags, options, and code samples must match identically across all languages.
   - Configuration key names, env var keys, and default values must match identically across all languages.
3. **Anti-AI-Cliché Technical Prose**:
   - Ban binary antitheses ("不是……而是……", "不仅……而且……").
   - Ban buzzwords ("收敛", "赋能", "对齐", "底层逻辑").
   - Ban redundant colons in headings (`## 步骤 1：安装` $\rightarrow$ `## 步骤 1 安装`).
   - Use direct, active, engineer-to-engineer phrasing.

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