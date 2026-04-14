---
name: makewiki-review
description: "Run cross-language consistency review on existing makewiki documentation. Compares structured facts (commands, config keys, paths, versions) and semantic meaning across all language versions to find inconsistencies. Use when: user has generated multilingual docs and wants to verify consistency."
argument-hint: "[--lang <code>...]"
allowed-tools: Bash(python *) Read Glob Grep
---

# MakeWiki Review - Cross-Language Consistency Check

Review existing makewiki documentation for cross-language consistency — both structural and semantic.

## Arguments

Parse `$ARGUMENTS` for:
- `--lang <code>` (repeatable): Languages to review. Default: auto-detect from files.

## Execution

### Step 1: Locate the repo-local launcher

Locate the MakeWiki skill repository. The launcher at `<makewiki_root>/scripts/run_toolkit.py` always bootstraps `<makewiki_root>/.venv`, preferring `uv` and falling back to `python -m venv`, then runs the internal toolkit inside that environment.

Use this locator:

```bash
python -c "import os, pathlib; cwd = pathlib.Path.cwd().resolve(); candidates = [cwd, *cwd.parents]; roots = [pathlib.Path(value) for value in (os.environ.get('CLAUDE_CONFIG_DIR'), os.environ.get('CODEX_HOME'), os.environ.get('OPENCODE_HOME')) if value]; home = pathlib.Path.home(); roots += [home / '.claude', home / '.codex', home / '.opencode', home / '.config' / 'claude', home / '.config' / 'codex', home / '.config' / 'opencode']; roots += [pathlib.Path(value) / name for value in (os.environ.get('APPDATA'), os.environ.get('LOCALAPPDATA')) if value for name in ('Claude', 'Codex', 'OpenCode')]; search_dirs = [candidate for root in roots if root.exists() for candidate in (root, root / 'plugins', root / 'skills') if candidate.exists()]; candidates.extend(path.parents[2] for search_dir in search_dirs for path in search_dir.rglob('__init__.py') if path.match('*/src/makewiki_skills/__init__.py')); root = next((path for path in candidates if (path / 'pyproject.toml').exists() and (path / 'scripts' / 'run_toolkit.py').exists() and (path / 'src' / 'makewiki_skills' / '__init__.py').exists()), None); print(root if root else 'NOT_FOUND')"
```

If the locator prints a path, refer to it as `<makewiki_root>` and run the toolkit reviewer.

Construct the command explicitly from the parsed arguments:

- If no `--lang` flags were provided, run `python <makewiki_root>/scripts/run_toolkit.py review .`
- If languages were provided, append them directly, for example `python <makewiki_root>/scripts/run_toolkit.py review . --lang en --lang zh-CN`

Example:

```bash
python <makewiki_root>/scripts/run_toolkit.py review . --lang en --lang zh-CN
```

If the locator prints `NOT_FOUND`, skip the launcher and perform the structural and semantic review manually.

### Step 2: Structural review

Read the generated docs yourself and compare across languages:

1. **Page coverage** - Do all languages have the same set of pages?
2. **Command consistency** - Are all code blocks with commands identical across languages?
3. **Config key consistency** - Are the same config keys mentioned in all languages?
4. **File path consistency** - Do all languages reference the same paths?
5. **Version consistency** - Are version numbers the same?
6. **Information drift** - Does any language add or omit facts compared to others?
7. **Link correctness** - Do internal links use correct language-suffixed filenames?

### Step 3: Semantic review (LLM analysis)

Go beyond structural comparison. For each page, read the corresponding versions in all languages and check:

**Hedging consistency:**
- For each uncertain claim that uses hedging ("may", "appears to", "suggests"), verify the hedge is preserved in all languages with equivalent epistemic force.
- A hedge removed in another language is a documentation accuracy failure.

**Semantic drift:**
- For each observable-behavior description ("After running X, you'll see Y"), verify all languages describe the same observable outcome.
- Different prose is acceptable; different observable outcomes are not.

**Cultural appropriateness:**
- Example values (personal names, dates, currencies) should be appropriate for each locale.
- Idiomatic expressions should be natural in each language, not literal translations.

### Step 4: Report

Report findings in two sections:

**Structural issues:**

| Issue Type | Value | Present In | Missing From | Severity |
|---|---|---|---|---|
| command | `make test` | en | zh-CN | critical |
| page | faq.md | en, zh-CN | ja | major |

**Semantic issues:**

| Review Type | File | Description | Languages Affected | Severity |
|---|---|---|---|---|
| hedging | config.md | Hedge "may support" removed in zh-CN | en, zh-CN | major |
| semantic_drift | usage.md | English says "dashboard", Chinese says "homepage" | en, zh-CN | minor |

Provide specific fix instructions for each issue.
