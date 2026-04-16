# FAQ

## Which Python version do I need?

MakeWiki.skills requires Python 3.11 or later. This constraint comes from `pyproject.toml` (`requires-python = ">=3.11"`).

## How do I check that the installation worked?

Run the test suite:

```bash
uv run pytest
```

All tests should pass. If any fail, check that you're using Python 3.11+ and that `uv sync` (or `pip install -e .`) completed without errors.

## Where do I change user-facing settings?

Place a `makewiki.config.yaml` file in the target project's root directory. You can generate one with default values by running `/makewiki-init` in a Claude Code conversation. See [Configuration](configuration.md) for the full reference.

## Which languages are supported?

Five languages are built in: English (`en`), Simplified Chinese (`zh-CN`), Japanese (`ja`), German (`de`), and French (`fr`). You can add more by creating a language profile under `src/makewiki_skills/languages/profiles/`.

## Does MakeWiki translate from one language to another?

No. Each language version is written independently from the same project evidence. Code blocks stay identical across languages, but the prose is generated separately for each language. This avoids translation artifacts and ensures each version reads naturally.

## What if MakeWiki doesn't detect my project type?

MakeWiki uses file indicators to detect project types (e.g., `pyproject.toml` for Python, `package.json` for Node.js, `Cargo.toml` for Rust, `go.mod` for Go). If none match, it falls back to `generic` with lower confidence. You can run `/makewiki-scan` to see what was detected and adjust your project files accordingly.

## Can I generate documentation for only one language?

Yes:

```text
/makewiki --lang en
```

This generates English-only documentation. The cross-language review stage is skipped when only one language is requested.

## What does "strict grounding" mean?

When `strict_grounding: true` (the default), every command, config key, and file path mentioned in the generated docs must be traceable to project evidence. Claims that can't be grounded are flagged as violations. Setting it to `false` downgrades ungrounded claims to warnings instead.

## What happens to existing files when I re-run `/makewiki`?

By default (`overwrite: true`), existing files in the output directory are overwritten. Files not generated in the current run are kept unless `delete_stale_files: true` is set.

## Are there platform-specific steps?

Some development commands in this repository use Unix shell syntax. On Windows, use WSL or Git Bash if you encounter issues with shell commands.
