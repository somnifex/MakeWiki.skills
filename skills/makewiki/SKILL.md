---
name: makewiki
description: "Generate multilingual user-facing wiki documentation for the current project inside Claude Code or Codex. Scans project structure, collects evidence from configs/scripts/docs, builds a language-neutral semantic model, then independently generates documentation in each specified language with cross-language verification and code-evidence grounding. Use when: user asks to generate wiki, docs, documentation, or multilingual docs for a project."
argument-hint: "[--lang <code>...] [--output <dir>]"
allowed-tools: Bash(python *) Read Write Edit Glob Grep
---

# MakeWiki - Multilingual Wiki Documentation Generator

You are executing the MakeWiki skill. Your task is to generate high-quality, multilingual user-facing wiki documentation for a software project.

## Execution Mode

Run this skill **serially in the main Claude Code conversation**.

- Do **NOT** use the `Task` tool, subagents, agent teams, or any "parallel agents" workflow.
- Do **NOT** say that you will "parallelize across multiple agents."
- If Claude Code exposes agent-related tools anyway, ignore them for this skill and continue sequentially.
- If you want to speed up I/O, only parallelize ordinary reads or shell commands inside the current conversation. Do not delegate writing or review to helper agents.
- If multiple languages are requested, generate them one by one in the current thread from the same project understanding.

---

## Part A: Documentation Philosophy

You are writing a **user guide for an open-source project**, not an architecture document, not an API reference, not a sales pitch. Every sentence you write must answer one question: **"What can the user do with this, and how?"**

### A.1 - Understand First, Then Decide Structure

**Do NOT open the directory listing and start writing section-by-section.** Instead:

1. Read the project as if you are a new user who just found this repo.
2. Figure out: what does this project DO? Who would use it? What problem does it solve?
3. Identify the user's journey: install -> configure -> first run -> daily use -> troubleshoot.
4. THEN decide which pages to create and what goes on each page.

The document structure must emerge from your understanding of the project - not from the directory tree. A project with 50 source files might need 5 pages. A project with 3 files might also need 5 pages. The directory count is irrelevant.

### A.2 - Write Only Observable Behavior

Every statement must describe something the user can see, do, or experience.

Good:
- "Run `docker compose up` to start the service. The API will be available at `http://localhost:8080`."
- "After login, you'll see a dashboard with your recent projects listed."

Bad:
- "The system employs a modern microservices architecture."
- "The codebase follows clean architecture principles with clear separation of concerns."

**Test:** If the user cannot verify the claim by running a command, opening a URL, or looking at their screen - do not write it.

### A.3 - No Unfounded Praise

The following words are **banned by default**. Do not use them unless the project's own README, docs, or published benchmarks explicitly make the claim, AND you can cite the evidence:

- powerful
- robust
- flexible
- enterprise-grade
- high-performance
- elegant
- state-of-the-art
- cutting-edge
- seamless
- blazing-fast
- world-class
- best-in-class
- production-ready (unless the project explicitly claims this)

If the project README says "high-performance" and provides benchmarks - you may quote it with attribution. Otherwise, describe what the software does; let the user decide whether it's "powerful."

### A.4 - Tasks Over Directory Listings

Users do not care about:
- `src/services/`
- `internal/core/`
- `lib/utils/`
- "The project is organized into 12 modules..."

Users care about:
- How to install it
- How to run it
- How to configure it
- What commands are available
- How to fix errors

**Never** write a "Project Structure" section in user documentation. Directory listings belong in contributor/developer docs, not in user guides. If a file path is relevant to a user action (e.g., "Edit `config/settings.yaml` to change the port"), mention it inline - do not dedicate a section to listing directories.

### A.5 - Every Feature Must Be an Action

Do not write:
- "Supports file management and task execution."
- "Provides comprehensive logging capabilities."

Write:
- "You can upload files, create tasks, and export results from the web interface."
- "Run `app --verbose` to see detailed logs, or check `~/.app/logs/` for historical log files."

**Test:** If the sentence uses "supports" or "provides" but doesn't tell the user what to DO - rewrite it with a verb the user performs.

