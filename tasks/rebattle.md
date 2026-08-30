# Task: ReBattle Competitive Verification with Subagent Self-Reflection (自反思对抗审查)

## Overview

ReBattle is Phase 2 of MakeWiki. It utilizes **autonomous Subagents with
internal self-reflection loops** across 3 distinct perspectives (Red, Blue,
Green) to debate, challenge, and converge on facts. The output of ReBattle
is a set of `Claim` objects (see `references/claim_schema.md`) with explicit
`provenance` markers — every claim is either a Python fact (`python_fact`)
or an LLM-authored assertion (`llm_claim`) so the downstream verification
layers can grade them appropriately.

The Python toolkit complements this with `rebattle-diff`, a deterministic
dispute organizer: given two or more ClaimSets (one per debater), it
produces a structured discrepancy matrix that the Chief Judge reads when
adjudicating.

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

Before issuing any claim or challenge, each Subagent executes an internal
self-critique:

1. **Self-Check Grounding**: Is every claimed command or flag directly

   backed by a line in source code? If not, the claim's `provenance` must
   be `llm_claim` and the claim must carry an `uncertainty` note; never
   fabricate a value the evidence cannot prove.
2. **Confidence Grading** (use the canonical claim vocabulary — values must be
   one of `high` / `medium` / `low` / `inferred`, which the pydantic claim
   model enforces):
   - `high`: 100% verified in source argument parser/handler (the ground truth
     tier formerly labeled `CONFIRMED_AST`).
   - `inferred`: Inferred from `.env.example` or manifest settings (formerly
     `DERIVED_CONFIG`).
   - `low`: Provisional/uncertain capability requiring explicit caveat (formerly
     `HYPOTHESIS_HEDGED`).
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
   - The Main Agent arbitrates discrepancies, purges refuted claims, hedges unconfirmed facts, and synthesizes the authoritative **`SemanticModel`**. `rebattle-diff` produces the discrepancy matrix used here.

The Judge must not promote an ungrounded `llm_claim` into a `python_fact` —
it can only keep it as `llm_claim` with explicit hedging or drop it
entirely.
