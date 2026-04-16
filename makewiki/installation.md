# Installation

## Prerequisites

| Requirement          | Version           | Notes                                         |
| -------------------- | ----------------- | --------------------------------------------- |
| Python               | >= 3.11           | Required for both `uv` and `pip` installation |
| Claude Code or Codex | Any               | Skills are invoked as slash commands          |
| uv                   | Any (recommended) | Falls back to pip if unavailable              |

## Install with uv (recommended)

```bash
git clone https://github.com/somnifex/MakeWiki.skills.git
cd MakeWiki.skills
uv sync
```

## Install with pip

```bash
git clone https://github.com/somnifex/MakeWiki.skills.git
cd MakeWiki.skills
pip install -e .
```

## Load as a Claude Code plugin

After installation, load the plugin each time you start Claude Code:

```bash
claude --plugin-dir /path/to/MakeWiki.skills
```

Replace `/path/to/MakeWiki.skills` with the actual path to the cloned repository.

## Verify installation

Run the test suite to confirm everything is set up correctly:

```bash
uv run pytest
```

You should see all tests pass. If any test fails, check that you are using Python 3.11 or later and that all dependencies installed without errors.

## Platform Notes

### Windows

Some development commands in this repository use Unix shell syntax. If you encounter issues, use WSL or Git Bash instead of the default Windows command prompt.

### macOS / Linux

No special steps required. Both `uv` and `pip` work as described above.
