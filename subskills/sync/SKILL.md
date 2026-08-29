---
name: makewiki-sync
description: "Synchronize or compile generated makewiki documentation into Atlassian Confluence Storage Format XHTML and Notion Block API JSON payloads. Use when: user wants to publish or sync wiki docs to enterprise knowledge bases."
version: "2.0.0"
argument-hint: "[path-to-makewiki-dir] [--target all|confluence|notion] [--lang <code>]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Write Glob
---
# MakeWiki Sync - Enterprise Knowledge Base Sync & Export

Compile generated makewiki Markdown documentation into Confluence Storage Format XHTML and Notion Block API JSON payloads.

## Arguments

- `$ARGUMENTS`: Path to makewiki documentation directory (default: `./makewiki`).
- `--target all|confluence|notion`: Target platform (default: `all`).
- `--lang <code>`: Target language to sync (default: `zh-CN` or detected primary).

## Execution

### Step 1: Bootstrap the home-scoped toolkit

```bash
python scripts/bootstrap_toolkit.py
```

If the script prints a path, refer to it as `<makewiki_root>` and run the sync tool:

```bash
python <makewiki_root>/scripts/run_toolkit.py sync ./makewiki --target all --lang zh-CN
```

### Step 2: Output Verification

The sync engine generates:
- `<makewiki_dir>/sync/confluence/<lang>/manifest.json` (Confluence XHTML pages with macros)
- `<makewiki_dir>/sync/notion/<lang>/manifest.json` (Notion Block API payloads)
