# Basic Example: Single-Module Python CLI

## 1. Project Profile

- **Type**: Python CLI (Typer / Click)
- **Files**: 8 source files (Single-module)
- **Target**: `examples/sample-python-cli`

## 2. Command Invocation

```bash
/makewiki --lang en --lang zh-CN
```

## 3. Execution Flow (V3 pipeline)

1. **Orientation**: Main Agent reads high-information entries, forms an initial
   hypothesis, identifies the CLI persona and one semantic domain, and authors a
   `RepositoryBrief` + `InvestigationPlan`. (`census` / `evidence` may run as
   optional mechanical assistance, never as a prerequisite or authority.)
2. **Investigation**: One Explorer subtask returns an evidence-backed `ClaimBundle`
   for the single domain (`sample-cli greet <name>`, `--count`, `.env.example`).
3. **Semantic Synthesis**: Semantic Analyst reconciles the brief, plan, and claims
   into the canonical `SemanticModel`.
4. **Documentation Modeling & Page Planning**: Documentation Architect produces a
   `DocumentationModel`, a `DocumentationPlan`, and one `PageSpec` per page.
5. **Writing**: Parallel Language Writers author 7 pages for English and 7 pages for
   Chinese — one `PageSpec` × one language each, never machine-translated.
6. **Review → Revision**: Read-only Page Reviewer emits `ReviewFindings`; a separate
   Revision Agent implements them; re-review confirms completion (bounded rounds).
7. **Integration & Verify**: Integrator authors `SitePresentationPlan`; Python runs
   `verify-docs` (L0–L5) and the Final Semantic Auditor emits the `SemanticAuditBundle`.
8. **Site & Deliver**: Compiles `makewiki/site/index.html` and exports delivery bundles.
