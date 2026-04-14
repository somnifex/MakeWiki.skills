# AGENTS.md

Instructions for AI coding assistants using MakeWiki.skills.

## What this is

A skill set that generates multilingual user documentation. Load it as a Claude Code plugin and call `/makewiki`, or use the CLI from this repo.

## Skills (Claude Code)

```bash
claude --plugin-dir /path/to/MakeWiki.skills

/makewiki --lang en --lang zh-CN
/makewiki-scan
/makewiki-review --lang en --lang zh-CN
/makewiki-validate ./makewiki
/makewiki-init
```

## CLI (Codex / other assistants)

```bash
cd /path/to/MakeWiki.skills && uv sync
uv run makewiki generate /path/to/target --lang en --lang zh-CN
uv run makewiki scan /path/to/target
uv run makewiki review /path/to/target --lang en --lang zh-CN
uv run makewiki validate /path/to/target/makewiki
```

## Rules

1. Generate each language independently — never translate.
2. Only include facts verifiable from project evidence.
3. Hedge when evidence is insufficient.
4. Keep code blocks identical across languages.
5. Output to `<project>/makewiki/` by default.

## Structure

```
skills/                  Skill definitions (SKILL.md)
src/makewiki_skills/     Python toolkit (scanning, review, validation)
tests/                   Automated tests
```

## Tests

```bash
uv sync && uv run pytest
```