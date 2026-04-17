---
name: makewiki-page-repair
description: "Internal MakeWiki child skill. Use when a specific assembled page failed validation or verification and you need to rewrite only that page-language artifact from the existing page, page plan, and failure details."
allowed-tools: Read Write Edit Glob Grep
---

# MakeWiki Page Repair

Read only:

- the failing page artifact
- its page plan
- the relevant validation or verification failures
- the minimal supporting briefs or evidence

Rewrite only that page-language artifact.

Also write:

- one trace JSON
- one receipt JSON

Use the built-in `Write` or `Edit` tool for the rewritten page and both JSON artifacts. Do not use Python, `uv`, or shell redirection to write them.

Do not touch unrelated pages. Do not summarize the repair trace in the main conversation.
