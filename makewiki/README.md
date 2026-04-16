# MakeWiki.skills

MakeWiki.skills is a Claude Code / Codex plugin that generates multilingual user documentation for software projects. It scans your repository for commands, configuration, and scripts, then produces a set of Markdown wiki pages — one per requested language — with cross-language consistency checks and codebase verification.

## Who is it for?

- Developers who want user-facing documentation generated from their project's actual code and config files
- Teams maintaining documentation in multiple languages who need consistent content across all versions

## How it works

You load MakeWiki.skills as a Claude Code plugin and run `/makewiki` inside a project conversation. The plugin:

1. Scans the project for commands, config keys, file paths, and version info
2. Builds a semantic model of user-facing features
3. Generates documentation pages for each requested language (independently, not by translation)
4. Compares all language versions for factual consistency
5. Verifies generated claims against the actual project codebase
6. Validates output quality (headings, links, page completeness)

## Quick start

```bash
git clone https://github.com/somnifex/MakeWiki.skills.git
cd MakeWiki.skills
uv sync
```

Load the plugin in Claude Code:

```bash
claude --plugin-dir /path/to/MakeWiki.skills
```

Then in a project conversation:

```text
/makewiki --lang en --lang zh-CN
```

## Built-in languages

English, Simplified Chinese, Japanese, German, and French.

## Table of Contents

- [Getting Started](getting-started.md)
- [Installation](installation.md)
- [Configuration](configuration.md)
- **Usage**
  - [Overview](usage/overview.md)
  - [Documentation Generation](usage/doc-generation.md)
  - [Project Inspection and Validation](usage/project-inspection.md)
- [FAQ](faq.md)
- [Troubleshooting](troubleshooting.md)

## Documentation Navigation

| Language | Link                               |
| -------- | ---------------------------------- |
| English  | [README.md](README.md)             |
| 简体中文     | [README.zh-CN.md](README.zh-CN.md) |