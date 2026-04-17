---
name: makewiki-llm-scan
description: "Internal MakeWiki child skill. Use when Python-based scanning failed or the current job is `llm-scan`, and you need to scan the repository directly with LLM tools, write objective evidence shards, update evidence.index.json, and emit a short receipt."
allowed-tools: Read Write Edit Glob Grep
---

# MakeWiki LLM Scan

Use this skill only when Python scanning is unavailable or failed for the current run.

## Inputs

Read only what you need to create objective evidence:

- the current `state.json`
- the current `evidence.index.json`
- repository files via `Read`, `Glob`, and `Grep`

## Output

Write:

- updated `evidence.index.json`
- `evidence/shards/*.json`
- one trace JSON
- one receipt JSON for job `llm-scan`

Use the built-in `Write` or `Edit` tool for those artifacts. Do not invoke Python, `uv`, or shell redirection to materialize them.

The receipt must contain only:

- `job_id`
- `status`
- `artifact_path`
- `trace_path`
- `error_code`
- `attempt`

## Rules

Do not perform semantic grouping here.

Do not invent module titles, workflow summaries, or page groupings.

Prefer direct file evidence. When you must infer from loose text or fallback grep, mark the evidence confidence as `low`.
