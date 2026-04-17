---
name: makewiki
description: "Artifact-first multilingual documentation orchestrator for software projects. Use when a user wants project-level docs or wiki output and MakeWiki should run as the main LLM orchestrator: prepare objective evidence, read only the semantic index and short child-skill receipts, loop through module/workflow/page/language jobs, assemble markdown, and verify the final output."
version: "0.6.0"
argument-hint: "[--lang <code>...] [--output <dir>]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Write Edit Glob Grep
---

# MakeWiki Orchestrator

Run MakeWiki as an artifact-first LLM orchestrator.

## Execution Mode

Stay in the main conversation.

- Do not use subagents or multi-agent fan-out.
- Use the Python toolkit only for objective evidence, run state, assembly, and verification.
- Use the internal child skills for semantic understanding and page writing.

## Bootstrap

Prepare the home-scoped toolkit first.

The bootstrap script refreshes `HOME/.makewiki` and its `.venv`, preferring `uv` and falling back to `python -m venv`.

```bash
python scripts/bootstrap_toolkit.py
```

If the command prints a path, refer to it as `<makewiki_root>`. Then prepare or resume the run:

```bash
python <makewiki_root>/scripts/run_toolkit.py prepare . --format json
```

This creates or resumes `.makewiki/runs/<run_id>/` and writes:

- `state.json`
- `evidence.index.json`
- `evidence/shards/*.json`

If `prepare` reports `llm_scan_required: true`, do not stop. Switch the scan stage to the internal LLM fallback skill and continue the same run.

If the bootstrap command prints `NOT_FOUND`, or if `prepare` cannot run because the Python environment is unavailable, switch to direct LLM scan mode:

- create the run directory manually under `.makewiki/runs/manual-<timestamp>/`
- write `state.json`
- write `evidence.index.json`
- write `evidence/shards/*.json`
- then continue with `llm-scan`, `semantic-root`, and the rest of the normal loop

## Main Loop

Refresh orchestration state before choosing work:

```bash
python <makewiki_root>/scripts/run_toolkit.py status . --format json
```

Use the returned `ready_jobs` list as the only scheduler input. The loop is:

1. If `llm-scan` is ready, complete it first.
2. Complete all `surface-card` jobs.
3. Complete `semantic-root`.
4. Loop `module-brief`.
5. Loop `workflow-brief`.
6. Loop `page-plan`.
7. Loop `page-write` by language.
8. If validation fails, run `page-repair` for the specific page-language pair.

Only pass the minimal artifact paths needed for the current job.

## Child Skills

Map job kinds to these internal skills:

- `llm-scan` -> `makewiki-llm-scan`
- `surface-card` -> `makewiki-surface-card`
- `semantic-root` -> `makewiki-semantic-root`
- `module-brief` -> `makewiki-module-brief`
- `workflow-brief` -> `makewiki-workflow-brief`
- `page-plan` -> `makewiki-page-plan`
- `page-write` -> `makewiki-page-write`
- `page-repair` -> `makewiki-page-repair`

Each child skill must write its own artifact, trace, and receipt file. After a child skill finishes, read only its receipt JSON and then run `status` again.

## Assembly And Checks

When the needed page plans and page artifacts exist, assemble the output:

```bash
python <makewiki_root>/scripts/run_toolkit.py assemble . --lang en --lang zh-CN --format json
```

Then run the mechanical checks:

```bash
python <makewiki_root>/scripts/run_toolkit.py verify . --format json
```

```bash
python <makewiki_root>/scripts/run_toolkit.py review . --lang en --lang zh-CN
```

```bash
python <makewiki_root>/scripts/run_toolkit.py validate ./makewiki
```

If a page fails validation, call `makewiki-page-repair` for that page only, read its receipt, and rerun `assemble` plus the failing checks.

## Artifact Boundaries

Load only these top-level orchestration artifacts in the main conversation:

- `state.json`
- `evidence.index.json`
- `semantic-model.index.json`
- child-skill receipt JSON files

`semantic-model.index.json` is index-only. It may contain module names, workflow ids, page ids, and languages. It must not contain full module briefs in the main conversation.

The main conversation should never copy child-skill prose back into itself. Child skills communicate through disk artifacts, not through conversational summaries.

## Hard Rules

Do not summarize or quote the content of module briefs / traces in the main conversation.

Only read child-skill receipts that contain status, artifact_path, trace_path, error_code, and attempt.

Do not load full module brief JSON, workflow brief JSON, trace JSON, or page markdown into the main conversation unless the current child skill explicitly needs that artifact as its direct input.

When `module_count > 30`, continue using only the index view and job receipts in the main conversation. Do not switch to loading full semantic artifacts.

If a receipt says `done` but the artifact file is missing, treat the job as stale and rerun only that job.

If a receipt says `failed`, rerun only that failed job. Do not restart the whole run.
