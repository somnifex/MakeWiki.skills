---
name: makewiki-validate
description: "Validate existing makewiki output directory for Markdown quality: heading hierarchy, broken links, empty pages, and language alignment. Use when: user wants to check quality of generated documentation."
version: "2.0.0"
argument-hint: "[path-to-makewiki-dir]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Glob Grep
---

# MakeWiki Validate - Output Quality Check

Validate the generated makewiki documentation directory.

## Arguments

`$ARGUMENTS` is the path to the makewiki output directory. Default: `./makewiki`

## Execution

### Step 1: Bootstrap the home-scoped toolkit

```bash
python scripts/bootstrap_toolkit.py
```

If the script prints a path, refer to it as `<makewiki_root>` and run the toolkit validator:

```bash
python <makewiki_root>/scripts/run_toolkit.py validate ./makewiki
```

### Step 2: Quality Checks

1. **H1 heading** - Every page must have exactly one H1
2. **Heading hierarchy** - No skipped levels (H1 -> H3 without H2)
3. **Internal links** - All relative links point to existing files
4. **Empty pages** - No placeholder pages without body text
5. **Code blocks** - All code blocks specify language identifier
