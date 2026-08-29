# Task: Autonomous Project Reconnaissance & Sizing (Subagent 深度勘探)

## Overview

Reconnaissance is Phase 0 & 1 of the MakeWiki pipeline. **Scout Subagents**
autonomously explore the repository structure and developer interfaces,
extracting rich evidence directly from the codebase. The Python toolkit
provides the mechanical counterpart: `sizing` assesses tier + subagent
budget, and `evidence` (formerly `scan`) returns a facts-only JSON bundle
of commands, config keys, paths, and versions.

The boundary is explicit: Python returns **facts**; the LLM returns
**meaning**. Where the LLM cannot ground a claim in evidence, the
corresponding Markdown slot renders `UNKNOWN` rather than fabricated prose.

---

## 1. Dynamic Sizing & Subagent Allocation (Phase 0)

The tier is computed mechanically from source file count (`sizing`); the
LLM-orchestrated subagent budget respects that ceiling.

| Tier       | Source File Count | Subagent Budget  | ReBattle Protocol                         | Subagent Allocation                                   |
| ---------- | ----------------- | ---------------- | ----------------------------------------- | ----------------------------------------------------- |
| **Tier S** | < 15 files        | 1 ~ 2 Subagents  | Single-pass prompt self-review (0 rounds) | Main Agent (Scout+Judge) + 1~2 Parallel Writers       |
| **Tier M** | 15 ~ 80 files     | 3 ~ 5 Subagents  | Red vs Blue (1 debate round)              | 1 Scout + 2 ReBattle (Red, Blue) + 2 Writers          |
| **Tier L** | > 80 files        | 5 ~ 10 Subagents | Red + Blue + Green (2 debate rounds)      | 2 Scouts + 3 ReBattle + Parallel Writers + 1 Reviewer |

`agent.tier_override` in `makewiki.config.yaml` (LLM-consumed) lets the
Skill honor a manual override; otherwise the tier comes from `sizing`.

---

## 2. Scout Subagent Extraction Scope (Phase 1)

### `Scout-Structure Subagent`

Autonomously reads repository topology using `Glob`, `Grep`, and `Read`:
- Package manifests: `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`
- Build configurations: `Makefile`, `CMakeLists.txt`, `Taskfile.yml`, `Justfile`
- Infrastructure: `Dockerfile`, `docker-compose.yml`, Kubernetes manifests, GitHub Actions CI workflows

### `Scout-Surface Subagent`

Autonomously inspects user-facing surfaces:
- CLI entrypoints: Typer, Click, Argparse, Cobra, Clap flags, commands, help strings
- API route definitions: FastAPI, Flask, Gin, Express, Axum REST endpoints
- Configuration schemas: `.env.example`, `config.yaml`, environment variables

All findings must trace back to a concrete file/line citation; claims the
Scout cannot ground stay out of the SemanticModel and the corresponding
Markdown slot renders `UNKNOWN`.
