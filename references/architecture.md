# Architecture & Multi-Agent Design

## Overview

MakeWiki orchestrates autonomous subagents with dynamic sizing (Tier S/M/L, capped at 10) and ReBattle competitive verification.

```
                  ┌──────────────────────────────────────────────┐
                  │ Main Agent (Orchestrator & Chief Adjudicator)│
                  │ - Assesses Project Tier (S / M / L)          │
                  │ - Dispatches Subagents & Manages Budget      │
                  │ - Arbitrates ReBattle Conflicts              │
                  │ - Compiles Unified SemanticModel             │
                  └──────────────────────┬───────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
  [Phase 1: Scout]             [Phase 2: ReBattle]             [Phase 3: Writers]
 ├─ Scout-Structure           ├─ Agent Red (User & Dev)        ├─ English Writer
 └─ Scout-Surface             ├─ Agent Blue (Code & AST)       ├─ Chinese Writer
                              ├─ Agent Green (Deploy & Ops)    └─ (Other Lang Writers)
                              └─ [Mechanical Verifier]
                                         │
                                         ▼
                                [Phase 4: Reviewer]
                              ├─ Code Block Parity Auditor
                              ├─ Ground-Truth Verifier
                              └─ Anti-AI-Cliché & Link Auditor
```

## Pipeline Stages

1. `detect_project`: File indicator scoring (Python, Node, Go, Rust, React, Generic).
2. `collect_evidence`: Gathers files, CLI help flags, config comments, routes, exports.
3. `infer_tasks`: Identifies user-facing workflows and goal journeys.
4. `rebattle`: 3-way competitive cross-examination and mechanical adjudication.
5. `generate`: Independent parallel drafting per target language.
6. `validate` & `verify`: Cross-language parity, codebase ground-truth, anti-AI-cliché audit.
7. `build-site`: Single-file offline static SPA wiki compilation.