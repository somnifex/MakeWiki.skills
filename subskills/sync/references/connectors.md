# Enterprise Knowledge Base Sync Connectors

The sync connectors prepare **import-ready bundles only**. They never call
Confluence or Notion APIs; publishing is left to each platform's native
importer (Confluence "Import from HTML", Notion "Import") until a future
`--push` option lands. The authoritative toolkit command is `sync-bundle`
(the legacy `sync` alias is retained).

## 1. Atlassian Confluence

- Storage Format XHTML (`ac:structured-macro`).
- Code blocks (`code` macro), info/warning callouts (`info`, `warning` macros).
- Generates `sync/confluence/<lang>/manifest.json` for manual import.

## 2. Notion

- Notion Block API payload.
- Heading blocks (`heading_1`, `heading_2`), Callout blocks, Code blocks with language identifier.
- Generates `sync/notion/<lang>/manifest.json` for manual import.