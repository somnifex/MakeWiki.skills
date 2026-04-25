---
name: makewiki-init
description: "Generate a default makewiki.config.yaml configuration file in the current project. Use when: user wants to customize MakeWiki behavior before generating docs."
version: "0.7.5"
argument-hint: "[--lang <code>...]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Write
---
# MakeWiki Init - Generate Configuration

Create a default `makewiki.config.yaml` in the current project root.

## Execution

Use the bundled bootstrap script. It prepares `<makewiki_root>` at `HOME/.makewiki` on Windows, macOS, and Linux. The launcher at `<makewiki_root>/scripts/run_toolkit.py` then bootstraps `<makewiki_root>/.venv`, preferring `uv` and falling back to `python -m venv`.

Run this bootstrap command:

```bash
python scripts/bootstrap_toolkit.py
```

If the script prints a path, refer to it as `<makewiki_root>` and try the toolkit first:

Build the command explicitly from the parsed arguments:

- If no `--lang` flags were provided, run `python <makewiki_root>/scripts/run_toolkit.py init-config .`
- If languages were provided, append them directly, for example `python <makewiki_root>/scripts/run_toolkit.py init-config . --lang en --lang zh-CN`

```bash
python <makewiki_root>/scripts/run_toolkit.py init-config . --lang en --lang zh-CN
```

If the script prints `NOT_FOUND`, or if the launcher command fails, create the file manually with this content:

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
review:
  enable_cross_language_review: true
  enable_code_grounding_verification: true
  enable_semantic_review: true
  min_page_alignment_ratio: 0.9
content_depth:
  mode: auto                      # auto | detailed | compact
  max_faq_items: 20               # max FAQ entries (detailed mode)
  max_usage_examples: 8           # max usage examples (detailed mode)
  max_troubleshooting_items: 8    # max troubleshooting entries (detailed mode)
  split_usage_threshold: 6        # split usage into sub-pages when commands exceed this
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

Report the created file path and explain the key configuration options.
