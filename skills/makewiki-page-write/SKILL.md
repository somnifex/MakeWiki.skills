---
name: makewiki-page-write
description: "Internal MakeWiki child skill. Use when the current job is a page-write task and you need to write one markdown page artifact for one page id and one language from a page plan plus the minimal relevant briefs."
allowed-tools: Read Write Edit Glob Grep
---
# MakeWiki Page Write

Read only:

- one page-plan JSON
- the minimal relevant module or workflow briefs
- the objective evidence needed for factual grounding

Write:

- one markdown page artifact
- one trace JSON
- one receipt JSON

Always create or update those artifacts with the built-in `Write` or `Edit` tool. Do not invoke Python, `uv`, or shell redirection to write them.

Code blocks must stay identical across languages.

When you must mention a low-confidence fact inferred from fallback scan, annotate it inline as:

`{{LOW_CONFIDENCE:relative/source/path.py}}`

Do not normalize the marker yourself. The Python assembler will convert it into a footnote.
