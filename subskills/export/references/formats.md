# Export Format Technical Details

The exporter is a **mechanical** package step. The prose has already been
authored by the LLM Language Writers and verified through the L0–L5 +
Quality Gate pipeline; the exporter only wraps that verified content into
the formats below.

## 1. Single-File HTML

- Standalone CSS styling for print and screen view.
- CSS `@media print` with automated chapter page breaks.
- Embedded navigation and table of contents.
- Suitable for browser "Print to PDF" if a PDF file is required — MakeWiki

  intentionally does not produce native PDF.

## 2. EPUB 2.0 Archive

- Standard Open Packaging Format (`content.opf`).
- Navigation Control file (`toc.ncx`).
- XHTML chapter content files.
- Compatible with Apple Books, Kindle, Calibre, and mobile readers.