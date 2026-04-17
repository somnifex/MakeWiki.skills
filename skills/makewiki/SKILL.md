---
name: makewiki
description: "Artifact-first multilingual documentation orchestrator for software projects. Use when a user wants project-level docs or wiki output and MakeWiki should run as the main LLM orchestrator: prepare objective evidence, read only the semantic index and short child-skill receipts, loop through module/workflow/page/language jobs, assemble markdown, and verify the final output."
version: "0.6.1"
argument-hint: "[--lang <code>...] [--output <dir>]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py *) Bash(python */scripts/run_toolkit.py *) Read Write Edit Glob Grep
---

# MakeWiki Orchestrator

Run MakeWiki as an artifact-first LLM orchestrator.

## Execution Mode

Stay in the main conversation.

- Do not use subagents or multi-agent fan-out.
- Use the Python toolkit only to compute objective evidence, run state, assembly content, and verification results.
- Use the internal child skills for semantic understanding and page writing.

## Bootstrap

Prepare the home-scoped toolkit first.

The bootstrap script inspects `HOME/.makewiki`, reports whether the bundled skill checkout is newer than the installed toolkit, and can sync it on demand. The launcher at `<makewiki_root>/scripts/run_toolkit.py` then bootstraps `<makewiki_root>/.venv`, preferring `uv` and falling back to `python -m venv`.

First inspect the installed toolkit:

```bash
python scripts/bootstrap_toolkit.py status --format json
```

Use `toolkit_root` from the JSON as `<makewiki_root>`.

- If `update_available` is `true`, pause and ask the user whether to update to the bundled version before continuing.
- If the user says yes, run `python scripts/bootstrap_toolkit.py update` and keep using the printed path as `<makewiki_root>`.
- If the user says no, keep using the existing `<makewiki_root>` from the JSON status output.
- If `status` is `missing`, run `python scripts/bootstrap_toolkit.py` to install the toolkit and use the printed path as `<makewiki_root>`.

Then prepare or resume the run:

```bash
python <makewiki_root>/scripts/run_toolkit.py prepare . --format json --no-write-run
```

This creates or resumes `.makewiki/runs/<run_id>/` logically and returns the initial files for:

- `state.json`
- `evidence.index.json`
- `evidence/shards/*.json`

Immediately materialize the returned `files` list with the built-in `Write` or `Edit` tool before moving to `status`. Do not use Python, `uv`, or shell redirection to write these objective evidence artifacts.

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
python <makewiki_root>/scripts/run_toolkit.py status . --format json --no-write-state
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

After each `status` call, overwrite `state.json` with the returned `state_update.content` using the built-in `Write` or `Edit` tool. Do not use Python, `uv`, or shell redirection to update `state.json`.

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
python <makewiki_root>/scripts/run_toolkit.py assemble . --lang en --lang zh-CN --format json --no-write-output
```

Use the returned `files` list to create or overwrite the final `makewiki/` files with the built-in `Write` or `Edit` tool. The toolkit should compute the content, but the agent should materialize the final user-facing files.

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

Do not use Python, `uv`, shell redirection, or ad-hoc scripts to write page artifacts, receipts, traces, `state.json`, or final `makewiki/` pages when the built-in `Write` or `Edit` tool can do the job.