### A.6 - Presence Is Not Proof of Support

A directory named `oauth/` does not mean the project "supports OAuth." A file named `docker-compose.yml` does not mean the project "provides seamless container orchestration."

When evidence is indirect (directory names, file names, config keys that exist but aren't documented):

Good:
- "The repository contains OAuth-related configuration files, suggesting the project may support OAuth authentication. Refer to the project's release notes or issue tracker for current status."

Bad:
- "The project supports full OAuth 2.0 authentication with SSO integration."

**Hedging rules:**
- File/directory exists but no docs -> "The repository contains X, which suggests Y may be available"
- Config key exists but no explanation -> "The configuration file includes a `key` field; its exact behavior may depend on version"
- Code references a feature but README doesn't mention it -> "The codebase includes references to X; this feature may not be fully released"

When in doubt, under-claim. A user who discovers a feature is pleasantly surprised. A user who follows docs for a non-working feature is frustrated.

---

## Part B: Content Priorities

### B.1 - Required Sections (generate these by default)

In priority order:

1. **Project overview** - What it is, who it's for, what problem it solves. 2-4 sentences, no marketing.
2. **Installation** - Prerequisites, step-by-step commands, verification step.
3. **Getting started / Quick start** - Minimal steps from zero to "it works."
4. **Configuration** - Config files, environment variables, key options. Table format with key, description, default, required/optional.
5. **Basic usage** - Common tasks with concrete commands and expected output.
6. **Usage examples** - Real scenarios showing command sequences for typical workflows.
7. **FAQ** - Based on actual project issues, common questions, easy-to-miss details.
8. **Troubleshooting** - Symptom -> Cause -> Solution format. Include actual error messages when available.
9. **Platform notes** - Platform-specific behavior, OS-specific commands, compatibility notes (only if relevant).
10. **Documentation navigation / Index** - Links between all pages, language version links.

### B.2 - Banned Sections (do NOT generate by default)

The following are **forbidden** in user documentation unless the user explicitly requests a developer-facing mode:

- Architecture analysis or design pattern descriptions
- Internal module dependency graphs or call relationships
- Class diagrams, package diagrams, UML of any kind
- Source code walkthroughs from a maintainer's perspective
- Exhaustive directory listings with per-folder descriptions
- Contributor guidelines (this belongs in CONTRIBUTING.md, not in user docs)
- Technology stack summaries ("Built with React, Express, PostgreSQL, Redis...")

**Why:** These are useful for contributors, not for users. A user guide that opens with "The system uses a hexagonal architecture with ports and adapters" has failed before it starts.

If you discover the project is a library/framework where the "user" IS a developer (e.g., an SDK, a testing framework), adjust accordingly - but still focus on "what you can do with it" over "how it's built internally."

---

## Part C: Execution Steps

### Arguments

Parse `$ARGUMENTS` for:
- `--lang <code>` (repeatable): Language codes to generate. Default: `en zh-CN`
- `--output <dir>`: Output directory name. Default: `makewiki`

Supported language codes: `en`, `zh-CN`, `ja`, `de`, `fr` (and any BCP-47 code you can write fluently)

### Step 1: Locate the repo-local launcher

Locate the MakeWiki skill repository. The launcher at `<makewiki_root>/scripts/run_toolkit.py` always bootstraps `<makewiki_root>/.venv`, preferring `uv` and falling back to `python -m venv`, then runs the internal toolkit inside that environment.

Use this locator:

```bash
python -c "import os, pathlib; cwd = pathlib.Path.cwd().resolve(); candidates = [cwd, *cwd.parents]; roots = [pathlib.Path(value) for value in (os.environ.get('CLAUDE_CONFIG_DIR'), os.environ.get('CODEX_HOME'), os.environ.get('OPENCODE_HOME')) if value]; home = pathlib.Path.home(); roots += [home / '.claude', home / '.codex', home / '.opencode', home / '.config' / 'claude', home / '.config' / 'codex', home / '.config' / 'opencode']; roots += [pathlib.Path(value) / name for value in (os.environ.get('APPDATA'), os.environ.get('LOCALAPPDATA')) if value for name in ('Claude', 'Codex', 'OpenCode')]; search_dirs = [candidate for root in roots if root.exists() for candidate in (root, root / 'plugins', root / 'skills') if candidate.exists()]; candidates.extend(path.parents[2] for search_dir in search_dirs for path in search_dir.rglob('__init__.py') if path.match('*/src/makewiki_skills/__init__.py')); root = next((path for path in candidates if (path / 'pyproject.toml').exists() and (path / 'scripts' / 'run_toolkit.py').exists() and (path / 'src' / 'makewiki_skills' / '__init__.py').exists()), None); print(root if root else 'NOT_FOUND')"
```

If the locator prints a path, refer to it as `<makewiki_root>` and continue to Step 2.

If it prints `NOT_FOUND`, do **not** stop. Continue in manual mode:
- skip all `python <makewiki_root>/scripts/run_toolkit.py ...` commands
- gather evidence with `Read`, `Grep`, and ordinary file inspection instead
- make it explicit in your notes that the repo-local launcher was unavailable

### Step 2: Collect structured evidence

If the launcher is available, run the scan stage with structured JSON output:

```bash
python <makewiki_root>/scripts/run_toolkit.py scan . --format json
```

This produces a JSON evidence bundle containing every individual fact the scanner found — commands, config keys, file paths, version strings, config comments, CLI help text, and error messages — each with source file locations and confidence levels.

Parse the JSON output. Identify **evidence gaps** — areas where the toolkit could not extract enough information:
- Config keys with no `config_comment` facts → you need to read the config file to understand what they do
- Commands with no `cli_help` facts → you need to read the entry point source to understand usage
- Few or no `error_message` facts → check source code for error handling patterns

If the toolkit is unavailable, build the same evidence set manually from the project:
- commands from `README`, `Makefile`, task files, scripts, and entry points
- config keys from config files, `.env.example`, and comments
- file paths, version strings, and install steps from manifests and existing docs
- error messages from source code, tests, and troubleshooting notes

Then **read the project yourself**, targeting the gaps:

1. **Read the README** - What does this project claim to do? Who is the audience?
2. **Read config files the scanner flagged** - especially any with missing comment context
3. **Read build/task files** - `Makefile`, npm scripts, Taskfile - for commands the scanner might have missed
4. **Read example configs** - `.env.example`, `config.example.yaml` - what does the user need to configure?
5. **Read entry points** - main files, CLI entry points - what does running the program actually do?
6. **Read existing docs** - Are there already docs, tutorials, or usage examples?

### Step 3: Build project brief (required — do not skip)

Based on all evidence collected, produce a **project brief** as a YAML code block in the conversation. This is your authoritative reference for all subsequent document generation. Do NOT proceed to writing documentation until this brief is complete.

```yaml
project_brief:
  name: “”               # from toolkit detection / manifest
  version: “”            # from pyproject.toml / package.json / Cargo.toml
  purpose: “”            # ONE sentence: what does this tool do for the user?
  target_users:          # who uses this? (list, inferred from README + CLI design)
    - “”
  project_type: “”       # python-cli | node-react | rust-cli | go-cli | etc.

install_path:            # the exact sequence a new user runs
  prerequisites:
    - name: “”
      version_constraint: “”
  commands:
    - “”
  verify: “”             # command to confirm install worked

key_workflows:           # 3-7 things users actually DO with this tool
  - title: “”
    user_goal: “”        # finish the sentence: “so that I can...”
    commands:
      - “”
    config_keys: []      # which config keys affect this workflow
    expected_output: “”  # what the user sees after running these commands

config_semantics:        # for each non-obvious config key, what does it DO?
  - key: “”
    effect: “”           # user-visible effect of changing this key
    source_file: “”
    default_value: “”
    comment_text: “”     # verbatim comment from the config file, if any

common_pitfalls:         # things that go wrong and how to fix them
  - symptom: “”          # what the user sees (error message, unexpected behavior)
    cause: “”
    fix: “”
    evidence_source: “”  # where you found this (error message in code, README warning, etc.)

uncertainty_flags:       # things you're NOT sure about — be explicit
  - claim: “”
    reason: “”           # why you're uncertain
    evidence_gaps: “”    # what would resolve the uncertainty
```

**Rules for the project brief:**
- Every `purpose` statement must be verifiable from README or source entry point behavior.
- Every workflow `command` must appear in the evidence bundle OR in a file you personally read.
- `config_semantics` must only include keys where you found the comment or can infer the effect from usage context.
- `uncertainty_flags` is **mandatory**. If you have zero uncertainties, that itself is a red flag — re-examine your understanding. Every project has ambiguities.
- Do NOT populate fields with guesses. Leave them empty and add the gap to `uncertainty_flags` instead.

### Step 4: Decide document structure

Based on the project brief (NOT from the directory tree), decide which pages to create. The default set is:

| Base file | Purpose |
|---|---|
| `README.md` | Project overview, table of contents, quick start |
| `getting-started.md` | What it is, prerequisites, first run, verify |
| `installation.md` | Detailed installation, platform notes |
| `configuration.md` | Config files, env vars, options table |
| `usage/basic-usage.md` | Common tasks, commands, examples |
| `faq.md` | Common questions from issues/docs |
| `troubleshooting.md` | Error messages, symptoms, fixes |

You may **add** pages if the project warrants it (e.g., a `deployment.md` for a web service, a `plugins.md` for an extensible tool). You may **skip** pages if the project is too simple to warrant them (e.g., skip `configuration.md` if the tool has no configuration). Do not generate empty or near-empty pages.

### Step 5: Generate documentation for each language

Use the project brief from Step 3 as your authoritative source. The brief overrides any heuristic defaults for all interpretive decisions. The toolkit evidence (commands, config keys, paths) remains the ground truth for factual claims.

For each requested language, **independently** generate the full documentation set.

**Critical: You are NOT translating. You are writing each language version from scratch, from your understanding of the project.** A native Chinese speaker and a native English speaker reading the same project would emphasize different things, use different idioms, structure explanations differently. That is correct and expected.

Work through the requested languages **sequentially in the current conversation**. Do not spawn a helper agent per language.

**How the brief drives generation:**
- `project_brief.purpose` → project overview (not the README's full text verbatim)
- `key_workflows` → Usage and Getting Started sections
- `config_semantics` → config table descriptions (use `effect` and `comment_text`, not just key names)
- `common_pitfalls` → Troubleshooting section (real symptoms and fixes, not generic advice)
- `uncertainty_flags` → explicit hedging in output (every uncertain claim must be hedged)

#### Output structure

Create `<project_root>/<output_dir>/` with files per language:

| Base file | Default (en) | zh-CN | ja |
|---|---|---|---|
| README.md | README.md | README.zh-CN.md | README.ja.md |
| getting-started.md | getting-started.md | getting-started.zh-CN.md | getting-started.ja.md |
| installation.md | installation.md | installation.zh-CN.md | installation.ja.md |
| configuration.md | configuration.md | configuration.zh-CN.md | configuration.ja.md |
| usage/basic-usage.md | usage/basic-usage.md | usage/basic-usage.zh-CN.md | usage/basic-usage.ja.md |
| faq.md | faq.md | faq.zh-CN.md | faq.ja.md |
| troubleshooting.md | troubleshooting.md | troubleshooting.zh-CN.md | troubleshooting.ja.md |

Plus an `index.md` linking all language versions.

#### Language style guidelines

**English (en):** Clear, professional, concise. Active voice. Address reader as “you”. Short sentences. Lead each section with what the user DOES, not what the system IS.

**简体中文 (zh-CN):** 简洁专业的技术文档风格。使用主动语态，以”你”称呼用户。英文专有名词保留英文，中英文之间加空格。使用全角标点。先写用户能做什么，再解释原因。

**日本語 (ja):** 丁寧で正確な技術文書。です・ます調を使用。専門用語はカタカナまたは英語のまま使用。ユーザーの操作手順を中心に記述。

**Deutsch (de):** Klare, professionelle technische Dokumentation. Sie-Form verwenden. Englische Fachbegriffe beibehalten, wenn im Deutschen üblich. Handlungsorientiert schreiben.

**Français (fr):** Documentation technique claire et professionnelle. Vouvoiement. Les termes techniques anglais courants peuvent être conservés. Prioriser les actions utilisateur.

#### Writing checklist (apply to EVERY paragraph)

Before writing each paragraph, verify:

- [ ] Does this describe something the user can see, do, or experience?
- [ ] If I removed this paragraph, would the user miss anything actionable?
- [ ] Does every “supports X” have a concrete “you can do Y” follow-up?
- [ ] Are all commands verified against evidence (files, scripts, configs)?
- [ ] Am I hedging appropriately for uncertain capabilities?
- [ ] Am I free of banned marketing words?

### Step 6: Cross-language verification

If the launcher is available, run the structural review:

```bash
python <makewiki_root>/scripts/run_toolkit.py review . --lang en --lang zh-CN
```

Always manually verify:
1. **All languages have the same pages** - no missing pages
2. **Commands are identical** across all languages (code blocks must match exactly)
3. **Config keys are identical** - same keys, same defaults
4. **File paths are identical** - same paths referenced
5. **No information drift** - one language doesn't add unsupported facts

If inconsistencies are found, fix them.

#### Step 6b: Semantic consistency review (LLM analysis)

After the structural check above, perform a **semantic pass** across all language versions:

**Hedging consistency check:**
For each uncertain claim in one language that uses hedging language (“may”, “appears to”, “suggests”, “the repository contains X which suggests Y”):
1. Find the equivalent passage in each other language
2. Verify the hedge is preserved with equivalent epistemic force
3. A hedge removed in translation is a documentation accuracy failure — fix it

**Semantic drift check:**
For each observable-behavior description (e.g., “After running the command, you'll see X”):
1. Find the equivalent in other languages
2. Verify the described observable outcome matches
3. Different prose is acceptable; different observable outcomes are not

**Cultural appropriateness check:**
For any examples that use:
- Personal names as example values → are they culturally appropriate for the locale?
- Currency or date format examples → do they match the locale's conventions?
- Humor or idiomatic expressions → are they natural in the target language?

### Step 7: Validate output

If the launcher is available, run:

```bash
python <makewiki_root>/scripts/run_toolkit.py validate <output_dir>
```

Then check manually:
- Every page has a proper H1 heading
- No broken internal links
- No empty pages
- Heading hierarchy is correct (no skipped levels)

### Step 8: Report

After completion, report:
- Number of files generated per language
- Cross-language consistency score (structural + semantic)
- Any grounding warnings (claims without strong evidence)
- Any validation issues
- Any sections you chose to skip and why
- Summary of uncertainty flags from the project brief

---

## Part D: Hard Rules

These are non-negotiable. Violating any of them is a failure condition.

1. **NEVER generate one language then translate to others.** Each language must be written independently from your project understanding.
2. **NEVER present guesses as facts.** If you can't verify a claim from project evidence, hedge explicitly.
3. **NEVER fabricate commands, config keys, or paths** that don't exist in the project.
4. **NEVER write architecture analysis, module relationship diagrams, or source code walkthroughs** in user documentation.
5. **NEVER open with marketing language.** No "Welcome to X, a powerful and flexible..." - just state what the project does.
6. **NEVER list directories as a documentation strategy.** If you find yourself writing "The `src/` directory contains...", stop and rewrite as a user task.
7. **ALWAYS use correct language-suffixed filenames** for cross-page links.
8. **ALWAYS keep code blocks, commands, and config keys identical** across all languages - only the prose differs.
9. **ALWAYS describe features as user actions** - "You can..." not "The system supports..."
10. **Output directory MUST be `<project_root>/makewiki/`** unless the user specifies otherwise.
11. **NEVER use `Task`, subagents, or multi-agent orchestration for this skill.** Complete the workflow in the main conversation.
