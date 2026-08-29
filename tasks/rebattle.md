# Task: ReBattle Competitive Verification (对抗审查与仲裁)

## Overview

ReBattle is Phase 2 of MakeWiki. It utilizes 3 independent perspectives (Red, Blue, Green) to debate and cross-examine facts, eliminating single-agent hallucinations before any documentation is drafted.

---

## 1. The Three Battle Roles

```
        ┌───────────────────────────────────────────────────────────┐
        │                  Adjudicator (Main Agent)                 │
        │                  Arbitrates & Compiles                    │
        └─────────────────────────────┬─────────────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
      ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
      │  Agent Red   │◄──────►│  Agent Blue  │◄──────►│ Agent Green  │
      │  (User & DX) │        │ (Source AST) │        │(Deploy & Ops)│
      └──────────────┘        └──────────────┘        └──────────────┘
```

1. **Agent Red (User & DX Perspective)**:
   - Primary Focus: 5-minute onboarding tutorial, runnable commands, CLI arguments, expected terminal output.
   - Generates: `claims_red.json`
2. **Agent Blue (Source AST & Ground-Truth)**:
   - Primary Focus: AST functions, argument parser schemas, actual default values, stub / deprecated code warnings.
   - Generates: `claims_blue.json`
3. **Agent Green (Enterprise Deployment & Ops)**:
   - Primary Focus: Runtime dependencies, OS compatibility, port mappings, environment variable matrix, error codes and logs.
   - Generates: `claims_green.json`

---

## 2. Cross-Examination & Adjudication Protocol

1. **Round 1 (Blind Extraction)**: Red, Blue, Green extract facts independently without seeing each other's claims.
2. **Round 2 (Cross-Challenge)**:
   - Blue verifies if Red's commands exist in code AST.
   - Green verifies if Red's quickstart has missing mandatory environment variables.
   - Red verifies if Blue's internal functions are exposed to the CLI.
3. **Round 3 (Judge Adjudication)**:
   - The Main Agent mechanically verifies disputed claims with the codebase verifier.
   - Discards invalid/unsupported claims.
   - Compiles the final **`SemanticModel`**.

---

## 3. Toolkit Execution Command

```bash
# Verify proposed claims against target codebase
python scripts/run_toolkit.py verify <target_path> --format json
```