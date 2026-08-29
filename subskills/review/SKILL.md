---
name: makewiki-review
description: "Verify and review existing makewiki documentation: checks factual accuracy against project source code, compares structured facts and code blocks across all language versions, and audits enterprise delivery standards. Use when: user has generated multilingual docs and wants to verify consistency, accuracy, and completeness."
version: "2.0.0"
argument-hint: "[--lang <code>...]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Glob Grep
---

# MakeWiki Review - Cross-Language, Codebase & Enterprise Delivery Check

Review existing makewiki documentation for factual accuracy against actual source code, 100% code block parity across languages, and enterprise delivery runbook completeness.

## Arguments

- `--lang <code>` (repeatable): Languages to review. Default: auto-detect.

## Execution

### Step 1: Bootstrap the home-scoped toolkit

```bash
python scripts/bootstrap_toolkit.py
```

If the script prints a path, refer to it as `<makewiki_root>` and run physical verification:

```bash
python <makewiki_root>/scripts/run_toolkit.py verify . --format json
python <makewiki_root>/scripts/run_toolkit.py review . --lang en --lang zh-CN
```

### Step 2: Adversarial Audit Checklist

1. **Codebase Truth Audit (Zero Hallucinations)**:
   - Does every CLI command exist with the documented flags?
   - Does every config key exist in the actual code/configuration files?
   - Are all referenced file paths real?
2. **Code Block Parity (100% Match)**:
   - Code blocks, command lines, environment variable names, and JSON/YAML snippets must match character-for-character across all language versions.
3. **Enterprise Delivery Audit**:
   - `installation.md` includes clear prerequisites and installation verification / health check.
   - `configuration.md` includes types, defaults, and mandatory/optional status.
   - `troubleshooting.md` includes real error strings, root causes, and resolution steps.
4. **Diátaxis Developer Audit**:
   - `getting-started.md` provides an unbroken 5-minute tutorial to verify first run.
   - `usage/` provides clear task-oriented how-to guides.

### Step 3: In-Place Fix & Final Report

- If discrepancies are detected, fix the markdown files in place.
- Ensure all languages receive matching fixes for code blocks and facts.
