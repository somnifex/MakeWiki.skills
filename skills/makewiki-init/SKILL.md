---
name: makewiki-init
description: "Generate a default makewiki.config.yaml configuration file in the current project with multi-agent budget, static site, and enterprise delivery options. Use when: user wants to customize MakeWiki behavior before generating docs."
version: "2.0.0"
argument-hint: "[--lang <code>...]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Write
---
# MakeWiki Init - Generate Configuration

Create a default `makewiki.config.yaml` in the current project root.

## Execution

### Step 1: Bootstrap the home-scoped toolkit

Use the bundled bootstrap script. It prepares `<makewiki_root>` at `HOME/.makewiki` on Windows, macOS, and Linux. The launcher at `<makewiki_root>/scripts/run_toolkit.py` then bootstraps `<makewiki_root>/.venv`, preferring `uv` and falling back to `python -m venv`.

Run this bootstrap command:

```bash
python scripts/bootstrap_toolkit.py
```

### Step 2: Create Configuration File

Create `makewiki.config.yaml` with the following configuration:

```yaml
output_dir: makewiki
languages:
  - en
  - zh-CN
default_language: en
overwrite: true
delete_stale_files: false
generate_faq: true
generate_troubleshooting: true
strict_grounding: true
emit_uncertainty_notes: true

agent:
  max_subagents: 10
  rebattle_rounds: 2
  tier_override: auto         # auto | S | M | L

site:
  compile: true
  theme: auto                 # auto | light | dark
  include_search: true
  output_subdir: site

delivery:
  audience: dual              # dual | end-user | enterprise
  include_deployment_runbook: true
  include_compatibility_matrix: true
  include_health_checks: true

scan:
  ignore_dirs:
    - node_modules
    - dist
    - build
    - .git
    - .makewiki
    - __pycache__
    - .venv
    - venv
  max_depth: 6
  max_file_size_kb: 512
  enable_source_intelligence: true

review:
  enable_cross_language_review: true
  enable_code_grounding_verification: true
  enable_codebase_verification: true
  enable_semantic_review: true

content_depth:
  mode: auto                  # auto | compact | detailed
  max_faq_items: 20
  max_usage_examples: 8
  max_troubleshooting_items: 8
  split_usage_threshold: 6

documentation_policy:
  audience: end-user
  structure_strategy: user-journey
  prefer_task_oriented_sections: true
  forbid_unfounded_praise: true
```
