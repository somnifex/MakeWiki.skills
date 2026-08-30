---
name: makewiki-review
description: "Verify and review existing makewiki documentation: checks factual accuracy against project source code via the unified L0-L5 pipeline, compares structured facts and code blocks across all language versions, and audits enterprise delivery standards. Use when: user has generated multilingual docs and wants to verify consistency, accuracy, and completeness. Always finishes with a Quality Gate PASS/FAIL."
version: "2.0.0"
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
into PASS / FAIL mapped to the CI exit code.

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

`verify-docs` produces the unified L0–L5 + Quality Gate verdict (exit code
0 PASS / 1 FAIL). `parity` produces the block-ID exact-match report.
`semantic-review` produces aligned passages for the LLM Auditor.

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
   position — section ORDER may legitimately differ per language.
3. **L5 Over-Assertion Audit** — are any claims more confident than the
   evidence supports? Are anti-AI-cliché rules followed?

The Auditor uses the `references/anti_ai_cliche.md` style guide plus the
Quality Gate thresholds from `makewiki.config.yaml:quality`.

**Emit the SemanticAuditBundle.** After judging, the Auditor writes a
machine-readable `SemanticAuditBundle` JSON capturing its L3 / L4b / L5
verdicts — schema `{schema_version, documents_digest, semantic_model_digest?,
auditor, audited_at, verdicts:[{review_item_id, layer: L3|L4b|L5, status:
passed|failed, rationale_summary, evidence_refs, confidence}]}`. `documents_digest`
is a sha256 over the audited markdown set, binding the audit to that exact
revision. If the documents change after the bundle is written, the bundle is
stale and must be rejected and re-audited. Python validates schema and digests
but never re-judges the semantic verdicts.

### Step 3: In-Place Revision & Final Report

- If discrepancies are detected, the Auditor revises the markdown files in
  place via the Skill's Semantic Revision step (Phase 3.5).
- Ensure all languages receive matching fixes for code blocks and facts.
- Re-emit the `SemanticAuditBundle` **after** all in-place edits so its
  `documents_digest` matches the final markdown set, then consume it with
  `verify-docs --semantic-audit <file>` (a flag on the existing `verify-docs`
  command) so the Quality Gate folds the Auditor's semantic verdicts in:
  ```bash
  python <makewiki_root>/scripts/run_toolkit.py verify-docs . --semantic-audit ./makewiki/semantic_audit.json
  ```
  A stale bundle (digest mismatch) is rejected and the affected layers stay
  `pending` until re-audited.
- The final report contains real quality metrics: per-layer L0–L5 status,
  Grounding Score, Unresolved Claims, and the Quality Gate verdict — never
  the marketing phrase "zero-hallucination".
