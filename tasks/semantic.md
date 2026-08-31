# Task: Semantic Synthesis (语义综合)

## Overview

Semantic Synthesis is Phase 3 of the MakeWiki pipeline. The **Semantic Analyst**
receives the `RepositoryBrief`, the `InvestigationPlan`, and the gathered per-domain
`ClaimBundle`s, and reconciles them into the canonical **`SemanticModel`** — the single
authoritative statement of *what the software is*, its stable behaviors and interfaces,
how major concepts relate, and what remains uncertain.

Synthesis is a **cognitive** activity. It does not decide page layout (that is
Documentation Modeling / Page Planning), and it does not write final prose.

---

## 1. Inputs

```text
RepositoryBrief
+ InvestigationPlan
+ relevant ClaimBundles  (claims.<domain-slug>)
→ SemanticModel
```

The Semantic Analyst is grounded only in these artifacts and the underlying evidence;
it must not silently reuse prior-phase conclusions without re-examining their evidence
where a decision depends on them.

---

## 2. Semantic Analyst Responsibilities

Produce the `SemanticModel` by:

- **claim normalization**: deduplicate and align claims across bundles, resolving

  redundant phrasings without changing meaning;
- **entity identification**: recognize the stable entities / surfaces the software

  exposes;
- **relationship synthesis**: state how major concepts relate;
- **user-visible capability identification**: what stable behavior users and operators

  can exercise;
- **public / internal classification**: which behaviors are public, developer,

  operator, admin, or internal (LLM judgment, `COGNITIVE_BOUNDARY.md`);
- **abstraction classification**: product / workflow / interface / architecture /

  implementation / internal (LLM judgment);
- **conflict detection**: surface disagreements between claims or between claims and

  evidence;
- **confidence and uncertainty**: record honest confidence and explicit unknowns.

Python's `SemanticModel` (`.py`) is the mechanical data container; the Analyst fills its
semantic content. Python never decides meaning, persona, capability, classification, or
IA.

---

## 3. Conflict Handling: Escalation, Not Default Judgment

Synthesis is **not** a fixed conflict phase. Follow this order:

```text
conflict or ambiguity discovered
→ Semantic Analyst re-checks the original evidence
→ re-inspection of primary sources resolves it
   → update claims and continue
→ still ambiguous after evidence re-check
   → create a targeted conflict-resolution subtask
   → still genuinely disputed
      → optional adversarial ReBattle (escalation, not default)
→ result returns to Semantic Synthesis
```

### Ordinary ambiguity first

A normal ambiguity is resolved by **re-checking evidence**, not by debate. Reopen the
investigation, inspect primary sources, and update or resolve the claim directly.

### Hard conflict only escalates

Only a conflict that survives evidence re-check and targeted resolution escalates to
`conflict_resolution` / ReBattle. ReBattle is an **escalation path**, not a mandatory
phase, and not the default way to decide every disputed claim.

### Main Agent is not the default Judge

The Main Agent must **not** default to personally judging every dispute. When evidence
re-check or a targeted subtask can settle the matter, use that. Escalate to adversarial
debate only for genuinely unresolved disputes, and mark unreconcilable fields with an
explicit hedge or `UNKNOWN` rather than fabricating a verdict.

`rebattle-diff` remains a deterministic dispute *organizer* only; it never decides the
semantic truth.

---

## 4. Deliberate, Evidence-Backed Claims

- Every `SemanticModel` claim retains provenance back to the originating `ClaimBundle`

  and its evidence (`path` / `symbol_or_location` / `rationale`).
- `confidence` is honest (`high | medium | low`); lower-confidence claims must not be

  silently upgraded to certainty in a later layer.
- Classifications (`visibility`, `abstraction`) come from the LLM; when evidence is

  insufficient, write `unknown` instead of guessing.
- No framework-specific semantic rules: never let path conventions (e.g.

  `controllers/ ⇒ API`, `admin/ ⇒ operator`) become canonical facts without evidence.

---

## 5. Prohibitions & Strict Boundaries

During semantic synthesis the Analyst **MUST NOT**:
1. **Write final documentation** — no end-user prose or Markdown pages.
2. **Design the final IA / page layout** — the `SemanticModel` is not the page
   directory; Documentation Modeling derives audience needs from it.
3. **Decide every conflict by default adjudication** — escalate only genuinely hard
   conflicts; re-check evidence first.
4. **Promote unproven unknowns to facts** — mark `uncertainty` / `UNKNOWN` rather than
   guess.
5. **Defer semantic meaning to Python** — Python validates structure, never meaning.

---

## 6. Stop Conditions

The Analyst **MUST STOP** when:
1. All gathered `ClaimBundle`s are normalized and reconciled into the `SemanticModel`.
2. Major entities, behaviors, and relationships are stated with provenance.
3. Conflicts are resolved by evidence re-check or explicitly escalated (with
   `UNKNOWN` / hedge where truly unreconcilable).
4. `visibility` / `abstraction` classifications are assigned by the LLM (or `unknown`).
5. Important uncertainties are explicitly recorded.
6. No final page layout or documentation prose has been produced.

Terminate with a single status (`completed`, `blocked`, or `needs_followup`) and report
the `artifact produced`, `uncertainties`, and any `scope expansions`.
