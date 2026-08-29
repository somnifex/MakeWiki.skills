# Enterprise Knowledge Base Sync Connectors

## 1. Atlassian Confluence

- Storage Format XHTML (`ac:structured-macro`).
- Code blocks (`code` macro), info/warning callouts (`info`, `warning` macros).
- Generates `sync/confluence/<lang>/manifest.json`.

## 2. Notion

- Notion Block API payload.
- Heading blocks (`heading_1`, `heading_2`), Callout blocks, Code blocks with language identifier.
- Generates `sync/notion/<lang>/manifest.json`.