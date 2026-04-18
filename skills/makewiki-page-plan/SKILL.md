---
name: makewiki-page-plan
description: "Internal MakeWiki child skill. Use when the current job is a page-plan task and you need to write one language-agnostic page-plan JSON with page_id, output_path, kind, scope, and target_ids."
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

Keep the plan language-agnostic. Do not write markdown in this step.
