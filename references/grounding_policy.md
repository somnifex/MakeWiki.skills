# Grounding Hierarchy & Verification Policy

## Overview

MakeWiki provides **evidence-backed documentation with layered automated
verification**. Every documented capability is anchored to one of the six
verification layers (L0 - L5); the Quality Gate aggregates them into an
honest four-state verdict — `passed`, `pending_semantic_review`,
`pending_mechanical_verification`, `failed` — that maps to a CI exit policy.

### Cognitive Authority Boundary

LLM Agents are the authoritative decision makers for semantic work. Python
tooling MUST NOT invent semantic conclusions. When deterministic tooling
cannot mechanically establish a fact, it MUST return UNKNOWN rather than
guess. Python-generated semantic conclusions MUST NOT override LLM Agent
adjudication in the authoritative `/makewiki` path.

---

## 1. The L0 - L5 Verification Hierarchy

| Level  | Name               | Scope & Check Criteria                                                                                                          | Owner                                                                 | Mechanical Tool                           |
| ------ | ------------------ | ------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- | ----------------------------------------- |
| **L0** | **Syntax**         | Markdown AST, single H1, heading hierarchy, valid internal relative links.                                                      | Mechanical                                                            | `L0SyntaxVerifier` (`verify-docs`)        |
| **L1** | **Existence**      | Every referenced file path, command executable, and config key exists in repository files.                                      | Mechanical                                                            | `L1ExistenceVerifier` (`verify-docs`)     |
| **L2** | **Interface**      | CLI argument names, parameter flags, default values, environment variable keys, and type constraints match source declarations. | Mechanical                                                            | `L2InterfaceVerifier` + AST Parser        |
| **L3** | **Behavior**       | Documented exit codes, error conditions, log locations, and execution workflows trace to source handlers.                       | LLM-judged (Python provides evidence list)                            | `L3BehaviorVerifier` + Auditor reasoning  |
| **L4** | **Cross-Language** | 100% character-for-character parity of all code blocks, commands, and config keys across all language versions.                 | Mixed (exact = Python; prose = LLM)                                   | `CrossLanguageReviewer` + `parity`        |
| **L5** | **Epistemic**      | All unconfirmed or derived claims carry consistent hedging caveats across all languages.                                        | LLM-judged (Python provides low-confidence / ungrounded command list) | `L5EpistemicVerifier` + Auditor reasoning |

Layer ownership is enforced by the boundary rules in `references/architecture.md`.
Mechanical layers must be `passed` for the gate to pass; LLM-judged layers may
remain `pending` when `quality.allow_pending_llm_layers` is true.

---

## 2. The Quality Gate

The Quality Gate is the **honest four-state verdict** over all verification
layers — it is not a single PASS / FAIL. It lives at
`src/makewiki_skills/verification/quality_gate.py` and is exposed via the
`verify-docs` CLI command.

The four states:

- `passed` — every layer adjudicated and non-blocking (`passed == (verdict ==

  "passed")` strictly; a pending gate is never reported as passed).
- `pending_semantic_review` — the LLM layer (L3 / L4b / L5) has pending items

  (`semantic_complete=False`).
- `pending_mechanical_verification` — a mechanical layer (L0 / L1 / L2 / L4a)

  is still pending.
- `failed` — any layer explicitly failed.

CI exit policy (`ci_exit_code` is the single source of truth):

| Verdict                           | CI exit code                                                |
| --------------------------------- | ----------------------------------------------------------- |
| `passed`                          | 0                                                           |
| `failed`                          | 1                                                           |
| `pending_semantic_review`         | 0 (when `quality.allow_pending_llm_layers` is true, else 2) |
| `pending_mechanical_verification` | 3                                                           |

```yaml
quality_gate:
  verdict_source: "evaluate_quality_gate(report, cfg)"
  result_type: "QualityGateResult"
  fields:
    passed: bool
    verdict: "passed | pending_semantic_review | pending_mechanical_verification | failed"
    syntax_passed: bool               # L0
    existence_passed: bool            # L1
    interface_passed: bool            # L2
    behavior_passed: bool             # L3
    cross_language_passed: bool       # L4
    epistemic_passed: bool            # L5
    grounding_score: float            # 0.0 .. 1.0
    unresolved_critical: int
    unresolved_major: int
    unresolved_minor: int
    revision_rounds: int
    details: dict
  ci_exit_code: "0 passed | 1 failed | 0/2 pending_semantic_review (0 granted by quality.allow_pending_llm_layers, else 2) | 3 pending_mechanical_verification"

  config:
    quality.min_grounding_score: 1.0  # float 0.0..1.0; sole Quality Gate grounding threshold
    quality.allow_pending_llm_layers: true  # EXIT POLICY ONLY; never changes the truth verdict
```

`allow_pending_llm_layers` is EXIT POLICY ONLY: it maps a
`pending_semantic_review` verdict to exit 0 (when true, the default) or the
honest base 2 (when false). It NEVER changes the truth verdict — an un-reviewed
LLM layer (L3 / L4b / L5) is always `pending_semantic_review`, never `failed`:
Python must not convert a pending semantic item into a failure. The verdict /
UI reads PENDING_SEMANTIC_REVIEW in both cases.

### Layer Status Semantics

