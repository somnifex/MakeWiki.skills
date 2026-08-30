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

### Structured Scout Output

Every scout MUST return its findings in the same machine-readable shape so
the Main Agent can reconcile coverage and confidence mechanically before
Judge. Return **all five fields**, never a free-form narrative:

```
searched: [ <areas you actually inspected, e.g. "src/cli/", "tests/", "pyproject.toml"> ]
evidence_found:
  - claim: <fact>
    refs: [ "<path:line>", ... ]          # >= 2 independent citations for key facts
    confidence: low | medium | high        # explicit, per-claim
unresolved: [ <areas/topics you did NOT inspect, or could not ground> ]
recommended_followup:
  - <a targeted search to close the lowest-confidence claim, e.g. "trace server.workers default in .config/app.yml"> 
```

A claim marked `confidence: low` or an `unresolved` entry that is load-bearing
is **not** silently carried forward. It triggers a **Follow-up Scout**.

### Follow-up Scout Dispatch (low-confidence, not Python fallback)

Low confidence and unresolved load-bearing areas are closed by **another
targeted LLM Scout turn**, never by asking Python to guess:

1. The Main Agent, on receiving any `confidence: low` claim or an
   `unresolved` area the gate deems important, dispatches a **Follow-up
   Scout** — a single-purpose Round-2 deep dive riding the `recommended_followup`
   from the originating scout.
2. The Follow-up Scout searches only that lead with `Grep` / `Read` /
   `Bash`, traces the symbol / default / override to a concrete definition,
   and reports refs + a reassessed confidence.
3. Python (`evidence` / `coverage`) remains a deterministic *starting
   reference*; it never resolves semantic uncertainty by guessing. Unresolved
   means the LLM looks harder, or the slot stays `UNKNOWN` — never invented.

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

---

## 3. Pre-ReBattle Coverage Checklist (Main Agent gate)

Before entering ReBattle / Judge, the Main Agent answers **all six** against
the aggregated scout output + `coverage` report. Each must be **covered**
(evidence exists) or **explicitly accepted** (with a written reason why it is
out of scope); a `no` left unresolved blocks Judge:

| # | Check | Ask |
| - | ----- | --- |
| 1 | **Tests** | Did a scout actually read `tests/` / `test_*`, not just note it exists? Do docs assert behavior the tests contradict? |
| 2 | **CI / deployment** | Were `.github/workflows`, `.gitlab-ci.yml`, `Dockerfile` / `docker-compose.yml`, k8s manifests inspected — or only README? |
| 3 | **Examples** | Were `examples/` / `docs/` example commands checked against the *current* CLI, or copied stale from prose? |
| 4 | **Nested packages** | In a monorepo / multi-package repo, was every `packages/*` / `pkg/*` manifest + hidden entrypoint surfaced, or only the root? |
| 5 | **Runtime entrypoint** | Was the real process/CLI entrypoint located (`__main__`, `[project.scripts]`, `bin/`, `if __name__`), not assumed from README? |
| 6 | **Beyond README** | Was any fact sourced from README alone cross-checked against an independent source (parser / manifest / source)? |

A mis-answered checklist entry (e.g. "tests not checked", "entrypoint assumed
from README") is exactly the class of **incomplete-scan** gap the evals hunt.

---

## 4. ReBattle Adversarial Search Categories

Each ReBattle round actively hunts for conflict across these categories,
not just re-asserting each agent's facts:

1. **Contradictory evidence** — two sources assert different values for the
   same key (README vs parser, manifest vs source).
2. **Stale docs** — prose / examples / changelog that describe an old command,
   flag, default, or port the current code no longer has.
3. **Environment differences** — platform / OS / runtime-path divergence
   (Windows vs POSIX paths, default module vs installed package).
4. **Overrides** — a base config value overridden by a composed env /
   `*.override.*` / docker-compose env / CLI flag; the final resolved value
   wins, the stale base never stands.
5. **Test-vs-runtime differences** — a test (or fixture) asserting behavior
   the production source contradicts, or a mocked surface that is not real CLI.

Every detected conflict must surface as a ReBattle discrepancy keyed on its
semantic topic; the Judge resolves it on **evidence strength**, not on which
agent was louder.
