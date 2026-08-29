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

## Autonomous & Subagent-First Rules

1. **Subagent-First Cognitive Architecture**: All code comprehension, multi-perspective extraction, ReBattle debate, writing, and review must be driven by autonomous **Subagents** using their LLM reasoning and inspection tools (`Glob`, `Grep`, `Read`, `Edit`). Python scripts are strictly reserved as mechanical plumbing tools (for HTML site compilation and packaging).
2. **Zero Human Intervention (无人值守)**: Execute end-to-end autonomously from the initial skill invocation. Never pause to ask intermediate confirmation questions (e.g. outline approval, scan mode choices). Auto-select defaults and self-heal in-place.
3. **Project Sizing First**: Determine project tier (`Tier S`: 1-2 subagents, `Tier M`: 3-5 subagents, `Tier L`: 5-10 subagents max). Never spawn unbounded subagents.
4. **Subagent Role Specialization**:
   - **`Scout` (Structure / Surface)**: Read-only exploration of repository manifests, build tools, entrypoints, and CLI flags.
   - **`ReBattle` (Red / Blue / Green)**: 3-way competitive cross-examination (Red=User/DX, Blue=AST/Code, Green=Deployment/Ops).
   - **`Judge` (Main Agent)**: Mechanical conflict resolution (`verify`) to compile the authoritative `SemanticModel`.
   - **`Writers` (Multilingual)**: Parallel native generation strictly from `SemanticModel` — never machine-translate.
   - **`Auditor` (Reviewer)**: 100% code block & config key parity enforcement, link validation, and anti-AI-cliché audit.
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
SKILL.md                 Main skill definition
tasks/                   Task definitions (scan, rebattle, write, review, site, export, sync)
subskills/               Modular subskills (scan, site, review, validate, init)
scripts/                 Toolkit launcher and bootstrapping scripts
references/              Architecture, Diátaxis, Anti-cliché, Schemas, API docs
templates/               Config and report templates
examples/                Usage examples & sample test fixtures
src/makewiki_skills/     Python toolkit implementation
tests/                   Automated test suite
```

## Tests

```bash
uv sync --all-extras && uv run pytest --basetemp=.pytest_temp
```