```yaml
layer_status:
  passed: "A verifier actually executed the check and proved it. Never marked 'passed' merely because it was not run."
  failed: "A verifier ran and found a contradiction."
  pending: "No verifier ran / not yet proven (LLM-judged layers: L3 behavior, L4 prose-parity, L5 epistemic, and un-resolved command/behavior claims)."
  unknown: "Insufficient evidence to decide either way."
  not_applicable: "Genuinely irrelevant (e.g. L4 cross-language parity for a single-language project)."
  warning: "Advisory; does not fail the gate."
  rule: "Python never marks a layer 'passed' without actually proving it; the Quality Gate reports LLM-judged 'pending' layers transparently."
```

### Gate Decision Rules

```yaml
decision_rules:
  all_mechanical_passed: "L0 passed AND L1 passed AND L2 passed AND L4a passed"
  meets_score: "mechanical_score >= quality.min_grounding_score"
  pending_llm: "any of L3 / L4b / L5 is pending or unknown"
  pending_mechanical: "any of L0 / L1 / L2 / L4a is pending"
  verdict:
    failed: "any mechanical layer failed (or mechanical-score shortfall), OR any LLM-judged check explicitly failed"
    pending_mechanical_verification: "no failures, but a mechanical layer (L0/L1/L2/L4a) is still pending"
    pending_semantic_review: "no failures, mechanical layers resolved, but an LLM layer (L3/L4b/L5) is pending; this verdict NEVER flips to failed — allow_pending_llm_layers affects only the exit code"
    passed: "every layer adjudicated and non-blocking (strictly verdict == 'passed')"
  exit_policy:
    passed: 0
    failed: 1
    pending_semantic_review: "0 when quality.allow_pending_llm_layers is true, else 2"
    pending_mechanical_verification: 3
```

---

## 3. The LLM Role in Verification

The mechanical plane proves structure (L0 / L1 / L2 / L4-exact). The LLM
judges meaning (L3 behavior, L4 prose parity, L5 epistemic). The boundary is
strict:

```yaml
llm_verification_role:

  L3_behavior:
    python_provides: "List of documented behaviors + their source-handler traces"
    llm_judges: "Whether the documented behavior actually matches the user's mental model and the codebase reality"

  L4_prose_parity:
    python_provides: "Aligned passages across languages (semantic-review output) + exact block parity (parity)"
    llm_judges: "Whether prose meaning is consistent across languages"

  L5_epistemic:
    python_provides: "List of low-confidence / ungrounded / over-asserted claims"
    llm_judges: "Whether each claim is hedged or retracted appropriately"

  rule: "Python returns evidence; LLM returns judgment; Quality Gate combines."
```

### Revision & Repair Boundary

All semantic revisions, hedging adjustments, and anti-cliché prose rewrites are
performed in-place by the LLM Auditor (bounded by `agent.max_audit_rounds`).
Python mechanical tooling performs verification (`verify-docs`, `parity`,
`review`, `validate`) and returns evidence and status verdicts to guide the
Auditor. Python owns no cognitive rewriting.

---

## 4. Evidence-Backed Documentation (Replaces "zero-hallucination")

MakeWiki uses **evidence-backed documentation with layered automated
verification** instead of any zero-hallucination marketing claim. Documentation
quality is measured by:

- **Grounding Score**: proportion of L0 - L5 checks that pass (0.0 .. 1.0).
- **Layer Statuses**: per-layer passed / failed / pending counts.
- **Unresolved Claims**: critical / major / minor counts surfaced by the

  Quality Gate.
- **Revision Rounds**: how many in-place self-healing iterations the

  Auditor required before the gate passed.

```yaml
evidence_backed_metrics:
  grounding_score: "0.0 .. 1.0 (1.0 means every mechanical layer fully passed)"
  unresolved_critical: "Mechanical-layer failures + score shortfalls"
  unresolved_major: "Mechanical-layer failures (subset of critical)"
  unresolved_minor: "Style / clarity nits deferred to revision"
  revision_rounds: "Auditor in-place iteration count"
```

---

## 5. Mechanical UNKNOWN Contract

When Python cannot mechanically prove a slot, it leaves the slot empty and
emits an explicit `UNKNOWN` marker. The Skill layer (LLM) fills the slot via
ClaimSet authoring, or leaves it marked so a human reviewer can address it.

```yaml
mechanical_unknown_contract:

  rule: "When Python cannot mechanically prove a slot, leave it empty and emit an UNKNOWN marker"

  examples:
    installation.verify_command:
      proven: "extracted from Makefile / pyproject / README smoke test"
      unproven: "emit UNKNOWN; do not invent 'make test' or similar default"
    installation.steps:
      proven: "extracted from build scripts"
      unproven: "do not inject canned 'clone the repository' step"
    faq / troubleshooting / usage_examples:
      proven: "LLM-authored through ClaimSet"
      unproven: "do not synthesize via regex heuristics"

  scaffold_output:
    contains: "What Python can prove + UNKNOWN markers for the rest"
    never_contains: "Invented FAQ / troubleshooting / usage / install defaults"
```

---

## 6. Layer-To-Tool Mapping (Quick Reference)

```yaml
layer_to_tool:
  L0_syntax: "L0SyntaxVerifier / verify-docs"
  L1_existence: "L1ExistenceVerifier / verify-docs"
  L2_interface: "L2InterfaceVerifier + AST Parser / verify-docs"
  L3_behavior: "L3BehaviorVerifier (evidence) + Auditor reasoning / verify-docs + Auditor"
  L4_cross_language: "L4CrossLanguageVerifier + parity + Auditor prose review"
  L5_epistemic: "L5EpistemicVerifier (evidence list) + Auditor reasoning"
  gate: "evaluate_quality_gate / verify-docs exit code"
```