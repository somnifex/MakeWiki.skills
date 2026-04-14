---
name: makewiki-review
description: "Run cross-language consistency review on existing makewiki documentation. Compares structured facts (commands, config keys, paths, versions) across all language versions to find inconsistencies. Use when: user has generated multilingual docs and wants to verify consistency."
argument-hint: "[--lang <code>...]"
allowed-tools: Bash(python *) Bash(uv run *) Read Glob Grep
---

# MakeWiki Review - Cross-Language Consistency Check

Review existing makewiki documentation for cross-language consistency.

## Arguments

Parse `$ARGUMENTS` for:
- `--lang <code>` (repeatable): Languages to review. Default: auto-detect from files.

## Execution

### Step 1: Run the toolkit reviewer

```bash
uv run makewiki review . $ARGUMENTS 2>/dev/null || python -m makewiki_skills.cli review . $ARGUMENTS
```

### Step 2: Manual deep review

Read the generated docs yourself and compare across languages:

1. **Page coverage** - Do all languages have the same set of pages?
2. **Command consistency** - Are all code blocks with commands identical across languages?
3. **Config key consistency** - Are the same config keys mentioned in all languages?
4. **File path consistency** - Do all languages reference the same paths?
5. **Version consistency** - Are version numbers the same?
6. **Information drift** - Does any language add or omit facts compared to others?
7. **Link correctness** - Do internal links use correct language-suffixed filenames?

### Step 3: Report

Report findings as a table:

| Issue Type | Value | Present In | Missing From | Severity |
|---|---|---|---|---|
| command | `make test` | en | zh-CN | critical |
| page | faq.md | en, zh-CN | ja | major |

Provide specific fix instructions for each issue.
