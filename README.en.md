# MakeWiki.skills

Type `/makewiki` in Claude Code or Codex to generate multilingual user documentation for a project.

[简体中文](README.md) | **English**

## What it does

MakeWiki.skills runs `/makewiki` as an artifact-first orchestrator. Python scans the repository into objective evidence shards and resumable run state, while the LLM performs semantic grouping, module/workflow understanding, page planning, and page writing. Each language version is written independently from shared evidence instead of being translated from another language.

## Usage

### Claude Code

Load the plugin:

```bash
claude --plugin-dir /path/to/MakeWiki.skills
```

Then run the skills inside a project conversation:

```text
/makewiki --lang en --lang zh-CN
/makewiki-scan
/makewiki-review --lang en --lang zh-CN
/makewiki-validate ./makewiki
/makewiki-init
```

`/makewiki` now follows an artifact-first flow:

1. Prepare objective evidence and resumable run state.
2. Loop on `status` and execute child-skill jobs (`surface-card`, `semantic-root`, `module-brief`, `workflow-brief`, `page-plan`, `page-write`, `page-repair`).
3. Assemble page artifacts into `<project>/makewiki/`.
4. Run verification, review, and validation.

### Installation

Requires Python 3.11+. Install with `uv` or `pip`:

```bash
git clone https://github.com/somnifex/MakeWiki.skills.git
cd MakeWiki.skills
uv sync
```

## Principles

- Each language is written independently, not translated.
- Python only handles objective evidence, artifact/state management, assembly, and mechanical checks.
- Semantic grouping and page writing stay in the LLM-driven child skills.
- If Python-based scanning fails, MakeWiki can fall back to an LLM-driven repository scan that writes evidence artifacts directly.
- Documentation claims need project evidence. When evidence is weak, the docs stay cautious.
- Code blocks stay identical across languages; only the prose changes.
- The main `/makewiki` conversation reads only `state.json`, `semantic-model.index.json`, and short receipts. Module briefs and traces stay on disk.

## Output

By default, files are written to `<project>/makewiki/`:

```text
makewiki/
  index.md
  README.md / README.zh-CN.md
  getting-started.md / getting-started.zh-CN.md
  installation.md / installation.zh-CN.md
  configuration.md / configuration.zh-CN.md
  commands.md / commands.zh-CN.md
  modules/overview.md / modules/overview.zh-CN.md
  modules/<module>.md / modules/<module>.zh-CN.md
  workflows/overview.md / workflows/overview.zh-CN.md
  workflows/<workflow>.md / workflows/<workflow>.zh-CN.md
  integrations/overview.md / integrations/overview.zh-CN.md
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
  python_ast_config_tracking: true
  grep_fallback_for_config: true
  allow_llm_fallback_on_failure: true
semantic_reasoning:
  mode: llm-first
  module_index_threshold: 30
  index_only_in_main_conversation: true
orchestration:
  state_dir: .makewiki
  resume: true
  max_attempts: 2
render:
  annotate_low_confidence_footnotes: true
review:
  enable_cross_language_review: true
  enable_code_grounding_verification: true
```

## Built-in languages

English, Simplified Chinese, Japanese, German, and French. Add more under `src/makewiki_skills/languages/profiles/`.

## Internal toolkit

The toolkit under `scripts/run_toolkit.py` is for skills only. The key internal commands are:

```bash
python scripts/run_toolkit.py prepare . --format json --no-write-run
python scripts/run_toolkit.py status . --format json --no-write-state
python scripts/run_toolkit.py assemble . --lang en --lang zh-CN --format json --no-write-output
python scripts/run_toolkit.py verify .
python scripts/run_toolkit.py review . --lang en --lang zh-CN
python scripts/run_toolkit.py validate ./makewiki
```

In Claude Code, prefer letting the toolkit compute content and refreshed state while the built-in `Write` / `Edit` tools materialize `state.json`, `evidence.index.json`, `evidence/shards/*.json`, `makewiki.config.yaml`, and the final `makewiki/` pages. That reduces repeated approval prompts caused by Python or `uv` writing files directly.

## Out of scope

No translation of existing docs, no API reference generation from thin evidence, no architecture write-up in default user docs, no source edits, no unsafe commands, and no invented facts.

## Tests

```bash
uv sync
uv run pytest
```

## License

MIT License © 2026 HowieWood
