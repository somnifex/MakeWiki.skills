---
name: makewiki-export
description: "Export generated makewiki documentation into single-file PDF-ready HTML and standard EPUB 2.0 electronic books. Use when: user wants to package documentation into portable single-file offline manuals, printable books, or EPUB readers."
version: "2.0.0"
argument-hint: "[path-to-makewiki-dir] [--format all|html|epub] [--lang <code>]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Write Glob
---
# MakeWiki Export - PDF & EPUB Documentation Exporter

Export generated makewiki Markdown documentation into single-file PDF-ready HTML and standard EPUB e-books.

## Arguments

- `$ARGUMENTS`: Path to makewiki documentation directory (default: `./makewiki`).
- `--format all|html|epub`: Export format (default: `all`).
- `--lang <code>`: Target language to export (default: `zh-CN` or detected primary).

## Execution

### Step 1: Bootstrap the home-scoped toolkit

```bash
python scripts/bootstrap_toolkit.py
```

If the script prints a path, refer to it as `<makewiki_root>` and run the exporter:

```bash
python <makewiki_root>/scripts/run_toolkit.py export ./makewiki --format all --lang zh-CN
```

### Step 2: Output Verification

The exporter generates:
- `<makewiki_dir>/export/documentation.<lang>.html` (Single-file printable HTML with cover page and page break styles)
- `<makewiki_dir>/export/documentation.<lang>.epub` (Standard EPUB 2.0 archive with table of contents)
