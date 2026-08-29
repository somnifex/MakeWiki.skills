# Task: Offline Static Wiki Compilation (离线静态网站编译)

## Overview

Compilation is Phase 5 of MakeWiki. It compiles Markdown documents into an offline single-file Single Page Application (SPA) HTML website without any external CDNs or server dependencies.

---

## 1. Static SPA Features

- **Zero-Dependency Single File**: All styles, scripts, search index, and doc contents embedded in `<output_dir>/site/index.html`.
- **Multilingual Dropdown Switcher**: Seamless language switching with state preservation.
- **Dark / Light Theme Toggle**: Client-side persisted theme selection.
- **Client-Side Full-Text Search**: Instant keyword indexing and match highlighting.
- **Hash-Based SPA Routing**: Clickable internal wiki links and back/forward browser navigation.
- **1-Click Code Copy**: Copy button attached to all code blocks.

---

## 2. Toolkit Compilation Command

```bash
# Compile wiki markdown directory into offline static HTML site
python scripts/run_toolkit.py build-site <output_dir> --theme auto
```