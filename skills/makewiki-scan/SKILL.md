---
name: makewiki-scan
description: "Scan a project and output evidence summary with LLM analysis: detected project type, available commands, config keys, dependencies, file structure, and a structured project brief. Use when: user wants to understand a project before generating docs, or wants to see what MakeWiki would detect."
version: "0.7.5"
argument-hint: "[--format json|human]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Glob Grep
---

# MakeWiki Scan - Project Evidence Discovery

Scan the current project and report what MakeWiki can detect, supplemented with your own analysis.

## Arguments

Parse `$ARGUMENTS` for:
- `--format json|human`: Output format. Default: try json, fall back to human.

## Execution

### Step 1: Bootstrap the home-scoped toolkit

Use the bundled bootstrap script. It prepares `<makewiki_root>` at `HOME/.makewiki` on Windows, macOS, and Linux. The launcher at `<makewiki_root>/scripts/run_toolkit.py` then bootstraps `<makewiki_root>/.venv`, preferring `uv` and falling back to `python -m venv`.

Run this bootstrap command:

```bash
python scripts/bootstrap_toolkit.py
```

If the script prints a path, refer to it as `<makewiki_root>` and run the toolkit scanner with structured output:

```bash
python <makewiki_root>/scripts/run_toolkit.py scan . --format json
```

If `--format json` is not available, fall back to:

```bash
python <makewiki_root>/scripts/run_toolkit.py scan .
```

If the script prints `NOT_FOUND`, or if the launcher command fails, skip the launcher and perform the scan manually from project files.

### Step 2: Supplement with your own analysis

Read the project yourself to fill evidence gaps:

1. Read manifest files (`pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`)
2. Read build files (`Makefile`, scripts)
3. Read existing docs (`README.md`, `docs/`)
4. Read example configs (`.env.example`, `config.example.yaml`)
5. Read entry points — what does running the program actually do?

### Step 3: Build project brief

Produce a structured project brief as a YAML code block:

```yaml
project_brief:
  name: ""
  version: ""
  purpose: ""            # ONE sentence
  target_users: []
  project_type: ""

install_path:
  prerequisites: []
  commands: []
  verify: ""

key_workflows:
  - title: ""
    user_goal: ""
    commands: []

config_semantics:
  - key: ""
    effect: ""
    source_file: ""

common_pitfalls:
  - symptom: ""
    cause: ""
    fix: ""

uncertainty_flags:
  - claim: ""
    reason: ""
```

### Step 4: Report findings

Report a structured summary covering:

- **Project type** (Python CLI, Node React, Rust, Go, etc.)
- **Project name and version**
- **Detected commands** (from Makefile, package.json scripts, pyproject scripts, source analysis)
- **Configuration files** found and their key paths with descriptions
- **Environment variables** from .env.example files
- **Existing documentation** assets
- **Suggested languages** based on existing docs
- **Key workflows** identified (what users actually do with this tool)
- **Common pitfalls** (error patterns found in source code)
- **Evidence confidence** for key claims
- **Uncertainty flags** — what you could not determine

Flag anything uncertain with explicit hedging.
