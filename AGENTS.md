# AGENTS.md

Instructions for AI coding assistants using MakeWiki.skills.

## What this is

A skill set that generates multilingual user documentation. Load it as a Claude Code plugin and invoke the skills. The Python toolkit is internal infrastructure - do not expose CLI commands to end users.

## Skills

```bash
claude --plugin-dir /path/to/MakeWiki.skills

/makewiki --lang en --lang zh-CN
/makewiki-scan
/makewiki-review --lang en --lang zh-CN
/makewiki-validate ./makewiki
/makewiki-init
```

Internal child skills used by `/makewiki`:

- `makewiki-llm-scan`
- `makewiki-surface-card`
- `makewiki-semantic-root`
- `makewiki-module-brief`
- `makewiki-workflow-brief`
- `makewiki-page-plan`
- `makewiki-page-write`
- `makewiki-page-repair`

## Internal toolkit (for skills only)

Skills should bootstrap the home-scoped toolkit under `HOME/.makewiki`. The launcher `scripts/run_toolkit.py` refreshes `HOME/.makewiki/.venv`, preferring `uv` and falling back to `python -m venv`, then dispatches to the internal toolkit via `python -m makewiki_skills <command>`. This is internal infrastructure - not a user-facing CLI.

```bash
python /path/to/MakeWiki.skills/scripts/run_toolkit.py prepare <target> --format json
python /path/to/MakeWiki.skills/scripts/run_toolkit.py status <target> --format json
python /path/to/MakeWiki.skills/scripts/run_toolkit.py assemble <target> --lang en --lang zh-CN --format json
python /path/to/MakeWiki.skills/scripts/run_toolkit.py scan <target>
python /path/to/MakeWiki.skills/scripts/run_toolkit.py review <target> --lang en --lang zh-CN
python /path/to/MakeWiki.skills/scripts/run_toolkit.py validate <target>/makewiki
python /path/to/MakeWiki.skills/scripts/run_toolkit.py init-config <target>
```

## Rules

1. Generate each language independently - never translate.
2. Only include facts verifiable from project evidence.
3. Hedge when evidence is insufficient.
4. Keep code blocks identical across languages.
5. Output to `<project>/makewiki/` by default.
6. Treat `/makewiki` as the LLM orchestrator. Python is limited to objective evidence, artifact/state management, assembly, and mechanical checks.
7. The main conversation may read `semantic-model.index.json`, `state.json`, and short receipts only. Do not summarize module briefs or traces in the main conversation.

## Structure

```text
skills/                  Skill definitions (SKILL.md)
src/makewiki_skills/     Python toolkit (objective evidence, run state, assembly, review, validation)
tests/                   Automated tests
```

## Tests

```bash
uv sync
uv run pytest
```
