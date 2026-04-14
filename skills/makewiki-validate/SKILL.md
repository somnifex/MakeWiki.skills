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

### Step 1: Locate the repo-local launcher

Locate the MakeWiki skill repository. The launcher at `<makewiki_root>/scripts/run_toolkit.py` always bootstraps `<makewiki_root>/.venv`, preferring `uv` and falling back to `python -m venv`, then runs the internal toolkit inside that environment.

Use this locator:

```bash
python -c "import os, pathlib; cwd = pathlib.Path.cwd().resolve(); candidates = [cwd, *cwd.parents]; roots = [pathlib.Path(value) for value in (os.environ.get('CLAUDE_CONFIG_DIR'), os.environ.get('CODEX_HOME'), os.environ.get('OPENCODE_HOME')) if value]; home = pathlib.Path.home(); roots += [home / '.claude', home / '.codex', home / '.opencode', home / '.config' / 'claude', home / '.config' / 'codex', home / '.config' / 'opencode']; roots += [pathlib.Path(value) / name for value in (os.environ.get('APPDATA'), os.environ.get('LOCALAPPDATA')) if value for name in ('Claude', 'Codex', 'OpenCode')]; search_dirs = [candidate for root in roots if root.exists() for candidate in (root, root / 'plugins', root / 'skills') if candidate.exists()]; candidates.extend(path.parents[2] for search_dir in search_dirs for path in search_dir.rglob('__init__.py') if path.match('*/src/makewiki_skills/__init__.py')); root = next((path for path in candidates if (path / 'pyproject.toml').exists() and (path / 'scripts' / 'run_toolkit.py').exists() and (path / 'src' / 'makewiki_skills' / '__init__.py').exists()), None); print(root if root else 'NOT_FOUND')"
```

If the locator prints a path, refer to it as `<makewiki_root>` and run the toolkit validator.

After parsing `$ARGUMENTS`, build the command explicitly:

- If no path was provided, run `python <makewiki_root>/scripts/run_toolkit.py validate ./makewiki`
- If a path was provided, replace `./makewiki` with that exact path

Example default command:

```bash
python <makewiki_root>/scripts/run_toolkit.py validate ./makewiki
```

If the locator prints `NOT_FOUND`, skip the launcher and perform the manual quality checks below.

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
