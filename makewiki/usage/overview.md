# Usage Overview

MakeWiki.skills provides five slash commands that you run inside a Claude Code or Codex conversation. These commands cover the full lifecycle of documentation generation: from scanning your project to validating the final output.

## Available commands

| Command              | Purpose                                                             |
| -------------------- | ------------------------------------------------------------------- |
| `/makewiki`          | Run the full pipeline: scan, generate, review, verify, and validate |
| `/makewiki-scan`     | Scan a project and display collected evidence                       |
| `/makewiki-review`   | Compare language versions for factual consistency                   |
| `/makewiki-validate` | Check generated output for quality issues                           |
| `/makewiki-init`     | Create a default `makewiki.config.yaml`                             |

## Functional areas

### Documentation Generation

Run `/makewiki` to produce a complete multilingual wiki for your project. This is the primary command and runs all pipeline stages automatically.

- Scans your project for commands, config keys, file paths, and version info
- Builds a semantic model of user-visible features
- Generates documentation pages for each requested language
- Runs cross-language review and codebase verification
- Writes output to `<project>/makewiki/`

See [Documentation Generation](doc-generation.md) for full details.

### Project Inspection and Validation

Use `/makewiki-scan`, `/makewiki-review`, `/makewiki-validate`, and `/makewiki-init` to inspect, verify, and configure documentation without running the full generation pipeline.

- Preview what evidence MakeWiki can extract from your project
- Check existing docs for cross-language inconsistencies
- Validate output quality (headings, links, empty pages)
- Generate a config file to customize behavior

See [Project Inspection and Validation](project-inspection.md) for full details.

## Common workflow

A typical workflow looks like this:

1. Run `/makewiki-scan` to preview what MakeWiki sees in your project
2. Run `/makewiki-init` to create a config file (if you want custom settings)
3. Run `/makewiki` to generate the full documentation
4. Run `/makewiki-review` to check cross-language consistency
5. Run `/makewiki-validate ./makewiki` to check for quality issues

## Related documentation

- [Configuration](../configuration.md) — all config options in detail
- [FAQ](../faq.md) — common questions
- [Troubleshooting](../troubleshooting.md) — error messages and fixes