# MakeWiki.skills

MakeWiki.skills helps you put together multilingual user docs for a software project. It reads the project's configs, scripts, and existing docs first, then writes each language version separately instead of taking one source document and translating it line by line.

[简体中文](README.md) | **English**

## What it is for

This project is useful in two modes:

- As a CLI, it fits well into local scripts and CI and follows a predictable documentation workflow.
- As a skill/plugin, it works with AI coding assistants, but the final text still needs to be backed by the project.

In the end, the point is simple: docs people can follow, with claims you can trace back to the repo.

## Ground rules

- Each language is written separately rather than translated from one master version.
- Claims should come from project evidence.
- When evidence is incomplete, the docs should say so instead of guessing.
- Code blocks stay the same across languages; the prose is what changes.
- Output goes to `<target-project>/makewiki/` by default.

## Built-in languages

The repository ships with profiles for English, Simplified Chinese, Japanese, German, and French.  
You can add more by registering another language profile under `src/makewiki_skills/languages/profiles/`.

## Installation

Requires Python 3.11+ and either `uv` or `pip`.

```bash
git clone https://github.com/HowieWood/MakeWiki.skills.git
cd MakeWiki.skills
uv sync
```

If you prefer `pip`:

```bash
pip install -e .
```

## Quick start

Generate documentation for a target project:

```bash
makewiki generate /path/to/project --lang en --lang zh-CN
```

Other common commands:

```bash
makewiki scan /path/to/project
makewiki review /path/to/project --lang en --lang zh-CN
makewiki validate /path/to/project/makewiki
makewiki init-config /path/to/project
```

## Using it with AI assistants

### Claude Code

Load the repository as a plugin, then use the slash commands:

```bash
claude --plugin-dir /path/to/MakeWiki.skills

/makewiki --lang en --lang zh-CN
/makewiki-scan
/makewiki-review --lang en --lang zh-CN
/makewiki-validate ./makewiki
/makewiki-init
```

### Codex and other assistants

Assistants that read `AGENTS.md` can work from the repo root and call the CLI directly:

```bash
cd /path/to/MakeWiki.skills
uv sync
uv run makewiki generate /path/to/target --lang en --lang zh-CN
uv run makewiki scan /path/to/target
uv run makewiki review /path/to/target --lang en --lang zh-CN
uv run makewiki validate /path/to/target/makewiki
```

### CLI vs skill mode

- CLI mode is template-based and predictable. It fits automation, CI, and quick validation.
- Skill mode uses the same evidence pipeline, but lets the assistant write more natural prose for each language.

## Output layout

Generated files are written to `<target-project>/makewiki/`:

```text
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
  faq.md
  faq.zh-CN.md
  troubleshooting.md
  troubleshooting.zh-CN.md
  usage/
    basic-usage.md
    basic-usage.zh-CN.md
```

The default language keeps the base filename. Other languages add a suffix such as `.zh-CN`.

## Configuration

Create `makewiki.config.yaml` in the target project root:

```yaml
output_dir: makewiki
languages:
  - en
  - zh-CN
default_language: en
overwrite: true
generate_faq: true
generate_troubleshooting: true
strict_grounding: true
emit_uncertainty_notes: true
scan:
  ignore_dirs:
    - node_modules
    - dist
    - build
    - .git
  max_depth: 6
review:
  enable_cross_language_review: true
  enable_code_grounding_verification: true
  min_page_alignment_ratio: 0.9
```

You can generate the same file with:

```bash
makewiki init-config /path/to/project
```

## How the pipeline works

1. Detect the project type.
2. Collect evidence from configs, scripts, READMEs, and existing docs.
3. Build a language-neutral semantic model.
4. Render each language version independently.
5. Review structured facts across languages.
6. Check generated claims against project evidence.
7. Write the files and validate the Markdown output.

## Repository layout

```text
skills/                  AI skill definitions
src/makewiki_skills/     Python toolkit
  toolkit/               Filesystem, config, command, and markdown helpers
  scanner/               Project detection and evidence collection
  model/                 Language-neutral document model
  languages/             Language profiles and registry
  generator/             Document rendering
  review/                Cross-language consistency checks
  verification/          Evidence grounding checks
  pipeline/              Seven-stage orchestration
tests/                   Automated tests
examples/                Small sample projects
```

## Tests

```bash
uv sync && uv run pytest
```

## Boundaries

MakeWiki.skills is intentionally conservative. By default it does not:

- translate one language version into another
- generate API reference docs
- generate architecture diagrams or UML
- modify the target project's source code
- run dangerous or arbitrary project commands
- present guesses as confirmed facts

## License

MIT License © 2026 HowieWood
