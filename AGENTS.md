# AGENTS.md

Instructions for AI coding assistants using MakeWiki.skills v2.

## What this is

A multi-agent skill set that generates evidence-backed, zero-hallucination multilingual user documentation and an interactive offline static website. It features dynamic subagent synthesis, 4-dimensional self-reflection loops, and ReBattle competitive verification.

## Skills

```bash
claude --plugin-dir /path/to/MakeWiki.skills

/makewiki --lang en --lang zh-CN    # Full flow: Dynamic Synthesis -> Scout -> ReBattle -> Writers -> Review -> Site
/makewiki-site ./makewiki           # Compile Markdown docs into offline static HTML website
/makewiki-scan                      # Inspect evidence, assess Tier (S/M/L), and view project brief
/makewiki-review --lang en --lang zh-CN # Cross-language consistency, code parity & truth check
/makewiki-validate ./makewiki       # Markdown structure & link validation
/makewiki-init                      # Generate makewiki.config.yaml with agent & site options
```

## Autonomous & Subagent-First Rules

1. **Subagent-First Cognitive Architecture**: All code comprehension, multi-perspective extraction, ReBattle debate, writing, and review must be driven by autonomous **Subagents** using their LLM reasoning and inspection tools (`Glob`, `Grep`, `Read`, `Edit`). Python scripts are strictly reserved as mechanical plumbing tools (for HTML site compilation and packaging).
2. **Dynamic Subagent Role Synthesis**: The Orchestrator dynamically configures specialized Subagent roles based on repository characteristics (e.g., monorepo modules, FFI bindings, plugin ecosystems) within an elastic budget capped at 10.
3. **Mandatory 4D Self-Reflection**: Every subagent executes an internal self-critique loop before submitting claims or writing documents:
   - Grounding Check: Ensure every command/key is cited with real code lines.
   - Parity Check: Confirm 100% code block and parameter match.
   - Anti-Cliché Check: Strip binary tropes ("不是而是"), buzzwords ("收敛"), and redundant colons.
   - Adversarial Defense: Hedge or retract unprovable assertions.
4. **Zero Human Intervention (无人值守)**: Execute end-to-end autonomously from the initial skill invocation. Never pause to ask intermediate confirmation questions (e.g. outline approval, scan mode choices). Auto-select defaults and self-heal in-place.
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