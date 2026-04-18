---
name: makewiki-init
description: "Generate a default makewiki.config.yaml for MakeWiki. Use when a user wants to customize scan, orchestration, semantic reasoning, render, or review behaviour before running /makewiki."
version: "0.6.0"
argument-hint: "[--lang <code>...]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Write
---

# MakeWiki Init

Create a default `makewiki.config.yaml` in the current project root.

## Bootstrap

The bootstrap script refreshes `HOME/.makewiki` and its `.venv`, preferring `uv` and falling back to `python -m venv`.

```bash
python scripts/bootstrap_toolkit.py
```

If the launcher is available, run:

- `python <makewiki_root>/scripts/run_toolkit.py init-config .`
- or `python <makewiki_root>/scripts/run_toolkit.py init-config . --lang en --lang zh-CN`

If the launcher is unavailable, create the file manually with this content:

```yaml
output_dir: makewiki
languages:
  - en
  - zh-CN
default_language: en
overwrite: true
delete_stale_files: false
strict_grounding: true
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
  python_ast_config_tracking: true
  grep_fallback_for_config: true
  allow_llm_fallback_on_failure: true
review:
  enable_cross_language_review: true
  enable_code_grounding_verification: true
  enable_codebase_verification: true
  enable_semantic_review: true
  min_page_alignment_ratio: 0.9
semantic_reasoning:
  mode: llm-first
  module_index_threshold: 30
  index_only_in_main_conversation: true
orchestration:
  state_dir: .makewiki
  resume: true
  max_attempts: 2
  fail_fast: false
render:
  annotate_low_confidence_footnotes: true
documentation_policy:
  audience: end-user
  structure_strategy: user-journey
  prefer_task_oriented_sections: true
  include_architecture_analysis: false
  include_directory_overview: false
  include_source_walkthroughs: false
  forbid_unfounded_praise: true
  banned_descriptors:
    - powerful
    - robust
    - flexible
    - enterprise-grade
    - high-performance
    - elegant
    - state-of-the-art
    - cutting-edge
    - seamless
    - blazing-fast
    - world-class
    - best-in-class
    - production-ready
```

Explain the orchestration, semantic reasoning, and scan sections briefly after creating the file.
