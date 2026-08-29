# Task: ReBattle Competitive Verification (多 Subagent 对抗审查与辩论仲裁)

## Overview

ReBattle is Phase 2 of MakeWiki. It utilizes **autonomous Subagents representing 3 distinct cognitive perspectives (Red, Blue, Green)** to engage in an adversarial cross-examination debate, eliminating single-agent bias and hallucinations before documentation is generated.

---

## 1. The Three Battle Subagents

```yaml
rebattle_topology:
  adjudicator:
    agent: "Main Agent (Chief Judge)"
    duty: "Dispatches subagents, cross-routes claims, arbitrates disputes, builds SemanticModel"

  debating_subagents:
    agent_red:
      perspective: "User & Developer Experience (DX)"
      focus: "5-minute onboarding tutorial, runnable commands, CLI arguments, expected output"
      output: "claims_red.json"

    agent_blue:
      perspective: "Source AST & Implementation Truth"
      focus: "AST functions, argument parser schemas, default constants, stub warnings"
      output: "claims_blue.json"

    agent_green:
      perspective: "Enterprise Deployment & Operations"
      focus: "Runtime compatibility, env vars matrix, port bindings, error runbooks"
      output: "claims_green.json"
```

1. **Agent Red (User & Developer Experience Subagent)**:
   - Primary Focus: 5-minute onboarding tutorial, runnable commands, CLI arguments, expected terminal output.
   - Output: `claims_red.json` (Runnable commands and user workflows with confidence scores).
2. **Agent Blue (Source AST & Implementation Subagent)**:
   - Primary Focus: Source code AST, actual argument parser schemas, default fallback logic, stub / unreleased code warnings.
   - Output: `claims_blue.json` (Ground-truth implementation facts and objection challenges against fake/unsupported flags).
3. **Agent Green (Enterprise Deployment & Ops Subagent)**:
   - Primary Focus: Runtime dependencies, OS compatibility, port mappings, environment variable matrix, error codes and logs.
   - Output: `claims_green.json` (Ops runbook facts and failure recovery procedures).

---

## 2. Multi-Agent Cross-Examination Debate Protocol

1. **Round 1 (Blind Independent Extraction)**:
   - Red, Blue, Green Subagents explore the codebase simultaneously and produce independent claim sets.
2. **Round 2 (Adversarial Challenge & Cross-Examination)**:
   - Agent Blue inspects Agent Red's claims against AST definitions:
     - *"Objection: `--fast` flag proposed by Agent Red does not exist in cli.py parser; flag is invalid."*
   - Agent Green audits Agent Red's quickstart tutorial:
     - *"Objection: Quickstart tutorial omits mandatory `DB_PORT` environment variable."*
   - Agent Red challenges Agent Blue:
     - *"Clarification: Function `export_csv` is exposed via CLI even though marked internal in comments."*
3. **Round 3 (Judge Adjudication & Model Synthesis)**:
   - The Main Agent acts as Chief Judge:
   - Resolves all objections, drops hallucinated claims, explicitly hedges unconfirmed features, and synthesizes the authoritative **`SemanticModel`**.