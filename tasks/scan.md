# Task: Mechanical Fact Assistance & Explorer-Family Focus Variants (机械事实辅助与勘探族焦点变体)

## Overview

Repository orientation and investigation in V3 are **cognitive, LLM-owned**.
This task documents two supporting concerns:

1. **Optional mechanical fact assistance** — the Python `census` / `evidence` /
   `coverage` commands return raw, verifiable repository traits and facts.
   They are **optional supporting material, never a prerequisite or an
   authority**: they never decide semantic domains, meaning, visibility,
   abstraction, or the investigation topology. The LLM (Repository Orientation,
   Explorer) owns all interpretation (see `tasks/orient.md`, `tasks/investigate.md`,
   `references/v3/BASELINE.md` §3.1).
2. **Explorer-family focus variants** — when mechanical tooling fails or a
   complex repo risks hidden entrypoints, the Main Agent dispatches a
   **Recovery Explorer** or a **Blind Coverage Reviewer**. Both are *focus
   variants* of the stable **Explorer** role family (see `tasks/investigate.md`),
   not new architecture-level role families, and neither changes what
   investigation produces (`ClaimBundle`s, never V2 `SearchLedger`s).

---

## 1. Mechanical Facts Are Optional Assistance, Never an Authority

The Main Agent may run `census` / `evidence` / `coverage` on the target to obtain
objective, verifiable traits (file counts, languages, manifests, commands, config
keys, paths). Key boundaries:

- **Optional**: orientation and investigation proceed from direct `Glob` / `Grep` /
  `Read` inspection even when Python tooling is skipped. Census is **not** a
  mandatory Phase 0 prerequisite; it does not dictate the investigation plan.
- **Facts only**: `census` measures traits; `evidence` returns a facts-only JSON
  bundle; `coverage` reports which files/configs/tests/manifests were discovered
  vs inspected vs pruned. Python never interprets meaning.
- **Evidence channel, not authority**: if Python evidence conflicts with direct
  source inspection, the Main Agent investigates directly.
- **Never a topology authority**: investigation decomposition is decided by the
  authored `InvestigationPlan` (`tasks/investigate.md` §1) — never "synthesized
  from census needs" (BASELINE §3.1).

---

## 2. Recovery Explorer (mechanical-tool failure)

When mechanical extraction encounters errors or degraded coverage, the Main Agent
spawns a **Recovery Explorer** — an Explorer-family focus variant. It is **not** a
separate "Recovery Scout" role family.

- **Trigger conditions**:
  - Mechanical tool throws an AST / syntax / unhandled-format error.
  - Scanner returns 0 facts or skips a known-critical directory.
  - A claim sets `confidence: low` or flags critical paths as `unresolved`.
  - Evidence conflicts between doc comments and implementation.
- **Mandate**: relies exclusively on **direct cognitive inspection**
  (`Glob`, `Grep`, `Read`); reads raw source, extracts ground-truth
  symbols/schemas/entrypoints, and resolves ambiguities directly.
- **Output**: returns a **`ClaimBundle`** for its domain (per
  `tasks/investigate.md` §3), never a V2 `<search_ledger>` block. The preserved
  V2 `SearchLedger` parser (`src/makewiki_skills/model/search_ledger.py`) remains
  only as a backward-compatibility asset for legacy bundles; new work emits
  `ClaimBundle`s.

---

## 3. Blind Coverage Reviewer (complex / large repositories)

For complex, large, or polyglot repositories, the Main Agent may deploy an
independent **Blind Coverage Reviewer** — also an Explorer-family focus variant —
before publishing reviewed drafts:

- **Blind independence**: the reviewer is **not** given prior `ClaimBundle`s or
  generated drafts — only the raw repository path and, optionally, census traits.
  It independently re-explores to surface hidden entrypoints, forgotten
  sub-packages, undeclared plugins, config overrides, or missing workflows.
- **Discrepancy loop**: the Main Agent compares the reviewer's findings against
  the existing claim pool. If unexpected core subsystems were missed or placed in
  `unresolved` / `newly_discovered_areas`, the Main Agent updates the
  `InvestigationPlan` and dispatches targeted Explorer subtasks before proceeding.

---

## 4. Boundaries

- Neither variant is a new role family; both are synthesized as Explorer-family
  focus variants against the stable role families (SKILL §6).
- Neither variant makes IA decisions, adjudicates semantic meaning, or writes
  documentation — they produce `ClaimBundle`s / findings for the Main Agent.
- Census / evidence / coverage never replace LLM judgment of what the repository
  means, never decide visibility/abstraction, and never set the investigation
  topology.
