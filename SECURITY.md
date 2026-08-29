# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | :white_check_mark: |
| < 2.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in MakeWiki.skills, please report it responsibly:

1. **Do NOT** open a public issue on GitHub.
2. Email security findings or privately contact the repository maintainers.
3. Please include:
   - Description of the vulnerability.
   - Steps to reproduce or proof of concept.
   - Potential impact and affected components.

## Sandboxing & Execution Guarantees

MakeWiki.skills follows strict safety guidelines:
- **No Destructive Shell Execution**: Skills and launcher scripts only execute non-destructive probes (reading manifests, extracting comments, checking CLI `--help`).
- **Path Traversal Protection**: Filesystem tools enforce boundary checks against target directories.
- **Zero Pollution**: Temporary AST traces and venv scripts are isolated and cleaned up immediately after execution.
