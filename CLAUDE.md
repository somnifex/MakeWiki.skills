# MakeWiki.skills


This is a Claude Code plugin that generates multilingual user-facing wiki documentation for any software project.

## Project Overview

MakeWiki.skills provides 5 skills:
- `/makewiki` - Full documentation generation (scan -> generate -> review -> validate)
- `/makewiki-scan` - Scan a project and report evidence
- `/makewiki-review` - Cross-language consistency review
- `/makewiki-validate` - Output quality validation
- `/makewiki-init` - Generate default configuration

## Architecture

The project has two layers:

1. **Skills layer** (`skills/`) - Skill definitions (SKILL.md files) that instruct the AI assistant to generate documentation. The AI is the generation engine, producing genuinely fluent text in each language.
2. **Toolkit layer** (`src/makewiki_skills/`) - Python supporting infrastructure for project scanning, evidence collection, semantic model building, cross-language review, and validation. The CLI (`makewiki`) exposes these as commands.

## Key Design Principle

**Independent multi-language generation, NOT translation.** Each language is generated independently from a language-neutral understanding of the project. No language is used as a source text for another.

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