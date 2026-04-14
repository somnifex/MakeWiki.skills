# AGENTS.md

Instructions for AI coding assistants using MakeWiki.skills.

## What this is

A skill set that generates multilingual user documentation. Load it as a Claude Code plugin and invoke the skills. The Python toolkit is internal infrastructure — do not expose CLI commands to end users.

## Skills

```bash
claude --plugin-dir /path/to/MakeWiki.skills

/makewiki --lang en --lang zh-CN
/makewiki-scan
/makewiki-review --lang en --lang zh-CN
/makewiki-validate ./makewiki
/makewiki-init
```

## Internal toolkit (for skills only)

Skills call the Python toolkit via `python -m makewiki_skills <command>`. This is an internal interface — not a user-facing CLI.

```bash
python -m makewiki_skills scan <target>
python -m makewiki_skills review <target> --lang en --lang zh-CN
python -m makewiki_skills validate <target>/makewiki
python -m makewiki_skills init-config <target>
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