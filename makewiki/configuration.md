# Configuration

MakeWiki.skills reads configuration from a `makewiki.config.yaml` file in the target project's root directory. If no config file exists, defaults are used.

> This page lists runtime configuration only. Build and packaging metadata are left out.

## Create a default config file

Run `/makewiki-init` in a Claude Code conversation to generate a `makewiki.config.yaml` with default values:

```text
/makewiki-init
```

You can also specify languages:

```text
/makewiki-init --lang en --lang zh-CN --lang ja
```

## Configuration file reference

### Top-level options

| Key                        | Default       | Description                                                                                                      |
| -------------------------- | ------------- | ---------------------------------------------------------------------------------------------------------------- |
| `output_dir`               | `makewiki`    | Directory name for generated wiki files (relative to project root)                                               |
| `languages`                | `[en, zh-CN]` | Language codes to generate. Built-in: `en`, `zh-CN`, `ja`, `de`, `fr`                                            |
| `default_language`         | `en`          | The default language uses no file suffix (e.g., `README.md` instead of `README.en.md`)                           |
| `overwrite`                | `true`        | When `true`, existing files in the output directory are overwritten on each run                                  |
| `delete_stale_files`       | `false`       | When `true`, removes `.md` files from the output directory that were not generated in the current run            |
| `generate_faq`             | `true`        | When `false`, skips generating the FAQ page                                                                      |
| `generate_troubleshooting` | `true`        | When `false`, skips generating the troubleshooting page                                                          |
| `strict_grounding`         | `true`        | When `true`, claims not backed by project evidence are treated as violations. When `false`, they become warnings |
| `emit_uncertainty_notes`   | `true`        | When `true`, adds notes to generated pages where evidence is insufficient                                        |

### Scan options (`scan:`)

These options control how the project is scanned for evidence.

| Key                                  | Default                                                                  | Description                                                                                   |
| ------------------------------------ | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| `scan.ignore_dirs`                   | `[node_modules, dist, build, .git, .makewiki, __pycache__, .venv, venv]` | Directories excluded from scanning                                                            |
| `scan.max_depth`                     | `6`                                                                      | Maximum directory depth for scanning files                                                    |
| `scan.max_file_size_kb`              | `512`                                                                    | Files larger than this size (in KB) are skipped                                               |
| `scan.enable_source_intelligence`    | `true`                                                                   | When `true`, scans Python source files for CLI help text, error messages, and config comments |
| `scan.source_intelligence_max_files` | `50`                                                                     | Maximum number of source files to scan for intelligence extraction                            |

### Review options (`review:`)

These options control the post-generation review and verification stages.

| Key                                         | Default | Description                                                                                |
| ------------------------------------------- | ------- | ------------------------------------------------------------------------------------------ |
| `review.enable_cross_language_review`       | `true`  | Compares structured facts (commands, config keys, file paths) across all language versions |
| `review.enable_code_grounding_verification` | `true`  | Checks that claims in generated docs exist in the collected evidence cache                 |
| `review.enable_codebase_verification`       | `true`  | Checks that claims in generated docs exist on the actual project filesystem                |
| `review.enable_semantic_review`             | `true`  | Prepares aligned passages for semantic cross-language review                               |
| `review.min_page_alignment_ratio`           | `0.9`   | Minimum ratio of pages that should exist in all languages                                  |

### Content depth options (`content_depth:`)

These options control how much detail is generated.

| Key                                       | Default | Description                                                                                                                                            |
| ----------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `content_depth.mode`                      | `auto`  | `auto` detects from project complexity. `detailed` always uses modular docs with higher content caps. `compact` uses single-page usage with lower caps |
| `content_depth.max_faq_items`             | `20`    | Maximum number of FAQ entries to generate                                                                                                              |
| `content_depth.max_usage_examples`        | `8`     | Maximum number of usage examples to include                                                                                                            |
| `content_depth.max_troubleshooting_items` | `8`     | Maximum number of troubleshooting entries                                                                                                              |
| `content_depth.split_usage_threshold`     | `6`     | When commands exceed this count, usage is split into sub-pages                                                                                         |

## Example configuration

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

## Related documentation

- [Documentation Generation](usage/doc-generation.md) — how config options affect the `/makewiki` command
- [Project Inspection](usage/project-inspection.md) — how scan config affects `/makewiki-scan`