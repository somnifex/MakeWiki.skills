# Task: Offline Static Wiki Compilation (离线静态网站编译)

## Overview

Compilation is Phase 5 of MakeWiki. It compiles Markdown documents into an
offline single-file Single Page Application (SPA) HTML website without any
external CDNs or server dependencies. This step is fully **mechanical** —
the prose has already been authored by the LLM Language Writers and audited
through the Quality Gate; the site compiler only packages the result.

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

---

## 3. Rendered-Output Audit (mechanical, blocking)

`build-site` output is verified, never trusted:

```bash
python scripts/run_toolkit.py verify-html <output_dir> --target site
```

The audit extracts the per-language rendered documents embedded in the SPA and
re-pairs each one with its source Markdown segment by segment (preamble + H2
sections keyed by stable `<!-- makewiki:section=<id> -->` identity when
authored). Each pair is checked item by item for:

- `marker_leak` (critical) — `[[id:...]]` / `[[parity:ignore ...]]` / section
  markers, internal artifact paths, or writer frontmatter reaching a reader
- `heading_parity` (major) — every source section heading survives at the same
  level, and segment counts match
- `prose_coverage` (major) — every substantive source prose line appears in
  the rendered segment (normalized containment)
- `code_block_parity` / `table_integrity` / `callout_fidelity` — structural
  parity between source and artifact
- `fence_residue` / `link_residue` (major) — unrendered markdown syntax

This check **fails closed**: exit 1 means delivery is blocked. Fix the
Markdown source identified by the finding (never the HTML), rebuild, and
re-run until clean or the `agent.max_audit_rounds` budget is exhausted; an
unresolved failure is surfaced explicitly, never shipped. The Quality Gate's
four-state semantics are untouched — this is a post-render mechanical audit,
not a new verification layer (see `references/render_audit.md`).