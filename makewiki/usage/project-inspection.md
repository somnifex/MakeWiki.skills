# Project Inspection and Validation

MakeWiki.skills includes four commands for inspecting your project, reviewing existing documentation, validating output quality, and creating config files — without running the full generation pipeline.

## Scan project evidence

```text
/makewiki-scan
```

This scans the current project and displays a summary of all evidence collected: detected project type, fact counts by type (commands, config keys, paths, versions), and confidence levels.

### What it shows

After scanning, you see output like:

- **Project name** and **detected type** (e.g., `python-cli`, `node-react`)
- **Detection confidence** percentage
- **Indicators found** (e.g., `pyproject.toml`, `src/`)
- **Evidence summary table**: counts of commands, config keys, paths, versions, descriptions, and other fact types
- **Total facts** collected

### When to use it

- Before running `/makewiki`, to preview what MakeWiki can extract from your project
- To identify evidence gaps — for example, if few commands are detected, your README may need more code blocks
- To verify that ignored directories (`scan.ignore_dirs`) are set correctly

### Configuration keys that affect scanning

| Key                                  | Effect                                                |
| ------------------------------------ | ----------------------------------------------------- |
| `scan.ignore_dirs`                   | Directories excluded from scanning                    |
| `scan.max_depth`                     | Maximum directory depth                               |
| `scan.max_file_size_kb`              | Maximum file size to read                             |
| `scan.enable_source_intelligence`    | Whether to scan Python source for CLI help and errors |
| `scan.source_intelligence_max_files` | Maximum Python files to scan                          |

## Review cross-language consistency

```text
/makewiki-review --lang en --lang zh-CN
```

This compares the generated documentation across language versions and reports factual inconsistencies.

### What it checks

The reviewer extracts structured facts from each language version and compares:

- **Commands** — every command in code blocks must appear in all languages (severity: critical)
- **Config keys** — every config key reference must appear in all languages (severity: critical)
- **File paths** — file path references should match across languages (severity: major)
- **Version strings** — version numbers should match (severity: major)
- **Page coverage** — all languages should have the same set of pages (severity: major)

### What it shows

- **Consistency score** — percentage showing how well the language versions match
- **Inconsistency table** — each mismatch with its type, value, which languages have it, which are missing it, and severity

### When to use it

- After running `/makewiki` to verify the output before publishing
- When you suspect one language version was updated but another wasn't
- As part of a documentation quality checklist

## Validate generated output

```text
/makewiki-validate ./makewiki
```

This checks the generated output directory for Markdown quality issues.

### What it checks

- **Missing H1** — every page should start with an H1 heading
- **Heading hierarchy** — no skipped levels (e.g., jumping from H2 to H4)
- **Broken internal links** — links between generated pages must resolve to actual files
- **Empty pages** — pages with no meaningful content are flagged
- **Banned descriptors** — marketing words (like "powerful" or "seamless") used without evidence are flagged
- **Forbidden headings** — developer-facing headings (like "Architecture" or "Project Structure") are flagged in user documentation

### What it shows

- **File count** and number of files with issues
- **Errors** (must fix) and **warnings** (should fix)
- **Pass/fail** status — fails if any errors are found

### When to use it

- After running `/makewiki` as a final quality check
- After manually editing generated files to catch formatting regressions
- As part of a CI pipeline for documentation quality

## Create default configuration

```text
/makewiki-init
```

This generates a `makewiki.config.yaml` file in the current project root with default settings.

### Specify languages

```text
/makewiki-init --lang en --lang zh-CN --lang ja
```

### What it creates

A YAML file with all default configuration values, ready for you to customize:

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

### When to use it

- Before your first `/makewiki` run, if you want to customize behavior
- When adding support for additional languages
- When you want to adjust scanning or review settings

## Related documentation

- [Usage Overview](overview.md) — all available commands
- [Documentation Generation](doc-generation.md) — the full `/makewiki` pipeline
- [Configuration](../configuration.md) — all config options in detail