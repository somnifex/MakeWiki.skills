# Task: Hard-Conflict ReBattle & Dispute Resolution (硬冲突对决)

## Overview

ReBattle is an **escalation path** for genuinely hard disputes in the V3 pipeline —
**not** a mandatory Phase and **not** the default way to decide every disputed claim.
Ordinary ambiguity is resolved first by re-checking evidence; only a conflict that
survives evidence re-check and a targeted resolution attempt escalates here.

V3 replaces the V2 "Main Agent defaults to Judge" authority: the Main Agent does **not**
default to personally adjudicating every dispute. Evidence re-check, or a targeted
`conflict_resolution` subtask, settles most disagreements without debate.

`rebattle-diff` remains a **deterministic dispute organizer only** — it groups and
surfaces discrepancies, but it never decides semantic truth.

---

## 1. Conflict escalation order

Follow this order (mirrors `task: semantic` §3):

```text
conflict or ambiguity discovered
→ re-check the original evidence (primary sources)
   → resolved → update the claim, continue
→ still ambiguous → create a targeted conflict_resolution subtask
   → resolved → continue
→ still genuinely disputed → optional adversarial ReBattle (escalation, not default)
   → result returns to Semantic Synthesis
```

- **Ordinary ambiguity first**: resolve by re-inspecting primary sources and updating
  the claim directly — never by debate.
- **Hard conflict only escalates**: a conflict that survives evidence re-check and a
  targeted resolution attempt may escalate to adversarial ReBattle.
- **Main Agent is not the default Judge**: neither Python nor the Main Agent
  auto-adjudicates every dispute. When evidence re-check or a targeted subtask can
  settle it, use that. Unreconcilable fields keep an explicit hedge or `UNKNOWN` rather
  than a fabricated verdict.

---

## 2. `rebattle-diff` is a deterministic organizer only

`rebattle-diff` mechanically groups and organizes multiple ClaimSets / disputes so an
LLM can reason about them. It:
- groups conflicting claims and surfaces disagreements deterministically;
- never decides which claim is true;
- never classifies `visibility` / `abstraction` / meaning;
- is optional supporting material, not a resolution authority.

---

## 3. Dynamic Debater Role Synthesis

Only when a dispute escalates to ReBattle does the Main Agent synthesize debater
perspectives tailored to the specific disagreement (rather than a fixed mandatory
role set):

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

## 4. Subagent Self-Reflection Pass

Before submitting any claim, defense, or challenge, each Debater subagent executes
an internal self-critique:

1. **Grounding Verification**: Is every asserted command, argument flag, default value,
   or config key backed by concrete code citations? If ungrounded, hedge or retract
   immediately.
2. **Confidence Grading**:
   - `CONFIRMED_AST`: verified directly in source code / parser handlers.
   - `DERIVED_CONFIG`: inferred from manifest or sample config settings.
   - `HYPOTHESIS_HEDGED`: provisional/uncertain capability requiring explicit caveat.
3. **Adversarial Self-Correction**: When presented with unambiguous code line citations,
   immediately concede and retract invalid assertions.

---

## 5. Adversarial Resolution Protocol (escalation-scoped)

1. **Triage (`rebattle-diff`, optional)**: group the competing claims deterministically
   to make the genuine dispute legible.
2. **Targeted Debate Dispatch**: for genuinely disputed `semantic_key` entries, the Main
   Agent spawns the synthesized debater archetypes to defend or challenge positions,
   citing exact code lines.
3. **Convergence**: the debate terminates as soon as debaters concede/retract, or the
   facts stabilize.
4. **Outcome**: a claim either converges (with agreed provenance) or stays
   unreconcilable — in which case it is marked with an explicit hedge or `UNKNOWN`.
   A result never silently upgrades an ungrounded `llm_claim` into a `python_fact`.

---

## 6. Prohibitions & Strict Boundaries

During ReBattle (or a dispute-resolution subtask) the Agent **MUST NOT**:
1. **Treat ReBattle as a mandatory Phase** — it is escalation only, used when evidence
   re-check and a targeted subtask both fail to settle a hard conflict.
2. **Default to Main-Agent-as-Judge** — only genuinely unresolved disputes escalate;
   unreconcilable fields get a hedge / `UNKNOWN`, not a fabricated ruling.
3. **Let Python decide truth** — `rebattle-diff` merely organizes; it never
   adjudicates, classifies, or infers meaning.
4. **Get stuck on ordinary ambiguity** — that is resolved by re-checking evidence, not
   by debate.
5. **Endorse ungrounded `llm_claim` as `python_fact`** — provenance markers stay honest.
6. **Write final documentation or decide IA** — ReBattle resolves claims; later phases
   build pages from the reconciled `SemanticModel`.

---

## 7. Stop Conditions

ReBattle **MUST STOP** when:
1. Every escalated hard conflict either converges with agreed provenance, or is marked
   with an explicit hedge / `UNKNOWN`.
2. Ordinary ambiguities were resolved by evidence re-check, not by debate.
3. No ungrounded `llm_claim` was promoted to `python_fact`.
4. The reconciled claims return to Semantic Synthesis.
5. No final documentation or IA decision was produced here.

Terminate with a single status (`completed`, `blocked`, or `needs_followup`) and report
the `artifact produced` (the reconciled / hedged claim set), `uncertainties`, and any
`scope expansions`.
