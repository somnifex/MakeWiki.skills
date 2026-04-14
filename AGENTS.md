# AGENTS.md - MakeWiki.skills

This file provides instructions for AI coding assistants (Claude Code, Codex, etc.) working on or using this project.

> Primary documentation: [README.md](README.md) (简体中文) | [README.en.md](README.en.md) (English)

## What This Project Does

MakeWiki.skills generates multilingual user-facing wiki documentation for any software project by:
1. Scanning the target project (files, configs, scripts, READMEs)
2. Building a language-neutral semantic model of the project
3. Independently generating documentation in each requested language
4. Cross-verifying facts across languages for consistency
5. Validating generated docs against project evidence

## How to Use This Project

### As a Plugin (Claude Code)

```bash
# Load as plugin
claude --plugin-dir /path/to/MakeWiki.skills

# Then invoke skills:
# /makewiki --lang en --lang zh-CN
# /makewiki-scan
# /makewiki-review --lang en --lang zh-CN
# /makewiki-validate ./makewiki
# /makewiki-init
```

### As a CLI Tool

```bash
cd /path/to/MakeWiki.skills && uv sync
uv run makewiki generate /path/to/target --lang en --lang zh-CN
uv run makewiki scan /path/to/target
uv run makewiki review /path/to/target --lang en --lang zh-CN
uv run makewiki validate /path/to/target/makewiki
uv run makewiki init-config /path/to/target
```

## Critical Rules for AI Assistants

1. **NEVER translate.** Generate each language independently from project understanding.
2. **NEVER fabricate.** Only include facts verifiable from project evidence.
3. **Use hedged language** when evidence is insufficient.
4. **Keep code blocks identical** across languages - only prose differs.
5. **Output to `<project>/makewiki/`** by default.

## Project Structure

```
skills/                  # Skill definitions (SKILL.md)
src/makewiki_skills/     # Python toolkit
  toolkit/               # I/O abstraction (filesystem, config, evidence)
  scanner/               # Project detection + evidence collection
  model/                 # Language-neutral semantic model
  languages/             # Language profiles (en, zh-CN, ja, de, fr)
  generator/             # Template-based generation
  review/                # Cross-language consistency
  verification/          # Code-evidence grounding
  pipeline/              # 7-stage orchestrator
tests/                   # 80 test cases
examples/                # Sample projects for testing
```

## Testing

```bash
uv sync && uv run pytest
```