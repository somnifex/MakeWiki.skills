---
name: makewiki-surface-card
description: "Internal MakeWiki child skill. Use when the current job is a surface-card task and you have exactly one evidence shard JSON to interpret into one surface-card artifact plus a short receipt."
---

# MakeWiki Surface Card

Read exactly one evidence shard JSON.

Write exactly three artifacts:

- one surface-card JSON
- one trace JSON
- one receipt JSON

The receipt must contain only:

- `job_id`
- `status`
- `artifact_path`
- `trace_path`
- `error_code`
- `attempt`

Do not summarize the shard back into the main conversation. Finish by reporting the receipt path only.
