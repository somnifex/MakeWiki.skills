# Claim Schema & Representation Standard

## Overview

In MakeWiki v2, documentation is treated as a set of **structured, verifiable Claims** rather than unconstrained markdown strings. All multi-language writers generate documents by rendering verified Claims.

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
  "command": {
    "executable": "makewiki",
    "subcommand": "scan",
    "arguments": ["."],
    "flags": ["--format json"],
    "expected_output_type": "application/json"
  },
  "evidence": [
    {
      "source_file": "src/makewiki_skills/cli.py",
      "line_range": [120, 145],
      "raw_text": "@app.command()\ndef scan(...):",
      "extraction_method": "ast_parser",
      "confidence": "high"
    }
  ],
  "verification": {
    "l0_syntax": "passed",
    "l1_existence": "passed",
    "l2_interface": "passed",
    "l3_behavior": "passed",
    "l4_cross_language": "passed",
    "l5_epistemic": "passed"
  },
  "uncertainty": null
}
```

---

## 2. Claim-Level Multilingual Rendering

All target languages (`en`, `zh-CN`, `ja`, etc.) share the exact same `claim_id` and executable command representation:

- **English Prose**: `Run \`makewiki scan . --format json\` to generate a structured evidence bundle.`
- **Chinese Prose**: `运行 \`makewiki scan . --format json\` 获取结构化代码证据清单。`

This guarantees 100% parameter and code block parity across all language versions.
