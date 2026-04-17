---
name: makewiki-page-plan
description: "Internal MakeWiki child skill. Use when the current job is a page-plan task and you need to write one language-agnostic page-plan JSON with page_id, output_path, kind, scope, and target_ids."
allowed-tools: Read Write Edit Glob Grep
---

# MakeWiki Page Plan

Read only the directly relevant semantic artifacts for the target page.

Write one language-agnostic page plan JSON. It must include:

- `page_id`
- `output_path`
- `kind`
- `scope`
- `target_ids`

Also write one trace JSON and one receipt JSON.

Use the built-in `Write` or `Edit` tool for every artifact. Do not use Python, `uv`, or shell redirection to write JSON files.

Keep the plan language-agnostic. Do not write markdown in this step.
