# Getting Started

This guide walks you from zero to a working MakeWiki.skills setup and your first generated wiki.

> This guide focuses on user-visible behavior and skips internal architecture.

## What is MakeWiki.skills?

MakeWiki.skills is a set of skills (slash commands) for Claude Code and Codex. When you run `/makewiki` inside a project conversation, it scans the project and writes user-facing documentation in as many languages as you request. Each language version is written independently from the project evidence — not translated from another language.

## Prerequisites

- **Python** >= 3.11
- **Claude Code** or **Codex** (the skills are invoked as slash commands within a Claude Code session)
- **uv** (recommended) or **pip** for dependency management

## Install

```bash
git clone https://github.com/somnifex/MakeWiki.skills.git
cd MakeWiki.skills
uv sync
```

Or with pip:

```bash
pip install -e .
```

## Load the plugin

```bash
claude --plugin-dir /path/to/MakeWiki.skills
```

Replace `/path/to/MakeWiki.skills` with the actual path to your cloned repository.

## Generate your first wiki

Open a Claude Code conversation in any project directory, then run:

```text
/makewiki
```

By default, this generates English and Simplified Chinese documentation. After the command completes, you will find a `makewiki/` directory in your project root containing:

```
makewiki/
  index.md
  README.md
  README.zh-CN.md
  getting-started.md
  getting-started.zh-CN.md
  installation.md
  installation.zh-CN.md
  configuration.md
  configuration.zh-CN.md
  usage/basic-usage.md
  usage/basic-usage.zh-CN.md
  faq.md
  faq.zh-CN.md
  troubleshooting.md
  troubleshooting.zh-CN.md
```

## Verify the output

Check that the generated files look correct:

1. Open `makewiki/index.md` — it lists all generated pages with links
2. Open `makewiki/README.md` — it should describe your project based on evidence from your codebase
3. Compare `makewiki/README.md` and `makewiki/README.zh-CN.md` — code blocks should be identical, only the prose differs

## Next steps

- [Configure MakeWiki](configuration.md) to customize languages, output directory, and scanning behavior
- [Generate documentation](usage/doc-generation.md) with specific language and output options
- [Inspect and validate](usage/project-inspection.md) your project evidence and generated output