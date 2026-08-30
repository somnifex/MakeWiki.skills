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

Reconnaissance fans out across **eight role-scoped scouts**, each owning an
explicit search scope. Every scout:

- **Directly inspects the repository** using `Glob`, `Grep`, `Read`, and
  `Bash` (`ls` / `find` / `git ls-files`) — independent of, and in addition to,
  the Python `evidence` / `coverage` bundles. Python is a *starting
  reference*, never the only source.
- **Two-phase retrieval**:
  - *Round 1 Broad Scan*: entrypoints, modules, key directories, configs,
    tests, deployment, docs leads.
  - *Round 2 Targeted Deep Dive*: trace symbol definitions, callers,
    implementations, overrides, defaults, test evidence, and conflicting docs.
- **Two-independent-sources rule**: for each key fact (a flag, a route, a
  config key, a default), seek at least two independent evidence sources —
  e.g. README + the actual CLI parser; a manifest + the source that reads it.
  A single source that contradicts code is a *conflict to surface*, not a fact.
- **Coverage handoff**: each scout ends by listing `unexplored` /
  `unresolved` areas — directories or topics it did NOT inspect. This feeds
  the coverage gate in `SKILL.md` Phase 1.5: the Main Agent must resolve or
  explicitly accept every item before entering the Judge stage.

### Role-Scoped Scouts

| Scout | Search Scope |
| ----- | ------------ |
| **Structure** | Topology via manifests & build configs: `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`; `Makefile`, `CMakeLists.txt`, `Taskfile.yml`, `Justfile`; `Dockerfile`, `docker-compose.yml`, Kubernetes manifests |
| **Runtime / Entrypoint** | Process entrypoints & start scripts: `__main__.py` / `if __name__ == "__main__"`, `bin/` targets, `[project.scripts]` / `scripts` / `bin` manifest fields, service mains, worker / daemon processes |
| **CLI / API** | User-facing surfaces: Typer/Click/Argparse flags & commands; Cobra/Clap/Commander options; FastAPI/Flask/Gin/Express/Axum REST route definitions; help strings |
| **Config** | Configuration & env schemas: `.env*`, `config.yaml` / `.toml` / `.ini` / `.cfg`, `settings`/`constants` modules, env-var reads; nested / composed overrides |
| **Tests / Behavior** | Test suites & behavioral evidence: `tests/`, `test_*`, `*_test`, pytest/unittest/Jest fixtures, CI test steps |
| **Deployment / CI** | `.github/workflows`, `.gitlab-ci.yml`, `Jenkinsfile`, `Docker`/`Compose`, k8s manifests, cloud/deploy scripts (`deploy.sh`, `serverless.yml`), migrations |
| **Docs / Examples** | `README*`, `docs/`, `examples/`, `guides/`, changelogs; example commands & expected outputs |
| **Dependency / Monorepo** | Manifests & lock files, vendored deps, plugin/extension registrations, multi-package `packages/*` / `pkg/*` layout, **generated-code boundaries** (`vendor/`, `dist/`, `build/`, `*_pb2.py`, `.min.js`, `generated/`) |

### Search-Scope Checklist (all scouts combined)

Every pass must explicitly cover — or explicitly declare uncovered — each of:
`source`, `tests`, `examples`, `README/docs`, `pyproject`/`package`/`Cargo`/`go`
manifests, CLI entrypoints, API/routes, config/env files, Docker/Compose,
Makefile/scripts, CI/CD, deployment, migrations, plugins/extensions, monorepo
packages, and **generated-code boundaries**.

### Per-Tier Allocation

| Tier | Scout Allocation |
| ---- | ---------------- |
| **Tier S** | 1~2 consolidated scouts (all roles folded into Structure + Surface) |
| **Tier M** | 3 scouts (Structure, Runtime/Entrypoint + CLI/API + Config consolidated, Tests/Behavior) |
| **Tier L** | up to 8 in parallel (one per role) |

All findings must trace back to a concrete file/line citation; claims the
Scout cannot ground stay out of the SemanticModel and the corresponding
Markdown slot renders `UNKNOWN`.
