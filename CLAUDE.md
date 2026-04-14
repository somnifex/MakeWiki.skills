# MakeWiki.skills


A set of skills for Claude Code / Codex that generate multilingual user-facing wiki documentation for any software project. Users invoke `/makewiki` inside their AI coding assistant; the skill handles scanning, generation, review, and validation.

## Project Overview

MakeWiki.skills provides 5 skills for AI coding assistants:
- `/makewiki` - Full documentation generation (scan -> generate -> review -> validate)
- `/makewiki-scan` - Scan a project and report evidence
- `/makewiki-review` - Cross-language consistency review
- `/makewiki-validate` - Output quality validation
- `/makewiki-init` - Generate default configuration

## Architecture

The project has two layers:

1. **Skills layer** (`skills/`) - Skill definitions (SKILL.md files) that drive the AI assistant to generate documentation. The AI is the generation engine, producing genuinely fluent text in each language.
2. **Toolkit layer** (`src/makewiki_skills/`) - Python supporting infrastructure for project scanning, evidence collection, semantic model building, cross-language review, and validation. Skills should enter through `scripts/run_toolkit.py`, which bootstraps the home-scoped toolkit environment at `HOME/.makewiki/.venv` (prefer `uv`, fall back to `python -m venv`) and then dispatches to `python -m makewiki_skills <command>`. The CLI is internal-only — the AI agent (via `/makewiki` skills) is the sole user interface.

## Key Design Principle

**Independent multi-language generation, NOT translation.** Each language is generated independently from a language-neutral understanding of the project. No language is used as a source text for another.

## Claude Code Note

When invoking `/makewiki` inside this repository, keep the workflow single-threaded. Do not use `Task`, subagents, or "parallel agents" for this skill. Generate, review, and validate in the main conversation.

## Build & Test

```bash
uv sync              # install dependencies
uv run pytest        # run tests (80 test cases)
```

## Code Conventions

- Python 3.11+, type-annotated
- Pydantic models for data structures
- All I/O through the toolkit layer (`src/makewiki_skills/toolkit/`)
- Jinja2 templates in `src/makewiki_skills/templates/`
- Tests in `tests/` using pytest
