# Changelog

All notable changes to MakeWiki.skills are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2.0.0] — 2026-08-29

### Added

**Dynamic project sizing and subagent budgeting**
- Tier S / M / L classification based on file count, language diversity, and configuration complexity
- Hard cap of 10 concurrent subagents; Tier S projects use 1–2 agents to avoid unnecessary overhead

**ReBattle competitive verification**
- Three independent analysis perspectives: Red (developer/user UX), Blue (code AST/implementation), Green (deployment/ops)
- Judge agent cross-examines and resolves disagreements before any content is written
- Eliminates hallucinations by requiring evidence citations for every factual claim

**Offline static wiki SPA compiler** (`src/makewiki_skills/renderer/site_compiler.py`)
- Single self-contained HTML file with no external dependencies
- Multi-language switcher, dark/light theme toggle, local full-text search
- Hash-based URL routing with internal link navigation (`navigateTo`) and `hashchange` listener
- External links open with ↗ indicator in a new tab

**PDF-ready HTML and EPUB export** (`src/makewiki_skills/renderer/exporter.py`)
- `export_pdf_ready_html()` — print-ready single-file HTML with cover page, TOC, and page breaks
- `export_epub()` — valid EPUB 2.0 zip archive with `toc.ncx`, styled XHTML chapters, and no external dependencies
- CLI: `python scripts/run_toolkit.py export <makewiki_dir> --format all --lang zh-CN`

**Confluence and Notion knowledge base sync** (`src/makewiki_skills/sync/`)
- Markdown → Atlassian Confluence Storage Format (XHTML) with space import bundle
- Markdown → Notion Block API JSON payloads (Heading, Code, Callout, Table blocks)
- CLI: `python scripts/run_toolkit.py sync <makewiki_dir> --target all --lang zh-CN`

**Multi-language source code extractor** (`src/makewiki_skills/toolkit/source_extractor.py`)
- Go: `flag`/`pflag` CLI flags, Cobra/Urfave commands, Gin/Echo/Chi REST routes, exported functions with doc comments
- Rust: `clap` arg attributes, Axum/Actix route macros, `pub fn` with `///` doc comments
- Wired into `EvidenceCollector._collect_source_intelligence()` automatically for Go and Rust projects

**Docker Compose user-friendly config extraction**
- `extract_config_keys()` in `evidence.py` detects `services.*` structures and surfaces per-service environment variables with defaults and port bindings
- Eliminates internal YAML paths like `services.app.build.context` from generated configuration pages

**Open-source documentation**
- `CONTRIBUTING.md` — contributor workflow, code style, and test instructions
- `SECURITY.md` — responsible disclosure policy and sandboxing statement
- `README.md` + `README.en.md` — developer-first homepage, no marketing language

### Changed

- **Test suite**: comprehensive 157-test suite covering pipeline, scanner, renderer, sync, toolkit, and verification layers
- **Anti-cliché validation**: auto-flags `不是而是`, `收敛`, `这是xxx`, trailing colons, and redundant bullets during review phase
- **Evidence grounding**: all generated facts must be traceable to a file or command output; ungrounded assertions are blocked
- **Language generation**: each language version is generated independently from the shared semantic model — never translated from another language output

### Fixed

- Static site index links now render as clickable SPA-routed anchors (previously plain text after a regex interference bug)
- Docker Compose configuration pages no longer expose internal YAML path keys
- Go/Rust source extraction patterns correctly iterate per-pattern with `.finditer()` (previously miscalled on a list)
- Confluence sync CDATA blocks no longer double-escape HTML entities inside code samples

### Removed

- No deprecated APIs removed in this release; v2.0 is a clean additive major version on top of the original scaffold

---

## [0.1.0] — 2026-07-01

Initial scaffold release.

- Multilingual documentation generation (en, zh-CN, de, fr, ja) via language-specific generator modules
- Evidence collection from CLI help, README, config files, and Markdown tables
- Cross-language consistency reviewer
- Offline static wiki compiler (first iteration, no SPA routing)
- Basic Markdown structure validator
- `run_toolkit.py` dispatcher with `scan`, `build-site`, `validate`, `review`, `verify`, `sizing` commands