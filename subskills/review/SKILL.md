---
name: makewiki-review
description: "Verify and review existing makewiki documentation: checks factual accuracy against project source code via the unified L0-L5 pipeline, compares structured facts and code blocks across all language versions, and audits enterprise delivery standards. Use when: user has generated multilingual docs and wants to verify consistency, accuracy, and completeness. Always finishes with the honest four-state Quality Gate verdict."
version: "3.0.0"
argument-hint: "[--lang <code>...]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Write Edit Glob Grep
---

# MakeWiki Review - L0-L5 Verification, Quality Gate & Cross-Language Parity

Review existing makewiki documentation for factual accuracy against actual
source code, 100% code block parity across languages, and enterprise
delivery runbook completeness. The Python toolkit runs the mechanical layers
(L0 syntax, L1 existence, L2 interface, L4 block-ID parity) and prepares
aligned passages for the LLM-driven Auditor to grade L3 (behavior),
L4-prose, and L5 (over-assertion). The Quality Gate aggregates the result
into an honest four-state verdict — `passed`, `pending_semantic_review`,
`pending_mechanical_verification`, `failed` — mapped to the CI exit policy
(`passed→0`, `failed→1`, `pending_semantic_review→0` when
`allow_pending_llm_layers` / else 2, `pending_mechanical_verification→3`).

## Arguments

- `--lang <code>` (repeatable): Languages to review. Default: auto-detect.

## Execution

### Step 1: Bootstrap the home-scoped toolkit

```bash
python scripts/bootstrap_toolkit.py
```

If the script prints a path, refer to it as `<makewiki_root>` and run the
mechanical verification:

```bash
python <makewiki_root>/scripts/run_toolkit.py verify-docs . --format json
python <makewiki_root>/scripts/run_toolkit.py parity . --lang en --lang zh-CN
python <makewiki_root>/scripts/run_toolkit.py semantic-review ./makewiki --lang en --lang zh-CN --format json
```

`verify-docs` produces the unified L0–L5 + Quality Gate verdict as an honest
four-state result (`passed` / `failed` / `pending_semantic_review` /
`pending_mechanical_verification`) with separate **Failed Checks**,
**Pending Semantic Reviews**, **Unknown / Insufficient Evidence**, and
**Warnings** sections in human output. `parity` produces the block-ID
exact-match report. `semantic-review` produces aligned passages for the LLM
Auditor.

### Step 2: LLM Adversarial Audit

The Auditor subagent consumes the L0–L5 report, the parity deltas, and the
aligned passages, then judges the LLM-judged layers:

1. **L3 Behavior Audit** — does each documented command behave as described
   when actually run?
2. **L4b Prose Parity Audit** — do the aligned passages agree in meaning
   across languages (after Python's L4a block-ID parity already enforced exact
   code/command parity)? L4 matching is keyed on stable block IDs
   (`[[id:...]]`) and stable H2 section markers
   (`<!-- makewiki:section=<slug> -->`), never on heading text or heading
   position — section ORDER may legitimately differ per language. For
   multilingual output every reviewable H2 MUST carry a stable section marker,
   and duplicate section or block IDs within one document are L4a failures.
3. **L5 Over-Assertion Audit** — are any claims more confident than the
   evidence supports? Are anti-AI-cliché rules followed?

The Auditor uses the `references/anti_ai_cliche.md` style guide plus the
Quality Gate thresholds from `makewiki.config.yaml:quality`.

**Emit the SemanticAuditBundle.** After judging, the Auditor writes a
machine-readable `SemanticAuditBundle` JSON capturing its L3 / L4b / L5
verdicts — schema `{schema_version, documents_digest, semantic_model_digest?,
auditor, audited_at, verdicts:[{review_item_id, layer: L3|L4b|L5, status:
passed|failed, rationale_summary, evidence_refs, confidence}]}`. The bundle is
**item-level**: each `SemanticAuditVerdict` targets exactly one
`review_item_id` (e.g. `L3:README.md:make build`, `L4b:README.md:build`,
`L5:README.md:make build`). The report's `review_items` registry lists the
expected semantic review items for L3 / L4b / L5 — the bundle can only
adjudicate items that exist in this registry; a verdict for an unknown
`review_item_id` rejects the whole bundle, and omitted items remain `pending`.
`documents_digest` is a sha256 over the audited markdown set, binding the
audit to that exact revision (it includes each file's identity:
`path + NUL + byte_length + NUL + file_bytes + NUL`, sorted by relative path).
If the documents change after the bundle is written, the bundle is
stale and must be rejected and re-audited. Python validates schema and digests
but never re-judges the semantic verdicts; merged checks carry
`verification_source = "semantic_audit_bundle"` plus the verdict's
`review_item_id`, auditor, rationale, confidence, evidence refs, and
`audited_at`.

### Step 3: In-Place Revision & Final Report

- If discrepancies are detected, the Auditor revises the markdown files in
  place via the Skill's Semantic Revision step (Phase 3.5).
- Ensure all languages receive matching fixes for code blocks and facts.
- Re-emit the `SemanticAuditBundle` **after** all in-place edits so its
  `documents_digest` matches the final markdown set, then consume it with
  `verify-docs --semantic-audit <file>` (a flag on the existing `verify-docs`
  command) so the Quality Gate merges the Auditor's semantic verdicts
  item-level by `review_item_id`. When the bundle declares a
  `semantic_model_digest`, also pass `--semantic-model <file>` to prove the
  model binding; without it the binding is UNPROVEN and L3 / L4b / L5 stay
  `pending` (never silently trusted):
  ```bash
  python <makewiki_root>/scripts/run_toolkit.py verify-docs . --semantic-audit ./makewiki/semantic_audit.json --semantic-model ./makewiki/semantic_model.json
  ```
  A stale bundle (digest mismatch), an unprovable model binding, or any verdict
  for an unknown `review_item_id` rejects the bundle and the affected layers
  stay `pending` until re-audited.
- The final report contains real quality metrics: per-layer L0–L5 status,
  Grounding Score, Unresolved Claims, and the Quality Gate verdict — never
  the marketing phrase "zero-hallucination".
