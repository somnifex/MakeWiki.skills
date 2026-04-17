---
name: makewiki-validate
description: "Validate existing makewiki output directory for Markdown quality: heading hierarchy, broken links, empty pages, and language alignment. Use when: user wants to check quality of generated documentation."
version: "0.6.2"
argument-hint: "[path-to-makewiki-dir]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py *) Bash(python */scripts/run_toolkit.py *) Read Glob Grep
---

# MakeWiki Validate - Output Quality Check

Validate the generated makewiki documentation.

## Arguments

`$ARGUMENTS` is the path to the makewiki output directory. Default: `./makewiki`

## Execution

### Step 1: Bootstrap the home-scoped toolkit

Use the bundled bootstrap script. It inspects `<makewiki_root>` at `HOME/.makewiki`, reports whether the bundled skill checkout is newer than the installed toolkit, and can sync it on demand. The launcher at `<makewiki_root>/scripts/run_toolkit.py` then bootstraps `<makewiki_root>/.venv`, preferring `uv` and falling back to `python -m venv`.

Run this status command first:

```bash
python scripts/bootstrap_toolkit.py status --format json
```

Use `toolkit_root` from the JSON as `<makewiki_root>`.

- If `update_available` is `true`, pause and ask the user whether to update to the bundled version before continuing.
- If the user says yes, run `python scripts/bootstrap_toolkit.py update` and keep using the printed path as `<makewiki_root>`.
- If the user says no, keep using the existing `<makewiki_root>` from the JSON status output.
- If `status` is `missing`, run `python scripts/bootstrap_toolkit.py` to install the toolkit and use the printed path as `<makewiki_root>`.

After parsing `$ARGUMENTS`, build the command explicitly:

- If no path was provided, run `python <makewiki_root>/scripts/run_toolkit.py validate ./makewiki`
- If a path was provided, replace `./makewiki` with that exact path

Example default command:

```bash
python <makewiki_root>/scripts/run_toolkit.py validate ./makewiki
```

If the script prints `NOT_FOUND`, or if the launcher command fails, skip the launcher and perform the manual quality checks below.

### Step 2: Manual quality checks

Read the generated files and check:

1. **H1 heading** - Every page must have exactly one H1
2. **Heading hierarchy** - No skipped levels (H1 -> H3 without H2)
3. **Internal links** - All `[text](file.md)` links point to existing files
4. **Empty pages** - No pages with only a heading and no content
5. **Language suffix consistency** - All non-default language files use correct suffixes
6. **Entry page** - `README.md` links to the other generated pages, and should link to other language README files when they exist
7. **Code blocks** - All command code blocks have a language tag (`bash`, `yaml`, etc.)
8. **Page families** - `commands.md`, `modules/`, `workflows/`, and `integrations/` should be internally consistent when present

### Step 3: Report

Report: total files, errors, warnings. List each issue with file name and line number.
