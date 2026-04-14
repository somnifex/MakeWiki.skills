---
name: makewiki-scan
description: "Scan a project and output evidence summary with LLM analysis: detected project type, available commands, config keys, dependencies, file structure, and a structured project brief. Use when: user wants to understand a project before generating docs, or wants to see what MakeWiki would detect."
allowed-tools: Bash(python *) Read Glob Grep
---

# MakeWiki Scan - Project Evidence Discovery

Scan the current project and report what MakeWiki can detect, supplemented with your own analysis.

## Execution

### Step 1: Run the toolkit scanner with structured output

```bash
python -m makewiki_skills scan . --format json
```

If `--format json` is not available, fall back to:

```bash
python -m makewiki_skills scan .
```

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
