---
name: makewiki-review
description: "Verify and review existing makewiki documentation: checks factual accuracy against project source code, then compares structured facts and semantic meaning across all language versions. Use when: user has generated multilingual docs and wants to verify consistency and accuracy."
version: "0.7.0"
argument-hint: "[--lang <code>...]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Glob Grep
---

# MakeWiki Review - Cross-Language & Codebase Consistency Check

Review existing makewiki documentation for cross-language consistency and factual accuracy against the actual project codebase.

## Arguments

Parse `$ARGUMENTS` for:
- `--lang <code>` (repeatable): Languages to review. Default: auto-detect from files.

## Execution

### Step 1: Bootstrap the home-scoped toolkit

Use the bundled bootstrap script. It prepares `<makewiki_root>` at `HOME/.makewiki` on Windows, macOS, and Linux. The launcher at `<makewiki_root>/scripts/run_toolkit.py` then bootstraps `<makewiki_root>/.venv`, preferring `uv` and falling back to `python -m venv`.

Run this bootstrap command:

```bash
python scripts/bootstrap_toolkit.py
```

If the script prints a path, refer to it as `<makewiki_root>` and run the toolkit reviewer.

Construct the command explicitly from the parsed arguments:

- If no `--lang` flags were provided, run `python <makewiki_root>/scripts/run_toolkit.py review .`
- If languages were provided, append them directly, for example `python <makewiki_root>/scripts/run_toolkit.py review . --lang en --lang zh-CN`

Example:

```bash
python <makewiki_root>/scripts/run_toolkit.py review . --lang en --lang zh-CN
```

If the script prints `NOT_FOUND`, or if the launcher command fails, skip the launcher and perform the structural and semantic review manually.

### Step 2: Codebase verification (ground-truth check)

Before checking cross-language consistency, first verify that the documentation is **factually correct against the actual project source code**. A document that is perfectly consistent across 5 languages but contains a fabricated command is still wrong.

#### Step 2a: Run the toolkit mechanical check (if available)

```bash
python <makewiki_root>/scripts/run_toolkit.py verify . --format json
```

Parse the JSON output. Note any `verified: false` entries — these are claims in the docs that could not be confirmed against the project filesystem.

If the toolkit is unavailable, skip to Step 2b.

#### Step 2b: Agent-driven source code verification

For each of the following categories, **read the actual project files** and compare against what the documentation claims:

**Commands:**
- For every command in code blocks: find its definition (Makefile, package.json, pyproject.toml, CLI subcommand). Does it exist? Does it accept the documented flags?
- If a command doesn't exist → flag as critical error

**Configuration keys:**
- For every config key in configuration tables: open the real config file. Does the key exist? Is the default value correct?
- For non-obvious keys: read the source code that consumes them. Does the documented effect match the actual behavior?

**File paths:**
- For every file path referenced: confirm it exists on disk.

**Behavioral claims:**
- For claims like "starts on port 8080" or "generates a JSON file at...": trace the source code to verify.
- Pay attention to: default ports/URLs, output formats, environment variable names.

Flag every discrepancy with its severity:
- **Critical**: fabricated command, non-existent config key, wrong default value
- **Major**: incorrect behavioral description, outdated version constraint
- **Minor**: path exists but was renamed, config key is deprecated but still works

### Step 3: Structural review

Read the generated docs yourself and compare across languages:

1. **Page coverage** - Do all languages have the same set of pages?
2. **Command consistency** - Are all code blocks with commands identical across languages?
3. **Config key consistency** - Are the same config keys mentioned in all languages?
4. **File path consistency** - Do all languages reference the same paths?
5. **Version consistency** - Are version numbers the same?
6. **Information drift** - Does any language add or omit facts compared to others?
7. **Link correctness** - Do internal links use correct language-suffixed filenames?

### Step 4: Semantic review (LLM analysis)

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

### Step 5: Report

Report findings in three sections:

**Codebase verification issues:**

| Severity | Type | Claim | File | Detail |
|---|---|---|---|---|
| critical | command | `make deploy-prod` | usage.md | command not found in Makefile |
| major | config_key | `server.timeout` | configuration.md | key not found in config.yaml |
| minor | path | `./src/utils/` | README.md | directory renamed to `./src/lib/` |

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
