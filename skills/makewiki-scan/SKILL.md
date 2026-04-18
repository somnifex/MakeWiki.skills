---
name: makewiki-scan
description: "Objective evidence scan for MakeWiki. Use when a user wants to inspect what MakeWiki can prove from the repository before semantic orchestration: commands, config keys, paths, comments, AST config access hits, grep fallback hits, and shard layout."
version: "0.6.1"
argument-hint: "[--format json|human]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py *) Bash(python */scripts/run_toolkit.py *) Read Write Edit Glob Grep
---

# MakeWiki Scan

Run an objective scan only. Do not invent module or workflow structure during this skill.

## Bootstrap

The bootstrap script inspects `HOME/.makewiki`, reports whether the bundled skill checkout is newer than the installed toolkit, and can sync it on demand. The launcher at `<makewiki_root>/scripts/run_toolkit.py` then bootstraps `<makewiki_root>/.venv`, preferring `uv` and falling back to `python -m venv`.

```bash
python scripts/bootstrap_toolkit.py status --format json
```

Use `toolkit_root` from the JSON as `<makewiki_root>`.

- If `update_available` is `true`, pause and ask the user whether to update to the bundled version before continuing.
- If the user says yes, run `python scripts/bootstrap_toolkit.py update` and keep using the printed path as `<makewiki_root>`.
- If the user says no, keep using the existing `<makewiki_root>` from the JSON status output.
- If `status` is `missing`, run `python scripts/bootstrap_toolkit.py` to install the toolkit and use the printed path as `<makewiki_root>`.

If the launcher is available, run:

```bash
python <makewiki_root>/scripts/run_toolkit.py scan . --format json
```

The JSON output explicitly reports:

- `scan_status`
- `collection_mode`
- `llm_scan_required`
- `fallback_reason`
- `suggested_job_kind`
- `suggested_skill`

If the user wants a full orchestration run directory, you may also run:

```bash
python <makewiki_root>/scripts/run_toolkit.py prepare . --format json --no-write-run
```

If you use `prepare`, write the returned `files` list with the built-in `Write` or `Edit` tool instead of asking Python or `uv` to materialize the evidence artifacts.

If Python scanning fails or `prepare` reports `llm_scan_required: true`, fall back to direct LLM scanning:

- read the repository with `Read`, `Glob`, and `Grep`
- write objective evidence shards and an updated `evidence.index.json`
- keep semantic grouping out of this skill
- emit a short receipt for the `llm-scan` job

If the toolkit bootstrap itself is unavailable, create the evidence artifacts directly under `.makewiki/runs/manual-<timestamp>/` and keep the output objective.

## Report

Report only objective findings:

- detected project type
- commands
- config keys
- config access facts from Python AST
- grep fallback hits and their low confidence
- source files and paths
- error string evidence
- evidence shard count

Do not build a project brief, module list, workflow grouping, or page plan in this skill.
