# MakeWiki.skills

This repository contains the skills and Python toolkit behind `/makewiki`.

## What is in the repo

- `skills/`: skill definitions and bootstrap helpers
- `src/makewiki_skills/`: objective evidence, orchestration state, assembly, review, and validation code
- `tests/`: automated test coverage

## Available skills

- `/makewiki` - artifact-first orchestration flow (`prepare -> status loop -> assemble -> verify/review/validate`)
- `/makewiki-scan` - inspect project evidence
- `/makewiki-review` - compare language versions
- `/makewiki-validate` - validate generated output
- `/makewiki-init` - create a default config file

Internal child skills:

- `makewiki-llm-scan`
- `makewiki-surface-card`
- `makewiki-semantic-root`
- `makewiki-module-brief`
- `makewiki-workflow-brief`
- `makewiki-page-plan`
- `makewiki-page-write`
- `makewiki-page-repair`

## Working notes

- Generate each language independently. Do not translate from another generated page.
- Keep the workflow in the main conversation when working inside this repo. Do not use subagents or parallel-agent flows for the MakeWiki skill itself.
- Treat `scripts/run_toolkit.py` and `python -m makewiki_skills <command>` as internal plumbing, not end-user commands.
- Use Python only for objective evidence, artifact/state management, assembly, and mechanical verification. Keep semantic grouping and page writing in the LLM-driven child skills.
- The main `/makewiki` conversation may read only `state.json`, `evidence.index.json`, `semantic-model.index.json`, and short child-skill receipts.

## Build & Test

```bash
uv sync
uv run pytest
```

## Code conventions

- Python 3.11+ with type annotations
- Pydantic models for structured data
- All objective extraction lives under `src/makewiki_skills/toolkit/`
- Markdown page artifacts are assembled from `.makewiki/runs/<run_id>/page-artifacts/`
- Tests use pytest
