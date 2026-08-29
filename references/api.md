# Internal Toolkit CLI API Reference

All toolkit commands are dispatched via `python scripts/run_toolkit.py <command>`:

| Command      | Arguments / Flags                             | Description                                         |
| ------------ | --------------------------------------------- | --------------------------------------------------- |
| `sizing`     | `<target> [--format json\                     | human]`                                             | Estimate project tier (S/M/L) and subagent budget |
| `scan`       | `<target> [--format json\                     | human]`                                             | Extract structured evidence facts |
| `build-site` | `<makewiki_dir> [--theme auto\                | light\                                              | dark]` | Compile Markdown docs into offline SPA HTML site |
| `export`     | `<makewiki_dir> [--format all\                | html\                                               | epub] [--lang <lang>]` | Export single-file printable HTML and EPUB e-books |
| `sync`       | `<makewiki_dir> [--target all\                | confluence\                                         | notion] [--lang <lang>]` | Build Atlassian Confluence & Notion import bundles |
| `verify`     | `<target> [--wiki-dir <dir>] [--format json]` | Mechanical ground-truth validation against codebase |
| `review`     | `<target> [--lang <lang>...]`                 | Cross-language parity and consistency reviewer      |
| `validate`   | `<makewiki_dir>`                              | Heading hierarchy, link, and format validator       |