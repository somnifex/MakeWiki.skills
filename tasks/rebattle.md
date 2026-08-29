# Task: ReBattle Competitive Verification with Subagent Self-Reflection (自反思对抗审查)

## Overview

ReBattle is Phase 2 of MakeWiki. It utilizes **autonomous Subagents with internal self-reflection loops** across 3 distinct perspectives (Red, Blue, Green) to debate, challenge, and converge on facts.

---

## 1. Subagent ReBattle Topology

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

---

## 2. Mandatory Subagent Self-Reflection Pass

Before issuing any claim or challenge, each Subagent executes an internal self-critique:
1. **Self-Check Grounding**: Is every claimed command or flag directly backed by a line in source code?
2. **Confidence Grading**:
   - `CONFIRMED_AST`: 100% verified in source argument parser/handler.
   - `DERIVED_CONFIG`: Inferred from `.env.example` or manifest settings.
   - `HYPOTHESIS_HEDGED`: Provisional/uncertain capability requiring explicit caveat.
3. **Adversarial Self-Correction**: When countered with AST evidence, immediately concede and retract invalid claims without stubborn persistence.

---

## 3. Multi-Agent Cross-Examination Debate Protocol

1. **Round 1 (Blind Independent Extraction + Self-Reflection)**:
   - Red, Blue, Green Subagents independently extract facts, self-critique, and formulate their initial claim sets.
2. **Round 2 (Adversarial Challenge & Cross-Examination)**:
   - Agent Blue challenges Agent Red: *"Objection: `--fast` flag proposed by Agent Red does not exist in cli.py parser; flag is invalid."*
   - Agent Green challenges Agent Red: *"Objection: Quickstart tutorial omits mandatory `DB_PORT` environment variable."*
   - Agent Red challenges Agent Blue: *"Clarification: Function `export_csv` is exposed via CLI even though marked internal in comments."*
3. **Round 3 (Judge Adjudication & Model Synthesis)**:
   - The Main Agent arbitrates discrepancies, purges refuted claims, hedges unconfirmed facts, and synthesizes the authoritative **`SemanticModel`**.