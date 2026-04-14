# MakeWiki.skills

Type `/makewiki` in Claude Code or Codex to generate multilingual user documentation for your project.

[简体中文](README.md) | **English**

## What it does

Writes user documentation for any software project — installation, configuration, daily usage, troubleshooting — with each language generated independently rather than translated. Every claim in the output traces back to actual code, config, or scripts in the project.

## Usage

### Claude Code

Load the plugin, then call skills in any project conversation:

```bash
claude --plugin-dir /path/to/MakeWiki.skills
```

```
/makewiki --lang en --lang zh-CN    # Full pipeline: scan → generate → review → validate
/makewiki-scan                       # Scan only — see what the project exposes
/makewiki-review --lang en --lang zh-CN  # Cross-language consistency check
/makewiki-validate ./makewiki        # Validate existing docs
/makewiki-init                       # Generate default config
```

### Installation

Python 3.11+, via `uv` or `pip`:

```bash
git clone https://github.com/somnifex/MakeWiki.skills.git
cd MakeWiki.skills
uv sync          # or: pip install -e .
```

## Principles

- Each language is generated from the project understanding, never translated.
- Facts require project evidence; insufficient evidence is flagged, not guessed.
- Code blocks stay identical across languages — only prose differs.

## Output

Writes to `<project>/makewiki/` by default, with language suffixes:

```
makewiki/
  index.md
  README.md / README.zh-CN.md
  getting-started.md / getting-started.zh-CN.md
  installation.md / installation.zh-CN.md
  configuration.md / configuration.zh-CN.md
  usage/basic-usage.md / usage/basic-usage.zh-CN.md
  faq.md / faq.zh-CN.md
  troubleshooting.md / troubleshooting.zh-CN.md
```

## Configuration

Place `makewiki.config.yaml` in the target project root, or generate one with `/makewiki-init`:

```yaml
output_dir: makewiki
languages: [en, zh-CN]
default_language: en
overwrite: true
strict_grounding: true
scan:
  ignore_dirs: [node_modules, dist, build, .git, .makewiki]
  max_depth: 6
review:
  enable_cross_language_review: true
  enable_code_grounding_verification: true
```

## Built-in languages

English, Simplified Chinese, Japanese, German, French. Add more under `src/makewiki_skills/languages/profiles/`.

## Pipeline

Scan project → collect evidence → build semantic model → generate per language → cross-language review → evidence grounding → write and validate.

## Out of scope

No translation, no API reference, no architecture diagrams, no source code modification, no dangerous commands, no unsubstantiated claims.

## Tests

```bash
uv sync && uv run pytest
```

## License

MIT License © 2026 HowieWood
