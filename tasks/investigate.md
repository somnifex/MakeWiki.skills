# Task: Domain Investigation (语义域调查)

## Overview

Investigation is Phase 2 of the MakeWiki pipeline. It converts the `InvestigationPlan`
(and its `SubtaskSpec` units) into per-domain, evidence-backed `ClaimBundle`s. Each
investigation subtask (`type: investigation`) targets **one coherent semantic domain**
— a single subsystem, surface, or concern — and returns claims that ground everything
later synthesized into the `SemanticModel`.

Investigation is a **cognitive** activity owned by a child **Explorer** subagent or the
Main Agent (solo fallback). Python's `evidence` / `scan` output is optional supporting
material only; it never dictates semantic domains, meaning, visibility, or abstraction.

---

## 1. One Subtask = One Coherent Semantic Domain

Each `SubtaskSpec` of `type: investigation` is scoped to exactly one coherent semantic
domain. A domain is a **concern or subsystem**, not a filename and not an entire
repository:

- Good: `investigate.management-api` (an operator/admin surface), `investigate.auth`

  (authentication & authorization semantics), `investigate.payments.webhooks`.
- Bad: `investigate.auth.py` (a file), `investigate.everything` (the whole repo).

Split an oversized domain by concern (`payments.core`, `payments.admin-api`,
`payments.reconciliation`), never by file index (`payments.file-1`). See
`SUBTASK_PROTOCOL.md` §4.

---

## 2. Scope Hint Is a Recommendation, Not a Hard Allowlist

`scope_hint` lists recommended starting points (paths, globs, surface names). The
Explorer must follow evidence wherever it leads and may read files outside the hints
when a claim depends on them. The hint exists to bound the *initial* search, not to
forbid legitimate traversal. What stays bounded is the **goal**, not the file reads.

---

## 3. Deliverable: `ClaimBundle`

Each investigation subtask terminates with one `ClaimBundle` (see
`ARTIFACT_CONTRACTS.md` §3 for the canonical schema):

```yaml
claim_bundle:
  id: claims.<domain-slug>
  domain: <domain-slug>
  producer_subtask: investigate.<domain-slug>

  summary: ""

  claims:
    - id: <stable-claim-slug>
      statement: ""
      semantic_key: <domain-slug>.<claim-slug>
      confidence: high | medium | low

      visibility:
        - public | user | developer | admin | operator | root | internal | unknown

      abstraction: product | workflow | interface | architecture | implementation | internal | unknown

      evidence:
        - path: ""
          symbol_or_location: ""
          rationale: ""

      uncertainty: null | ""

  unresolved: []

  newly_discovered_areas: []

  recommended_followups: []

  scope_expansions:
    - path: ""
      reason: ""
```

### Every claim must carry

- **`statement`**: a concrete, single assertion about stable behavior or an interface.
- **`evidence`**: at least one `path` (plus `symbol_or_location` and `rationale`)

  that a later reader can verify.
- **`rationale`**: why the cited code supports the statement.
- **`confidence`**: honest `high | medium | low`.

### `visibility` & `abstraction` are LLM judgments

`visibility` (who may reach this surface) and `abstraction` (product / workflow /
interface / architecture / implementation / internal) are **cognitive classifications**
made by the Explorer. Python must never infer them from directory names, AST patterns,
or framework conventions. When the Explorer cannot judge from evidence, it writes
`unknown` rather than guessing.

---

## 4. Non-Deterministic Judgments Stay in the LLM

- Never encode heuristics like `controllers/ ⇒ API` or `admin/ ⇒ operator` as rules.
- Do not let a path convention become a fact without corroborating evidence.
- When a surface is reachable only with credentials or privileges you cannot verify,

  record `visibility: unknown` / note the uncertainty instead of assuming `public`.

---

## 5. New Domains → Follow-up Only

If the Explorer discovers a coherent area outside the current domain, it does **not**
expand its own scope. It records the area under `newly_discovered_areas` and proposes
it as a `recommended_followup` (a new candidate `SubtaskSpec`) for the Main Agent to
evaluate. The Main Agent decides whether to dispatch a new investigation subtask.

---

## 6. Prohibitions & Strict Boundaries

During an investigation subtask the Explorer **MUST NOT**:
1. **Write documentation** — no end-user prose, Markdown pages, or manual text.
2. **Design the global IA** — no final page set, routes, or site hierarchy.
3. **Synthesize the SemanticModel** — investigation produces `ClaimBundle`s only;
   synthesis happens later from gathered bundles.
4. **Upgrade to ReBattle on ordinary ambiguity** — a normal ambiguity is first
   re-checked against evidence; only a hard conflict escalates to `conflict_resolution`.
5. **Invent facts for unproven unknowns** — mark unclear items as `uncertainty`,
   `unresolved`, or `confidence: low` rather than guessing.
6. **Delegate to grandchildren** — delegation depth is 1 (Explorer reports back to the
   Main Agent; it does not recursively spawn further investigators).

---

## 7. Stop Conditions

The Explorer **MUST STOP** when:
1. The domain's core capabilities, behaviors, and interfaces are identified.
2. Every important claim is backed by concrete file/location evidence.
3. Important uncertainties are explicitly recorded (`uncertainty`, `unresolved`).
4. `visibility` / `abstraction` were assigned by the LLM for each claim (or `unknown`
   where evidence is insufficient).
5. New areas are surfaced as `recommended_followups`, not absorbed into scope.

Terminate with a single explicit status: `completed`, `blocked`, or `needs_followup`,
and report the `artifact produced`, `uncertainties`, and any `scope expansions`.
