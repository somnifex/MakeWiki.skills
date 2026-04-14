---
name: makewiki-scan
description: "Scan a project and output evidence summary: detected project type, available commands, config keys, dependencies, and file structure. Use when: user wants to understand a project before generating docs, or wants to see what MakeWiki would detect."
allowed-tools: Bash(python *) Bash(uv run *) Read Glob Grep
---

# MakeWiki Scan - Project Evidence Discovery

Scan the current project and report what MakeWiki can detect.

## Execution

### Step 1: Run the toolkit scanner

```bash
uv run makewiki scan . 2>/dev/null || python -m makewiki_skills.cli scan .
```

### Step 2: Supplement with your own analysis

Also read the project yourself:

1. Read manifest files (`pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`)
2. Read build files (`Makefile`, scripts)
3. Read existing docs (`README.md`, `docs/`)
4. Scan directory structure

### Step 3: Report findings

Report a structured summary:

- **Project type** (Python CLI, Node React, Rust, Go, etc.)
- **Project name and version**
- **Detected commands** (from Makefile, package.json scripts, pyproject scripts)
- **Configuration files** found and their key paths
- **Environment variables** from .env.example files
- **Existing documentation** assets
- **Suggested languages** based on existing docs
- **Evidence confidence** for key claims

Flag anything uncertain with explicit hedging.
