# Task: Confluence & Notion Knowledge Base Sync (企业知识库同步)

## Overview

The sync task prepares **bundle-only** payloads for Atlassian Confluence
spaces and Notion workspace databases. The authoritative command name is
`sync-bundle` (the legacy `sync` alias is retained). It writes import-ready
files to disk and **does not publish**. A future `--push` option is reserved
for actual API upload; until then, import the prepared bundles through each
platform's native importer (Confluence "Import from HTML", Notion "Import").

This task is mechanical: it converts the verified Markdown output into the
target platform's import format. All semantic decisions were already made
by the LLM Language Writers and audited through the Quality Gate.

---

## 1. Sync Targets

1. **Atlassian Confluence**:
   - Converts Markdown AST into Confluence Storage Format (XHTML with `ac:structured-macro` for code blocks, info, warning, and note callouts).
   - Generates import manifest: `<output_dir>/sync/confluence/<lang>/manifest.json`
2. **Notion**:
   - Converts Markdown AST into Notion Block API JSON payloads (Heading, Code, Callout, Bullet, and Table blocks).
   - Generates sync bundle: `<output_dir>/sync/notion/<lang>/manifest.json` and per-page payload JSON files.

---

## 2. Toolkit Sync Command

```bash
# Prepare sync bundles for both Confluence and Notion (no publishing)
python scripts/run_toolkit.py sync-bundle <output_dir> --target all --lang zh-CN
```