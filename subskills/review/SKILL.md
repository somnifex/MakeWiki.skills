---
name: makewiki-review
description: "Verify and review existing makewiki documentation: checks factual accuracy against project source code via the unified L0-L5 pipeline, compares structured facts and code blocks across all language versions, and audits enterprise delivery standards. Use when: user has generated multilingual docs and wants to verify consistency, accuracy, and completeness. Always finishes with a Quality Gate PASS/FAIL."
version: "2.0.0"
argument-hint: "[--lang <code>...]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Glob Grep
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
2. **L4 Prose Parity Audit** — do the aligned passages agree in meaning
   across languages (after Python's block-ID parity already enforced exact
   code/command parity)?
3. **L5 Over-Assertion Audit** — are any claims more confident than the
   evidence supports? Are anti-AI-cliché rules followed?

The Auditor uses the `references/anti_ai_cliche.md` style guide plus the
Quality Gate thresholds from `makewiki.config.yaml:quality`.

### Step 3: In-Place Revision & Final Report

- If discrepancies are detected, the Auditor revises the markdown files in
  place via the Skill's Semantic Revision step (Phase 3.5).
- Ensure all languages receive matching fixes for code blocks and facts.
- The final report contains real quality metrics: per-layer L0–L5 status,
  Grounding Score, Unresolved Claims, and the Quality Gate verdict — never
  the marketing phrase "zero-hallucination".
