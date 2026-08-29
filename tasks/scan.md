# Task: Project Reconnaissance & Sizing (勘探与规模判定)

## Overview

Reconnaissance is Phase 0 & 1 of the MakeWiki pipeline. It assesses project complexity (Tier S / M / L), allocates the subagent budget, and collects structural and interface evidence from the repository.

---

## 1. Complexity Sizing Criteria (Phase 0)

| Tier       | Source File Count | Entrypoint Characteristics                  | Subagent Budget  | ReBattle Strategy                                             |
| ---------- | ----------------- | ------------------------------------------- | ---------------- | ------------------------------------------------------------- |
| **Tier S** | < 15 files        | Single script/module, minimal config        | 1 ~ 2 Subagents  | Single-pass multi-perspective prompt review (0 debate rounds) |
| **Tier M** | 15 ~ 80 files     | 5 ~ 15 CLI commands, moderate config        | 3 ~ 5 Subagents  | Red vs Blue (1 debate round)                                  |
| **Tier L** | > 80 files        | Monorepo, multiple services, multi-language | 5 ~ 10 Subagents | Red + Blue + Green (2 debate rounds + Judge)                  |

---

## 2. Reconnaissance Extraction Scope (Phase 1)

### Scout-Structure

- **Manifests**: `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`
- **Build Tools**: `Makefile`, `CMakeLists.txt`, `Taskfile.yml`, `Justfile`
- **Deployment**: `Dockerfile`, `docker-compose.yml`, Kubernetes manifests, GitHub Actions / CI workflows
- **Directory Layout**: Top-level directory tree, source directory boundaries

### Scout-Surface

- **CLI Commands**: Typer, Click, Argparse, Cobra, Clap flags, arguments, help texts
- **API Endpoints**: Gin, Echo, FastAPI, Flask, Express, Axum REST route decorators
- **Configuration**: `.env.example`, `config.yaml`, `settings.json`, environment variable references
- **Existing Docs**: `README.md`, `CHANGELOG.md`, existing markdown files

---

## 3. Toolkit Execution Commands

```bash
# Assess complexity tier and subagent budget
python scripts/run_toolkit.py sizing <target_path> --format json

# Extract evidence facts into structured JSON
python scripts/run_toolkit.py scan <target_path> --format json
```