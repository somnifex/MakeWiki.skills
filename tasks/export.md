# Task: PDF & EPUB Book Export (电子书单文件导出)

## Overview

MakeWiki supports exporting documentation suites into portable single-file PDF-ready HTML documents and standard EPUB 2.0 electronic books.

---

## 1. Export Formats

1. **PDF-Ready Single-Page HTML**:
   - Includes styled cover page, automated table of contents, and CSS `page-break-before: always` page breaks.
   - Built-in `Print to PDF` floating action button.
   - Output path: `<output_dir>/export/documentation.<lang>.html`
2. **EPUB 2.0 E-Book**:
   - Valid standalone `.epub` zip archive containing `toc.ncx`, `content.opf`, and styled XHTML chapter files.
   - Compatible with Apple Books, Kindle, Calibre, and mobile readers.
   - Output path: `<output_dir>/export/documentation.<lang>.epub`

---

## 2. Toolkit Export Command

```bash
# Export documentation in all formats for specified language
python scripts/run_toolkit.py export <output_dir> --format all --lang zh-CN
```