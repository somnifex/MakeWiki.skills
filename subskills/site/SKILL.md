---
name: makewiki-site
description: "Compile an existing MakeWiki markdown documentation directory into an offline, zero-dependency, responsive static website, driven by an LLM-authored SitePresentationPlan. Use when: a SitePresentationPlan exists and the user wants to build or rebuild static HTML wiki pages from generated makewiki markdown docs. Pure mechanical step — renders the plan, does not modify prose and never decides information architecture from filenames."
version: "3.0.0"
argument-hint: "[path-to-makewiki-dir] [--plan <site_presentation.json>] [--theme <auto|light|dark>]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Write Glob
---
# MakeWiki Site - Offline Static Website Compiler (plan-driven)

Compile an existing `makewiki/` directory of Markdown documents into a
standalone, zero-dependency, offline-browseable static HTML website. This is
the final mechanical step in the MakeWiki pipeline: the **Main Agent / Site
Designer LLM** has already authored a `SitePresentationPlan` that declares the
site's Information Architecture (project title, navigation groups, page
ordering, routes, hierarchy, localized titles, visual direction) from the
SemanticModel and the document collection. The site compiler **only packages
that plan** — it never re-derives navigation, page roles, ordering, or
hierarchy from filenames or keywords.

## The SitePresentationPlan (LLM-authored, required)

The plan is the single IA authority. It is authored by the Main Agent (or a
Site Designer subagent it dispatches) and written to
`<wiki_dir>/site_presentation.json` (or `.yaml`). Its required fields include:

- `project_title`, `project_description` — site identity
- `navigation` — ordered nav items, each with `document_id`, `route`, `title`
  (+ per-language `titles`), `nav_group`, `ordering`, and optional `children`
- `languages`, `default_language`
- `visual` — theme, search toggle, accent color, brand label

Without a plan, the site build is left **pending/unavailable** and exits
cleanly; Python never fabricates an Information Architecture from filenames.

## Arguments

- `$ARGUMENTS` is the path to the makewiki documentation directory (default: `./makewiki`).
- Optional `--plan <path>` (default: `<wiki_dir>/site_presentation.json|.yaml`).
- Optional `--theme auto|light|dark` overrides the plan's visual theme.

## Execution

### Step 1: Bootstrap the home-scoped toolkit

```bash
python scripts/bootstrap_toolkit.py
```

If the script prints a path, refer to it as `<makewiki_root>` and run the
site compiler:

```bash
python <makewiki_root>/scripts/run_toolkit.py build-site ./makewiki --theme auto
```

The Main Agent must have authored `./makewiki/site_presentation.json` first; if
it is absent, the build stays pending (see above).

### Step 2: Output Confirmation

The compiler produces `<makewiki_dir>/site/index.html`.
Confirm that:
1. `index.html` was generated (requires the plan).
2. The rendered navigation matches the plan's groups, ordering, and hierarchy.
3. The user can open `<makewiki_dir>/site/index.html` directly in their browser without a local web server.
