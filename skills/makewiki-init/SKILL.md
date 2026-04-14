---
name: makewiki-init
description: "Generate a default makewiki.config.yaml configuration file in the current project. Use when: user wants to customize MakeWiki behavior before generating docs."
argument-hint: "[--lang <code>...]"
allowed-tools: Bash(python *) Write
---

# MakeWiki Init - Generate Configuration

Create a default `makewiki.config.yaml` in the current project root.

## Execution

Try the toolkit first:

Build the command explicitly from the parsed arguments:

- If no `--lang` flags were provided, run `python -m makewiki_skills init-config .`
- If languages were provided, append them directly, for example `python -m makewiki_skills init-config . --lang en --lang zh-CN`

```bash
python -m makewiki_skills init-config . --lang en --lang zh-CN
```

If the toolkit is not available, create the file manually with this content:

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
