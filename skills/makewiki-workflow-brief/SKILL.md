---
name: makewiki-workflow-brief
description: "Internal MakeWiki child skill. Use when the current job is a workflow-brief task and you need to write one workflow brief JSON from the semantic index, the target module briefs, and the directly relevant surface cards."
allowed-tools: Read Write Edit Glob Grep
---

# MakeWiki Workflow Brief

Read only the workflow id, the referenced module briefs, and the directly relevant evidence.

Write:

- one workflow brief JSON
- one trace JSON
- one receipt JSON

Materialize those artifacts with the built-in `Write` or `Edit` tool. Do not use Python, `uv`, or shell redirection to write them.

Do not quote the workflow brief in the main conversation.
