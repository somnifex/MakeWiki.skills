# MakeWiki.skills

Type `/makewiki` in Claude Code or Codex to generate multilingual user documentation for a project.

[简体中文](README.md) | **English**

## What it does

MakeWiki.skills scans the repository first, then writes user docs for installation, configuration, day-to-day usage, FAQ, and troubleshooting. Each language version is written from the same project evidence instead of being translated from another language.

## Usage

### Claude Code

Load the plugin:

```bash
claude --plugin-dir /path/to/MakeWiki.skills
```

Then run the skills inside a project conversation:

```text
/makewiki --lang en --lang zh-CN    # Full flow: scan → generate → review → validate
/makewiki-scan                      # Inspect what the project exposes
/makewiki-review --lang en --lang zh-CN
/makewiki-validate ./makewiki
/makewiki-init
```

### Installation

Requires Python 3.11+. Install with `uv` or `pip`:

```bash
git clone https://github.com/somnifex/MakeWiki.skills.git
cd MakeWiki.skills
uv sync          # or pip install -e .
```

## Principles

- Each language is written independently, not translated.
- Documentation claims need project evidence. When evidence is weak, the docs stay cautious.
- Code blocks stay identical across languages; only the prose changes.

## Output

By default, files are written to `<project>/makewiki/`:

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

English, Simplified Chinese, Japanese, German, and French. Add more under `src/makewiki_skills/languages/profiles/`.

## Pipeline

Scan the project → collect evidence → build the semantic model → generate docs → review across languages → validate the output.

## Out of scope

No translation of existing docs, no API reference generation, no architecture write-up, no source edits, no unsafe commands, and no invented facts.

## Thanks

Thanks to the people who keep sharing debugging notes, issue threads, and forum posts on [GitHub](https://github.com/), [Reddit](https://www.reddit.com/), and [Linux.do](https://linux.do/). That public problem-solving helped shape this project.

## Tests

```bash
uv sync && uv run pytest
```

## License

MIT License © 2026 HowieWood
