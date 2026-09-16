---
name: makewiki-site
description: "Compile an existing MakeWiki markdown documentation directory into an offline, zero-dependency, responsive static website, driven by an LLM-authored SitePresentationPlan. Use when: a SitePresentationPlan exists and the user wants to build or rebuild static HTML wiki pages from generated makewiki markdown docs. Pure mechanical step — renders the plan, does not modify prose and never decides information architecture from filenames."
version: "3.3.1"
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

### Step 2: Rendered-Output Audit (mechanical, blocking)

The compiler produces `<makewiki_dir>/site/index.html`. Do not eyeball it —
audit it:

```bash
python <makewiki_root>/scripts/run_toolkit.py verify-html ./makewiki --target site
```

The audit re-pairs every embedded rendered document with its source Markdown,
segment by segment (preamble + H2 sections), and checks each pair for marker
leaks, heading parity, prose coverage, code-block/table/callout integrity, and
unrendered markdown residue. The command exits 0 clean and 1 on blocking
findings.

On blocking findings:
1. Locate the offending **Markdown source** from the finding's
   `language/document_id#section_id` location — never hand-edit the generated
   HTML.
2. Fix the source, rebuild (`build-site`), and re-run `verify-html`.
3. Repeat within the `agent.max_audit_rounds` budget; if the budget is
   exhausted, surface the failure explicitly instead of shipping.

Finally confirm that `index.html` opens directly in a browser without a local
web server.
