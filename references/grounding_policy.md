# Grounding Hierarchy & Verification Policy

## Overview

MakeWiki provides **evidence-backed documentation with layered automated
verification**. Every documented capability is anchored to one of the six
verification layers (L0 - L5); the Quality Gate aggregates them into a single
PASS / FAIL decision that maps to a CI exit code (0 / 1).

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
| **L0** | **Syntax**         | Markdown AST, single H1, heading hierarchy, valid internal relative links.                                                      | Mechanical                                                            | `OutputValidator` (`validate`)            |
| **L1** | **Existence**      | Every referenced file path, command executable, and config key exists in repository files.                                      | Mechanical                                                            | `CodebaseVerifier` (`verify-docs`)        |
| **L2** | **Interface**      | CLI argument names, parameter flags, default values, environment variable keys, and type constraints match source declarations. | Mechanical                                                            | `CodeGroundingVerifier` + AST Parser      |
| **L3** | **Behavior**       | Documented exit codes, error conditions, log locations, and execution workflows trace to source handlers.                       | LLM-judged (Python provides evidence list)                            | `L3BehaviorVerifier` + Auditor reasoning  |
| **L4** | **Cross-Language** | 100% character-for-character parity of all code blocks, commands, and config keys across all language versions.                 | Mixed (exact = Python; prose = LLM)                                   | `CrossLanguageReviewer` + `parity`        |
| **L5** | **Epistemic**      | All unconfirmed or derived claims carry consistent hedging caveats across all languages.                                        | LLM-judged (Python provides low-confidence / ungrounded command list) | `L5EpistemicVerifier` + Auditor reasoning |

Layer ownership is enforced by the boundary rules in `references/architecture.md`.
Mechanical layers must be `passed` for the gate to pass; LLM-judged layers may
remain `pending` when `quality.allow_pending_llm_layers` is true.

---

## 2. The Quality Gate

The Quality Gate is the **single PASS / FAIL decision** over all verification
layers. It lives at `src/makewiki_skills/verification/quality_gate.py` and is
exposed via the `verify-docs` CLI command.

```yaml
quality_gate:
  verdict_source: "evaluate_quality_gate(report, cfg)"
  result_type: "QualityGateResult"
  fields:
    passed: bool
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
  exit_code: "0 if passed else 1"

  config:
    quality.fail_on_critical: true    # bool, default true
    quality.min_grounding_score: 1.0  # float 0.0..1.0
    quality.allow_pending_llm_layers: true
```

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
  all_mechanical_passed: "syntax_passed AND existence_passed AND interface_passed"
  score_meets_threshold: "grounding_score >= quality.min_grounding_score"
  gate_passes_when:
    fail_on_critical: "all_mechanical_passed AND score_meets_threshold"
    not_fail_on_critical: "score_meets_threshold AND existence_passed"
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

### Mechanical Repair Boundary

The semantic revision path is `MechanicalRepairEngine` (module
`makewiki_skills.revision`; `RevisionEngine` retained as an alias). It applies
**mechanical repairs only**: cross-language code-block parity by stable block
ID and canned UNKNOWN evidence caveats. Anti-cliché prose rewriting is the LLM
Auditor's domain; Python never rewrites narrative voice.

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
  L0_syntax: "OutputValidator / validate"
  L1_existence: "CodebaseVerifier / verify-docs"
  L2_interface: "CodeGroundingVerifier + AST Parser / verify-docs"
  L3_behavior: "L3BehaviorVerifier (evidence) + Auditor reasoning / verify-docs + Auditor"
  L4_cross_language: "L4CrossLanguageVerifier + parity + Auditor prose review"
  L5_epistemic: "L5EpistemicVerifier (evidence list) + Auditor reasoning"
  gate: "evaluate_quality_gate / verify-docs exit code"
```