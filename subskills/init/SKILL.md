---
name: makewiki-init
description: "Generate a default makewiki.config.yaml configuration file in the current project with multi-agent budget, static site, evidence, review and quality-gate options. Use when: user wants to customize MakeWiki behavior before generating docs. Fields are either consumed by the Python Mechanical Plane or by the LLM Skill layer — no dead config."
version: "2.0.0"
argument-hint: "[--lang <code>...]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Write
---

# MakeWiki Init - Generate Configuration

Create a default `makewiki.config.yaml` in the current project root.

## Execution

### Step 1: Bootstrap the home-scoped toolkit

```bash
python scripts/bootstrap_toolkit.py
```

### Step 2: Create Configuration File

Create `makewiki.config.yaml` with the following configuration. Each field
is consumed either by the Python Mechanical Plane (`scan`, `review`,
`site`, `quality`, `revision`, `emit_uncertainty_notes`, `generate_*`) or by
the LLM Skill layer (`agent`, `delivery`, `language_profiles`,
`documentation_policy`, `content_depth`); the contract tests in
`tests/contracts/test_config_consumption_contract.py` enforce that no field
is dead.

```yaml
output_dir: makewiki
languages:
  - en
  - zh-CN
default_language: en
overwrite: true
delete_stale_files: false
generate_faq: true                  # emit faq.md slot (LLM-populated; UNKNOWN if empty)
generate_troubleshooting: true      # emit troubleshooting.md slot (LLM-populated; UNKNOWN if empty)
strict_grounding: true
emit_uncertainty_notes: true

# LLM-consumed: read by the Skill orchestrator / Writers (subagent budget + tier).
agent:
  max_subagents: 10
  rebattle_rounds: 2
  tier_override: auto               # auto | S | M | L

# Python-consumed (build-site).
site:
  compile: true
  theme: auto                       # auto | light | dark
  include_search: true
  output_subdir: site

# LLM-consumed: delivery scope sections chosen by the Writers.
delivery:
  audience: dual                    # dual | end-user | enterprise
  include_deployment_runbook: true
  include_compatibility_matrix: true
  include_health_checks: true

# Python-consumed (evidence collector).
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
  source_intelligence_max_files: 50
  max_external_urls: 3
  recursive_docs: true

# Python-consumed (parity / semantic-review prep / code-grounding / codebase checks).
review:
  enable_cross_language_review: true
  enable_code_grounding_verification: true
  enable_codebase_verification: true
  enable_semantic_review: true
  min_page_alignment_ratio: 0.9

# LLM-consumed: writer depth decisions.
content_depth:
  mode: auto                        # auto | compact | detailed
  max_faq_items: 20
  max_usage_examples: 8
  max_troubleshooting_items: 8
  split_usage_threshold: 6

# LLM-consumed: writer tone / structure decisions.
documentation_policy:
  audience: end-user
  structure_strategy: user-journey
  prefer_task_oriented_sections: true
  forbid_unfounded_praise: true

# Python-consumed: unified L0-L5 + Quality Gate thresholds.
quality:
  fail_on_critical: true
  allow_pending_llm_layers: true
  min_grounding_score: 1.0
```
