# MakeWiki.skills

This repository contains the skills and Python toolkit behind `/makewiki`.

## What is in the repo

- `skills/`: skill definitions and bootstrap helpers
- `src/makewiki_skills/`: scanning, modeling, generation, review, and validation code
- `tests/`: automated test coverage

## Available skills

- `/makewiki` - full documentation flow (`scan -> generate -> review -> validate`)
- `/makewiki-scan` - inspect project evidence
- `/makewiki-review` - compare language versions
- `/makewiki-validate` - validate generated output
- `/makewiki-init` - create a default config file

## Working notes

- Generate each language independently. Do not translate from another generated page.
- Keep the workflow in the main conversation when working inside this repo. Do not use subagents or parallel-agent flows for the MakeWiki skill itself.
- Treat `scripts/run_toolkit.py` and `python -m makewiki_skills <command>` as internal plumbing, not end-user commands.

## Build & Test

```bash
uv sync
uv run pytest
```

## Code conventions

- Python 3.11+ with type annotations
- Pydantic models for structured data
- All I/O goes through `src/makewiki_skills/toolkit/`
- Jinja2 templates live in `src/makewiki_skills/templates/`
- Tests use pytest