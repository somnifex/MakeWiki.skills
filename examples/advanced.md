# Advanced Example: Multi-Module Go + React Monorepo


## 1. Project Profile

- **Type**: Go Gin Backend + React Frontend (Monorepo)
- **Files**: 1800+ source files (Monorepo)
- **Features**: Docker Compose, MySQL, Redis, REST API routes, multi-architecture build

## 2. Command Invocation

```bash
/makewiki --lang en --lang zh-CN --theme dark
```

## 3. Execution Flow (V3 pipeline)

1. **Orientation**: Main Agent reads high-information entries, forms an initial
   hypothesis, identifies end-user + operator + developer personas and major semantic
   domains (backend, frontend, ops/deployment, public & management APIs). Authors a
   `RepositoryBrief` + `InvestigationPlan` of coherent domains. `census` detects
   Go + Node ecosystems, monorepo workspaces, Docker/CI configs — **optional** raw
   evidence only, never a topology authority.
2. **Investigation**: Explorer subtasks (one coherent semantic domain each) return
   evidence-backed `ClaimBundle`s — e.g. the API surface (40+ REST routes), runtime
   config/env, deployment topology. A **Blind Coverage Reviewer** (Explorer-family
   focus variant) independently re-explores to catch hidden entrypoints; a **Recovery
   Explorer** handles any mechanical-tool failures via direct inspection.
3. **Semantic Synthesis**: Semantic Analyst reconciles the brief, plan, and all
   `ClaimBundle`s into the canonical `SemanticModel`. Ordinary ambiguity is re-checked
   against evidence; only a genuinely hard dispute escalates to adversarial ReBattle
   (a deterministic `rebattle-diff` organizer never decides truth).
4. **Documentation Modeling & Page Planning**: Documentation Architect produces a
   `DocumentationModel` (personas, capabilities, journeys, interface references incl.
   operator/management-API surfaces where evidence supports them), a `DocumentationPlan`,
   and one language-neutral `PageSpec` per page_id.
5. **Writing**: Parallel Language Writers author 25 pages per language — one
   page × one language each from the shared PageSpec, natively, never machine-translated,
   with stable `[[id:...]]` / section markers for 100% cross-language block parity.
6. **Review → Revision**: Read-only Page Reviewer emits `ReviewFindings`; a separate
   Revision Agent implements them; re-review confirms completion (bounded rounds).
7. **Integration & Verify**: Integrator authors `SitePresentationPlan` from approved
   page specs; Python runs `verify-docs` (L0–L5) and the Final Semantic Auditor emits
   the authoritative `SemanticAuditBundle`.
8. **Site & Deliver**: Compiles the standalone SPA static wiki at
   `makewiki/site/index.html`, then exports bundles:

   ```bash
   python scripts/run_toolkit.py export makewiki --format all --lang zh-CN
   python scripts/run_toolkit.py sync makewiki --target all --lang zh-CN
   ```
