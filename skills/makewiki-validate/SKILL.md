---
name: makewiki-validate
description: "Validate existing makewiki output directory for Markdown quality: heading hierarchy, broken links, empty pages, and language alignment. Use when: user wants to check quality of generated documentation."
argument-hint: "[path-to-makewiki-dir]"
allowed-tools: Bash(python *) Read Glob Grep
---

# MakeWiki Validate - Output Quality Check

Validate the generated makewiki documentation.

## Arguments

`$ARGUMENTS` is the path to the makewiki output directory. Default: `./makewiki`

## Execution

### Step 1: Bootstrap the home-scoped toolkit

Use the bundled bootstrap script. It prepares `<makewiki_root>` at `HOME/.makewiki` on Windows, macOS, and Linux. The launcher at `<makewiki_root>/scripts/run_toolkit.py` then bootstraps `<makewiki_root>/.venv`, preferring `uv` and falling back to `python -m venv`.

Run this bootstrap command:

```bash
python scripts/bootstrap_toolkit.py
```

If the script prints a path, refer to it as `<makewiki_root>` and run the toolkit validator.

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
6. **Index file** - `index.md` links to all language versions
7. **Code blocks** - All command code blocks have a language tag (`bash`, `yaml`, etc.)

### Step 3: Report

Report: total files, errors, warnings. List each issue with file name and line number.
