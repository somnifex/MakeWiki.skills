---
name: makewiki-scan
description: "Scan a project and output evidence summary with project sizing, complexity assessment (Tier S/M/L), recommended subagent budget, detected commands, config keys, dependencies, and enterprise delivery brief. Use when: user wants to understand a project before generating docs, or wants to inspect what MakeWiki detects."
version: "2.0.0"
argument-hint: "[--format json|human]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Glob Grep
---

# MakeWiki Scan - Project Evidence & Sizing Discovery

Scan the current project, assess complexity (Tier S / M / L), and report structured findings.

## Arguments

- `--format json|human`: Output format. Default: human.

## Execution

### Step 1: Bootstrap the home-scoped toolkit

Use the bundled bootstrap script. It prepares `<makewiki_root>` at `HOME/.makewiki` on Windows, macOS, and Linux. The launcher at `<makewiki_root>/scripts/run_toolkit.py` then bootstraps `<makewiki_root>/.venv`, preferring `uv` and falling back to `python -m venv`.

Run this bootstrap command:

```bash
python scripts/bootstrap_toolkit.py
```

If the script prints a path, refer to it as `<makewiki_root>` and run the sizing and scan tools:

```bash
python <makewiki_root>/scripts/run_toolkit.py sizing .
python <makewiki_root>/scripts/run_toolkit.py scan . --format json
```

### Step 2: Supplement with Multi-Perspective Analysis

Read manifest files, configs, entrypoints, and deployment configs to capture:
1. **Developer Perspective**: CLI commands, entrypoints, 5-minute quickstart requirements.
2. **Implementation Perspective**: Functions, AST arguments, unreleased features.
3. **Deployment & Enterprise Perspective**: Compatibility requirements, environment variables, health check commands, error logs.

### Step 3: Produce Project Brief

```yaml
project_brief:
  name: ""
  version: ""
  purpose: ""
  tier: "Tier S | Tier M | Tier L"
  subagent_budget: 4
  target_users: []
  project_type: ""

install_and_deploy:
  prerequisites: []
  commands: []
  health_check: ""

key_workflows:
  - title: ""
    user_goal: ""
    commands: []

config_semantics:
  - key: ""
    effect: ""
    source_file: ""
    default_value: ""

common_pitfalls_and_runbook:
  - symptom: ""
    cause: ""
    fix: ""
    log_path: ""

uncertainty_flags:
  - claim: ""
    reason: ""
```
