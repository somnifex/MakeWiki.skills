# Task: HTML & EPUB Book Export (电子书单文件导出)

## Overview

Export is the final **mechanical** step in the MakeWiki pipeline. The LLM
Language Writers have already produced the prose; the L0–L5 verification and
Quality Gate have already accepted it; this task only packages the result
into portable single-file printable HTML and standard EPUB 2.0 electronic
books. **PDF is intentionally out of scope** — use the printable HTML
output and your browser's "Print to PDF" action if a PDF file is required.

---

## 1. Export Formats

1. **Single-File Printable HTML**:
   - Includes styled cover page, automated table of contents, and CSS `page-break-before: always` page breaks.
   - Built-in `Print to PDF` floating action button for browser-based PDF export.
   - Output path: `<output_dir>/export/documentation.<lang>.html`
2. **EPUB 2.0 E-Book**:
   - Valid standalone `.epub` zip archive containing `toc.ncx`, `content.opf`, and styled XHTML chapter files.
   - Compatible with Apple Books, Kindle, Calibre, and mobile readers.
   - Output path: `<output_dir>/export/documentation.<lang>.epub`

---

## 2. Toolkit Export Command

The authoritative command is `export`. `--format pdf` is rejected with an
explicit error.

```bash
# Export documentation in all formats for specified language
python scripts/run_toolkit.py export <output_dir> --format all --lang zh-CN
```

---

## 3. Rendered-Output Audit (mechanical, blocking)

Export bundles are verified, never trusted:

```bash
python scripts/run_toolkit.py verify-html <output_dir> --target export
```

Every exported chapter — including the XHTML files inside the EPUB archive —
is paired with its source Markdown and checked segment by segment for marker
leaks, heading parity, prose coverage, code-block/table/callout integrity, and
unrendered markdown residue. The check fails closed (exit 1 blocks delivery):
fix the Markdown source named by the finding, re-export, and re-run until
clean or the `agent.max_audit_rounds` budget is exhausted; an unresolved
failure is surfaced explicitly, never shipped (see `references/render_audit.md`).