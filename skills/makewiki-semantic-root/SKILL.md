---
name: makewiki-semantic-root
description: "Internal MakeWiki child skill. Use when the current job is semantic-root and you need to aggregate surface-card artifacts into project-brief.json and semantic-model.index.json without exposing full semantic detail to the main conversation."
---

# MakeWiki Semantic Root

Read only the provided surface-card artifacts.

Write:

- `project-brief.json`
- `semantic-model.index.json`
- one trace JSON
- one receipt JSON

`semantic-model.index.json` must stay index-only. Include module ids, names, workflow ids, page ids, scopes, and languages. Do not embed full module or workflow prose inside the index.

Return only the receipt path to the main conversation.
