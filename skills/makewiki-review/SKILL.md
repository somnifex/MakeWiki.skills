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

### Step 1: Run the toolkit reviewer

```bash
python -m makewiki_skills review . $ARGUMENTS
```

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
