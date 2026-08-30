# Advanced Example: Multi-Module Go + React Monorepo

## 1. Project Profile

- **Type**: Go Gin Backend + React Frontend (Monorepo)
- **Files**: 1800+ source files (Monorepo)
- **Features**: Docker Compose, MySQL, Redis, REST API routes, multi-architecture build

## 2. Command Invocation

```bash
/makewiki --lang en --lang zh-CN --theme dark
```

## 3. Autonomous Execution Flow

1. **Phase 0 (Census)**: Census detects Go + Node ecosystems, monorepo workspaces, Docker/CI configs. Main Agent dynamically plans parallel specialized scouts from the Archetype Library.
2. **Phase 1 (Scout)**:
   - `Scout-Structure`: Maps `docker-compose.yml`, `go.mod`, `package.json`, Makefile.
   - `Scout-Surface`: Discovers 40+ REST API routes, Cobra CLI flags, and environment variables.
3. **Phase 2 (ReBattle)**:
   - `DX Debater`: Drafts 5-minute quickstart with Docker and local binary setup.
   - `AST Truth Debater`: Rejects unreleased experimental flags by checking Gin handler AST.
   - `Ops Debater`: Extracts environment variables and per-service port bindings from Docker Compose.
   - `Judge`: Adjudicates claims and synthesizes canonical `SemanticModel`.
4. **Phase 3 (Writers)**: Parallel English and Chinese writers produce 25 pages each.
5. **Phase 4 (Review)**: Mechanical check confirms 100% code block parity and zero AI clichés.
6. **Phase 5 (Site)**: Compiles standalone SPA static wiki at `makewiki/site/index.html`.
7. **Export & Sync**:

   ```bash
   python scripts/run_toolkit.py export makewiki --format all --lang zh-CN
   python scripts/run_toolkit.py sync makewiki --target all --lang zh-CN
   ```