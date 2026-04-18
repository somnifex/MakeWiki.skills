# Documentation Generation

The `/makewiki` command runs the full documentation pipeline: scanning your project, generating pages for each requested language, running cross-language review, verifying claims against the codebase, and validating the output.

## Basic usage

```text
/makewiki
```

This generates English and Simplified Chinese documentation (the defaults) and writes output to `<project>/makewiki/`.

## Specify languages

```text
/makewiki --lang en --lang zh-CN --lang ja
```

Built-in language codes: `en`, `zh-CN`, `ja`, `de`, `fr`.

Each language version is written independently from the project evidence. MakeWiki does not translate from one language to another — it generates each version from scratch based on the same project understanding.

## Specify output directory

```text
/makewiki --output docs-wiki
```

This writes output to `<project>/docs-wiki/` instead of the default `makewiki/`.

## What the pipeline does

When you run `/makewiki`, it executes these stages in order:

1. **Detect project type** — identifies whether the project is Python, Node.js, Rust, Go, or generic based on files like `pyproject.toml`, `package.json`, `Cargo.toml`, or `go.mod`
2. **Collect evidence** — reads config files, documentation, scripts, and (for Python projects) source code to extract commands, config keys, file paths, version strings, CLI help text, and error messages
3. **Build semantic model** — organizes collected facts into a structured model: project identity, installation steps, configuration, commands, user tasks, FAQ, and troubleshooting items
4. **Generate documents** — renders Markdown pages for each requested language using the semantic model
5. **Cross-language review** — compares all language versions to find missing commands, config keys, or file paths
6. **Grounding verification** — checks that every command, config key, and path in the generated docs exists in the collected evidence
7. **Codebase verification** — checks the same claims against the actual project filesystem
8. **Output and validation** — writes files to disk and checks heading hierarchy, link integrity, and page completeness

## Output structure

After a successful run, the output directory looks like this (for English + Chinese):

```
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
  usage/basic-usage.md
  usage/basic-usage.zh-CN.md
  faq.md
  faq.zh-CN.md
  troubleshooting.md
  troubleshooting.zh-CN.md
```

For complex projects (many commands or config keys), the `usage/` section may be split into multiple sub-pages instead of a single `basic-usage.md`. This happens automatically when `content_depth.mode` is set to `auto` (the default).

## Key principles

- **Evidence-backed claims**: every command, config key, and path in the generated docs must come from the actual project. Claims without evidence are flagged or hedged.
- **Independent language generation**: each language version is written from scratch, not translated. Code blocks stay identical across languages; only prose differs.
- **No marketing language**: the generated docs describe what the project does without using subjective descriptors like "powerful" or "blazing-fast."

## Configuration keys that affect generation

| Key                  | Effect                                                          |
| -------------------- | --------------------------------------------------------------- |
| `output_dir`         | Where output files are written                                  |
| `languages`          | Which language versions to generate                             |
| `default_language`   | Which language gets unsuffixed filenames                        |
| `overwrite`          | Whether to overwrite existing files                             |
| `strict_grounding`   | Whether ungrounded claims are violations or warnings            |
| `content_depth.mode` | Whether to auto-detect, force detailed, or force compact output |

See [Configuration](../configuration.md) for the full reference.

## Usage examples

### Generate docs for a Python project

```text
/makewiki --lang en --lang zh-CN
```

Expected output: a `makewiki/` directory with installation steps based on `pyproject.toml`, config documentation from YAML/TOML files, and usage examples from README code blocks.

### Generate docs with Japanese

```text
/makewiki --lang en --lang ja
```

The Japanese version uses polite technical style (desu/masu form) and keeps English technical terms in katakana or as-is.

### Generate to a custom directory

```text
/makewiki --output wiki --lang en
```

Writes English-only documentation to `<project>/wiki/`.

## Related documentation

- [Usage Overview](overview.md) — all available commands at a glance
- [Project Inspection](project-inspection.md) — scan, review, and validate without full generation
- [Configuration](../configuration.md) — all config options