---
name: makewiki-sync
description: "Prepare knowledge-base sync bundles (Atlassian Confluence Storage Format XHTML and Notion Block API JSON payloads) from generated makewiki documentation. Use when: user wants to ship documentation into Confluence or Notion. **Bundle preparation only — does NOT publish.**"
version: "3.0.0"
argument-hint: "[path-to-makewiki-dir] [--target all|confluence|notion] [--lang <code>]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Write Glob
---
# MakeWiki Sync - Knowledge Base Bundle Preparation (No Publishing)

Compile generated MakeWiki Markdown documentation into Confluence Storage
Format XHTML and Notion Block API JSON payloads **on disk**. The toolkit
authoritatively names this command `sync-bundle`; `sync` is retained as a
deprecated alias. The command **never** talks to Confluence or Notion
APIs — it only prepares import-ready bundles for a downstream publishing
step (planned as a future `--push` flag).

## Arguments

- `$ARGUMENTS`: Path to makewiki documentation directory (default: `./makewiki`).
- `--target all|confluence|notion`: Target platform (default: `all`).
- `--lang <code>`: Target language to sync (default: `zh-CN` or detected primary).

## Execution

### Step 1: Bootstrap the home-scoped toolkit

```bash
python scripts/bootstrap_toolkit.py
```

If the script prints a path, refer to it as `<makewiki_root>` and run the
sync tool:

```bash
python <makewiki_root>/scripts/run_toolkit.py sync-bundle ./makewiki --target all --lang zh-CN
```

### Step 2: Output Verification

The sync engine writes bundles to disk:
- `<makewiki_dir>/sync/confluence/<lang>/manifest.json` (Confluence Storage Format pages with macros)
- `<makewiki_dir>/sync/notion/<lang>/manifest.json` (Notion Block API payloads)

No external API calls are made. To publish the prepared bundles, use the
target platform's native importer (Confluence "Import from HTML", Notion
"Import" workflow) until a future `--push` option lands.
