# Task: Dynamic Conflict ReBattle & Dispute Resolution (冲突驱动动态对决)

## Overview

ReBattle is Phase 2 of MakeWiki. It is a **dynamic dispute resolution protocol
governed exclusively by the Main Agent** to resolve contradictions, ambiguous assertions,
and unverified claims discovered during reconnaissance before documentation authoring begins.

Instead of running a rigid fixed-round sequence with mandatory roles, the
Main Agent evaluates discrepancies using `rebattle-diff` (a deterministic
dispute organizer), dynamically synthesizes debater roles tailored to the specific
disputes, and terminates debate as soon as facts converge.

The output of ReBattle is a unified `SemanticModel` and an adjudicated `ClaimSet`
(see `references/claim_schema.md`) with explicit provenance markers: every claim is either
a mechanically verified fact (`python_fact`) or an LLM-authored assertion (`llm_claim`).

---

## 1. Dynamic Debater Role Synthesis

Rather than enforcing a fixed set of mandatory debater roles, the Main Agent analyzes
the dispute matrix and synthesizes debater perspectives that directly address the root of the disagreement:

```yaml
dynamic_debater_synthesis_examples:
  fork_or_divergence_dispute:
    role: "Fork Provenance Agent"
    focus: "Distinguishes upstream inherited legacy facts from current fork behaviors and patch sets"
  code_vs_doc_drift_dispute:
    role: "Stale Documentation Agent vs. Runtime Truth Agent"
    focus: "Audits outdated README claims against actual AST parsers, route definitions, and defaults"
  config_priority_override_dispute:
    role: "Config Hierarchy Agent"
    focus: "Traces environment variables, CLI flags, config files, and fallback evaluation orders"
  production_readiness_dispute:
    role: "Enterprise Ops Agent"
    focus: "Challenges ungrounded runtime assumptions, missing prerequisites, or omitted failure runbooks"
```

---

## 2. Subagent Self-Reflection Pass

Before submitting any claim, defense, or challenge, each Debater subagent executes
an internal self-critique:

1. **Grounding Verification**: Is every asserted command, argument flag, default value, or config key backed by concrete code citations? If ungrounded, hedge or retract immediately.
2. **Confidence Grading**:
   - `CONFIRMED_AST`: 100% verified in source code / parser handlers.
   - `DERIVED_CONFIG`: Inferred from manifest or sample config settings.
   - `HYPOTHESIS_HEDGED`: Provisional/uncertain capability requiring explicit caveat.
3. **Adversarial Self-Correction**: When presented with unambiguous code line citations, immediately concede and retract invalid assertions.

---

## 3. Dynamic Dispute Resolution Protocol

1. **Dispute Triage (`rebattle-diff`)**:
   - The Main Agent aggregates claims from Scout Search Ledgers.
   - If no conflicts or ambiguities exist: **Immediate Consensus Path** $\rightarrow$ proceed straight to `SemanticModel` compilation without debate rounds.
2. **Targeted Debate Dispatch**:
   - For disputed `semantic_key` entries (e.g. CLI flag drift, default port disagreement), the Main Agent spawns or messages the synthesized debater archetypes.
   - Subagents provide targeted defense or challenges citing exact code lines.
3. **Dynamic Convergence & Stopping Rule (Main Agent Owned)**:
   - The Main Agent evaluates debate progress after each exchange.
   - The loop terminates as soon as debaters concede/retract, or when the Main Agent determines that facts have stabilized.
   - If a dispute cannot be conclusively resolved from code, the Main Agent rules as Judge to mark the field with an explicit hedge or render `UNKNOWN`.
4. **Judge Adjudication & Model Synthesis**:
   - The Main Agent acts as Judge, compiles the authoritative **`SemanticModel`**, hedges unconfirmed assertions, and purges refuted claims.
   - The Judge never promotes an ungrounded `llm_claim` into a `python_fact` — it remains an `llm_claim` with explicit hedging or is dropped entirely.