---
name: makewiki-scan
description: "Scan a project and emit the evidence summary: project sizing tier (S/M/L), recommended subagent budget, detected commands, config keys, dependencies, and enterprise delivery brief. Use when: user wants to understand a project before generating docs, or wants to inspect what MakeWiki detects. Output is facts-only — Python never interprets what the repository means."
version: "2.0.0"
argument-hint: "[--format json|human]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Glob Grep
---

# MakeWiki Scan - Project Evidence & Sizing Discovery

Scan the current project, assess complexity (Tier S / M / L), and report
structured findings. The Python toolkit returns **facts only**; the LLM
Skill layer is responsible for any interpretation, narrative, or "what does
this mean for the user" reasoning.

## Arguments

- `--format json|human`: Output format. Default: human.

## Execution

### Step 1: Bootstrap the home-scoped toolkit

```bash
python scripts/bootstrap_toolkit.py
```

If the script prints a path, refer to it as `<makewiki_root>` and run the
sizing and evidence tools (the toolkit authoritatively renames `scan` to
`evidence`; `scan` remains as a deprecated alias):

```bash
python <makewiki_root>/scripts/run_toolkit.py sizing .
python <makewiki_root>/scripts/run_toolkit.py evidence . --format json
python <makewiki_root>/scripts/run_toolkit.py coverage . --format json
```

`coverage` reports deterministic mechanical coverage — files discovered vs
inspected vs skipped (with reason) vs ignored, entrypoints/configs/tests/
manifests found, `uncovered_categories`, and `low_confidence_facts`. It is
pure bookkeeping: the LLM owns acting on the gaps it surfaces.

### Step 2: Supplement with LLM Multi-Perspective Analysis

The Python toolkit delivers deterministic facts (commands, config keys,
paths, versions, dependencies). The LLM Skill layer reads those facts via
the `evidence` JSON and adds:

1. **Developer Perspective**: CLI commands, entrypoints, 5-minute quickstart requirements.
2. **Implementation Perspective**: Functions, AST arguments, unreleased features.
3. **Deployment & Enterprise Perspective**: Compatibility requirements, environment variables, health check commands, error logs.

The multi-perspective analysis must **directly inspect the tree** (Glob /
Grep / Read / `ls` / `find` / `git ls-files`), not only read the Python
bundle, and must annotate the `coverage` report's `uncovered_categories` and
`low_confidence_facts` — resolving each gap or explicitly accepting it with a
written reason before continuing.

Per scout, return structured fields — `searched`, `evidence_found` (each with
`path:line` refs + a `low`/`medium`/`high` confidence), `unresolved`, and
`recommended_followup`. Then pass the **six pre-ReBattle coverage checks**
(`tasks/scan.md` §3): tests, CI / deployment, examples, nested packages,
runtime entrypoint, and "beyond README". A load-bearing `low`-confidence claim
or an unresolved area is closed by a targeted **Follow-up Scout** deep dive,
never by asking Python to guess.

Where the LLM cannot ground a claim in evidence, it leaves the field empty
and the corresponding Markdown slot renders `UNKNOWN` — never invent
install steps, commands, or env vars that the Python evidence did not
prove.

### Step 3: Produce Project Brief

The final project brief is **LLM-authored**, drawing only on facts surfaced
by `evidence` / `sizing`:

```yaml
project_brief:
  name: ""
  version: ""
  purpose: ""                       # LLM-written, grounded in evidence
  tier: "Tier S | Tier M | Tier L"
  subagent_budget: 4
  target_users: []
  project_type: ""

install_and_deploy:
  prerequisites: []
  commands: []                      # sourced from evidence; UNKNOWN if absent
  health_check: ""                  # UNKNOWN unless a Claim proves it

key_workflows:                      # LLM-synthesized from evidence
  - title: ""
    user_goal: ""
    commands: []

config_semantics:
  - key: ""
    effect: ""                      # LLM-written description of mechanical key
    source_file: ""
    default_value: ""

common_pitfalls_and_runbook:
  - symptom: ""
    cause: ""
    fix: ""
    log_path: ""

uncertainty_flags:
  - claim: ""
    reason: ""                      # every hedging reason the LLM invoked
```
