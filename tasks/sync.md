# Task: Confluence & Notion Knowledge Base Sync (企业知识库同步)

## Overview

MakeWiki generates sync-ready payload bundles for Atlassian Confluence spaces and Notion workspace databases.

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
# Generate sync bundles for both Confluence and Notion
python scripts/run_toolkit.py sync <output_dir> --target all --lang zh-CN
```