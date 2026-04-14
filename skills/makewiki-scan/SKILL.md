---
name: makewiki-scan
description: "Scan a project and output evidence summary with LLM analysis: detected project type, available commands, config keys, dependencies, file structure, and a structured project brief. Use when: user wants to understand a project before generating docs, or wants to see what MakeWiki would detect."
allowed-tools: Bash(python *) Read Glob Grep
---

# MakeWiki Scan - Project Evidence Discovery

Scan the current project and report what MakeWiki can detect, supplemented with your own analysis.

## Execution

### Step 1: Locate the repo-local launcher

Locate the MakeWiki skill repository. The launcher at `<makewiki_root>/scripts/run_toolkit.py` always bootstraps `<makewiki_root>/.venv`, preferring `uv` and falling back to `python -m venv`, then runs the internal toolkit inside that environment.

Use this locator:

```bash
python -c "import os, pathlib; cwd = pathlib.Path.cwd().resolve(); candidates = [cwd, *cwd.parents]; roots = [pathlib.Path(value) for value in (os.environ.get('CLAUDE_CONFIG_DIR'), os.environ.get('CODEX_HOME'), os.environ.get('OPENCODE_HOME')) if value]; home = pathlib.Path.home(); roots += [home / '.claude', home / '.codex', home / '.opencode', home / '.config' / 'claude', home / '.config' / 'codex', home / '.config' / 'opencode']; roots += [pathlib.Path(value) / name for value in (os.environ.get('APPDATA'), os.environ.get('LOCALAPPDATA')) if value for name in ('Claude', 'Codex', 'OpenCode')]; search_dirs = [candidate for root in roots if root.exists() for candidate in (root, root / 'plugins', root / 'skills') if candidate.exists()]; candidates.extend(path.parents[2] for search_dir in search_dirs for path in search_dir.rglob('__init__.py') if path.match('*/src/makewiki_skills/__init__.py')); root = next((path for path in candidates if (path / 'pyproject.toml').exists() and (path / 'scripts' / 'run_toolkit.py').exists() and (path / 'src' / 'makewiki_skills' / '__init__.py').exists()), None); print(root if root else 'NOT_FOUND')"
```

If the locator prints a path, refer to it as `<makewiki_root>` and run the toolkit scanner with structured output:

```bash
python <makewiki_root>/scripts/run_toolkit.py scan . --format json
```

If `--format json` is not available, fall back to:

```bash
python <makewiki_root>/scripts/run_toolkit.py scan .
```

If the locator prints `NOT_FOUND`, skip the launcher and perform the scan manually from project files.

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
