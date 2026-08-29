# Claim Schema & Representation Standard

## Overview

In MakeWiki v2, documentation is treated as a set of **structured, verifiable
Claims** rather than unconstrained markdown strings. All multi-language
writers render verified Claims. Every Claim carries a `provenance` marker
that distinguishes **LLM-authored claims** (`llm_claim`) from **Python-extracted
facts** (`python_fact`); the L0–L5 verification pipeline grades both using
the same status vocabulary, but `llm_claim` items are subject to additional
over-assertion review at L5.

---

## 1. Claim Data Model

```json
{
  "claim_id": "CLI_SCAN_JSON",
  "type": "command_interface",
  "semantic_key": "scanner.cli.scan",
  "subject": "makewiki scan",
  "predicate": "produces",
  "object": "structured JSON evidence bundle",
  "provenance": "python_fact",
  "command": {
    "executable": "makewiki",
    "subcommand": "evidence",
    "arguments": ["."],
    "flags": ["--format json"],
    "expected_output_type": "application/json"
  },
  "evidence": [
    {
      "source_file": "src/makewiki_skills/cli.py",
      "line_range": [120, 145],
      "raw_text": "@app.command(name=\"evidence\")\ndef evidence(...):",
      "extraction_method": "ast_parser",
      "confidence": "high"
    }
  ],
  "verification": {
    "l0_syntax": "passed",
    "l1_existence": "passed",
    "l2_interface": "passed",
    "l3_behavior": "pending",
    "l4_cross_language": "pending",
    "l5_epistemic": "pending"
  },
  "uncertainty": null
}
```

`l3_behavior`, `l4_cross_language` (prose portion), and `l5_epistemic` are
**LLM-judged layers**: Python emits the underlying evidence and a tentative
status, and the Skill layer's Auditor / Semantic Revision step resolves them
into `passed` / `failed` / `hedged`. The Quality Gate reads the resolved
status to decide PASS / FAIL.

---

## 2. Claim-Level Multilingual Rendering

All target languages (`en`, `zh-CN`, `ja`, etc.) share the exact same `claim_id`
and executable command representation:

- **English Prose**: `Run \`makewiki evidence . --format json\` to generate a structured evidence bundle.`
- **Chinese Prose**: `运行 \`makewiki evidence . --format json\` 获取结构化代码证据清单。`

This guarantees 100% parameter and code block parity across all language
versions. The Mechanical Plane enforces exact block parity by comparing block
IDs; the LLM-driven Auditor resolves prose parity via `semantic-review`.
