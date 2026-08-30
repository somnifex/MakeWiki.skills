---
name: makewiki-export
description: "Compile generated makewiki Markdown documentation into single-file printable HTML and standard EPUB 2.0 electronic books. Use when: user wants to package documentation into portable single-file offline manuals or EPUB readers. (PDF export is intentionally not supported; use --format html|epub|all.)"
version: "2.0.0"
argument-hint: "[path-to-makewiki-dir] [--format all|html|epub] [--lang <code>]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Write Glob
---
# MakeWiki Export - HTML & EPUB Documentation Exporter

Compile generated MakeWiki Markdown documentation into single-file printable
HTML and standard EPUB 2.0 electronic books. This is a **mechanical** step —
the prose has already been authored by the LLM-driven Language Writers and
verified through the Quality Gate; the exporter only packages the result.

## Arguments

- `$ARGUMENTS`: Path to makewiki documentation directory (default: `./makewiki`).
- `--format all|html|epub`: Export format (default: `all`).
  - `html` produces a single-file printable HTML with cover page and `page-break-before` styles.
  - `epub` produces a standalone EPUB 2.0 archive with `toc.ncx` / `content.opf`.
  - `all` produces both.
- `--lang <code>`: Target language to export (default: `en`).

> **PDF is not supported.** `--format pdf` returns an explicit error from the
> toolkit. Use the printable HTML output and your browser's "Print to PDF"
> action if a PDF file is required.

## Execution

### Step 1: Bootstrap the home-scoped toolkit

```bash
python scripts/bootstrap_toolkit.py
```

If the script prints a path, refer to it as `<makewiki_root>` and run the
exporter:

```bash
python <makewiki_root>/scripts/run_toolkit.py export ./makewiki --format all --lang zh-CN
```

### Step 2: Output Verification

The exporter generates:
- `<makewiki_dir>/export/documentation.<lang>.html` (single-file printable HTML with cover page and page break styles)
- `<makewiki_dir>/export/documentation.<lang>.epub` (standard EPUB 2.0 archive with table of contents)
