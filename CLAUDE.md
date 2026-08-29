# MakeWiki.skills v2

This repository contains the multi-agent skills and Python toolkit behind `/makewiki`.

## What is in the repo

- `skills/`: skill definitions (`makewiki`, `makewiki-site`, `makewiki-scan`, `makewiki-review`, `makewiki-validate`, `makewiki-init`)
- `src/makewiki_skills/`: scanning, ReBattle modeling, site compilation, generation, review, and verification
- `tests/`: automated unit and integration tests

## Available skills

- `/makewiki` - full autonomous multi-agent flow (`sizing -> scout -> rebattle -> parallel writers -> review -> site compile`)
- `/makewiki-site` - build offline static website from generated markdown
- `export` - compile markdown into printable PDF-ready HTML & EPUB e-books
- `sync` - generate Confluence Storage XML and Notion Block API sync payloads
- `/makewiki-scan` - inspect project evidence and assess sizing tier
- `/makewiki-review` - compare language versions and verify codebase truth
- `/makewiki-validate` - validate markdown structure and links
- `/makewiki-init` - generate default `makewiki.config.yaml`

## Working notes

- Autonomous execution: Complete all phases end-to-end without pausing to ask intermediate questions.
- Subagent budget: Tier S (1-2 agents), Tier M (3-5 agents), Tier L (5-10 agents max).
- ReBattle cross-examination for fact validation before writing.
- Natural human engineer tone: Strictly avoid AI clichés ("不是而是", "收敛", "这是", trailing colons).
- Generate each language independently from the semantic model. Do not machine-translate.
- Code blocks must match 100% across all languages.
- Ephemeral execution: Keep environments clean and remove temporary artifacts.

## Build & Test

```bash
uv sync --all-extras
uv run pytest --basetemp=.pytest_temp
```