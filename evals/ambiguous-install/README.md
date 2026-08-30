# widget

A tiny Python package. Its install story is intentionally ambiguous — the
`pyproject.toml` defines package metadata (name, version, requires-python)
but no explicit build-system backend, so no single canonical install command
is resolvable from the evidence in this repo.

Docs must mark the install command UNKNOWN rather than guessing
`pip install -e .` or `uv sync` (there is no lockfile, no build backend, and
no documented environment setup).
