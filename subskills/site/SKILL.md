---
name: makewiki-site
description: "Compile an existing MakeWiki markdown documentation directory into an offline, zero-dependency, responsive static website with search, theme switching, and multilingual support. Use when: user wants to build or rebuild static HTML wiki pages from generated makewiki markdown docs."
version: "2.0.0"
argument-hint: "[path-to-makewiki-dir] [--theme <auto|light|dark>]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Write Glob
---
# MakeWiki Site - Offline Static Website Compiler

Compile an existing `makewiki/` directory of Markdown documents into a standalone, zero-dependency, offline-browseable static HTML website.

## Arguments

- `$ARGUMENTS` is the path to the makewiki documentation directory (default: `./makewiki`).
- Optional `--theme auto|light|dark` (default: `auto`).

## Execution

### Step 1: Bootstrap the home-scoped toolkit

```bash
python scripts/bootstrap_toolkit.py
```

If the script prints a path, refer to it as `<makewiki_root>` and run the site compiler:

```bash
python <makewiki_root>/scripts/run_toolkit.py build-site ./makewiki --theme auto
```

If a custom path is provided in arguments (e.g. `docs/wiki`), replace `./makewiki` with that exact path.

### Step 2: Output Confirmation

The compiler produces `<makewiki_dir>/site/index.html`.
Confirm that:
1. `index.html` was generated.
2. All language versions and categories are properly indexed.
3. The user can open `<makewiki_dir>/site/index.html` directly in their browser without a local web server.
