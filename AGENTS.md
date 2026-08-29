# AGENTS.md

Instructions for AI coding assistants using MakeWiki.skills v2.

## What this is

A multi-agent skill set that generates evidence-backed, zero-hallucination multilingual user documentation and an interactive offline static website. It uses dynamic subagent budgeting (capped at 10) and ReBattle competitive verification.

## Skills

```bash
claude --plugin-dir /path/to/MakeWiki.skills

/makewiki --lang en --lang zh-CN    # Full flow: Sizing -> Scout -> ReBattle -> Writers -> Review -> Site
/makewiki-site ./makewiki           # Compile Markdown docs into offline static HTML website
/makewiki-scan                      # Inspect evidence, assess Tier (S/M/L), and view project brief
/makewiki-review --lang en --lang zh-CN # Cross-language consistency, code parity & truth check
/makewiki-validate ./makewiki       # Markdown structure & link validation
/makewiki-init                      # Generate makewiki.config.yaml with agent & site options
```

## Autonomous & Subagent Rules

1. **Zero Human Intervention (无人值守)**: Execute end-to-end autonomously from the initial skill invocation. Never pause to ask intermediate confirmation questions (e.g. outline approval, scan mode choices). Auto-select defaults and self-heal in-place.
2. **Project Sizing First**: Determine project tier (`Tier S`: 1-2 subagents, `Tier M`: 3-5 subagents, `Tier L`: 5-10 subagents max). Never spawn unbounded subagents.
3. **ReBattle Competitive Verification**: Use multi-perspective analysis (Agent Red for Developer/User UX, Agent Blue for Code AST/Implementation, Agent Green for Deployment/Ops) with cross-examination to eliminate hallucinations.
4. **Independent Generation**: Generate each language from the unified Semantic Model — never translate.
5. **No AI Clichés (去 AI 腔)**: Ban binary tropes ("不是而是"), abstract buzzwords ("收敛"), and redundant colons. Write natural, professional engineer prose.
6. **Code Block Parity**: Commands and code blocks must match 100% across all language versions.
7. **Zero Pollution**: Skill-first, run Python tools in temporary isolated environments when needed, and clean up immediately.

## Internal Toolkit (For Skills Only)

The launcher `scripts/run_toolkit.py` dispatches internal plumbing commands:

```bash
python scripts/run_toolkit.py sizing <target>
python scripts/run_toolkit.py scan <target> --format json
python scripts/run_toolkit.py build-site <target>/makewiki --theme auto
python scripts/run_toolkit.py export <target>/makewiki --format all --lang zh-CN
python scripts/run_toolkit.py sync <target>/makewiki --target all --lang zh-CN
python scripts/run_toolkit.py verify <target> --format json
python scripts/run_toolkit.py review <target> --lang en --lang zh-CN
python scripts/run_toolkit.py validate <target>/makewiki
```

## Structure

```
skills/                  Skill definitions (SKILL.md)
src/makewiki_skills/     Python toolkit (scanning, rebattle, site compiler, review, validation)
tests/                   Automated tests
```

## Tests

```bash
uv sync --all-extras && uv run pytest --basetemp=.pytest_temp
```