# Changelog

All notable changes to MakeWiki.skills are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2.0.0] — 2026-08-29

### Docs consolidation — accurate surface, honest statuses

A final documentation pass aligning every doc to the implemented reality:

- **Command rename**: the CLI command is `legacy-generate` (function

  `deterministic_generate`); `generate` remains as a deprecated alias. Both
  are explicitly non-authoritative / mechanical scaffold only — NOT the
  `/makewiki` path.
- **Revision engine**: the semantic revision engine is now

  `MechanicalRepairEngine` (module `makewiki_skills.revision`; `RevisionEngine`
  alias kept). It performs **mechanical repairs only** — cross-language
  code-block parity by stable `[[id:...]]` block ID and canned UNKNOWN
  evidence caveats. Anti-cliché prose rewriting is the LLM Auditor's job.
- **Four-layer claim vocabulary**: `EvidenceFact` → `MechanicalAssertion` →

  `AgentClaim` → `AdjudicatedClaim`, threaded by
  `provenance: python_fact | llm_claim | adjudicated`.
- **Honest L0–L5 statuses**: `passed` / `failed` / `pending` / `unknown` /

  `not_applicable` / `warning` per `verification/report.py`. Python never marks
  a layer `passed` without actually proving it; LLM-judged pending layers are
  reported transparently.
- Consistent Cognitive Authority Boundary wording across `SKILL.md`,

  `AGENTS.md`, `CLAUDE.md`, `references/architecture.md`,
  `references/grounding_policy.md`.
- Quick-start selection is explicit (`is_quick_start: bool` only); config

  classification is mechanical (facts only, no fuzzy narrative label);
  cross-language code blocks are matched by stable IDs, not position.

### Refactor — LLM-first, evidence-backed architecture

MakeWiki v2 splits the system cleanly along a **Cognitive Authority Boundary**:

- **Cognitive Plane (LLM)**: subagents own all comprehension, reasoning, ReBattle debate, writing, and auditing.
- **Mechanical Plane (Python)**: the toolkit only proves what can be mechanically proven — fact harvesting, AST/CLI/config parsing, L0/L1/L2, exact-block parity, `UNKNOWN` fallbacks, Quality Gate aggregation.
- **Cognitive Authority Boundary**: Python MUST NOT invent FAQ / troubleshooting / usage / workflow / install-step content; it returns `UNKNOWN` when it cannot prove something. The LLM fills those slots or leaves them marked.
- **Host Capability fallback**: `supports_subagents` / `supports_parallel_subagents` / `max_parallelism` / `supports_file_write` / `supports_web` drive parallel / sequential / solo topologies. "No subagent API" means "MakeWiki runs sequentially on one agent", not "MakeWiki cannot run".

#### Added

**Two-plane architecture & authoritative pipeline**
- Authoritative flow is LLM-orchestrated: Sizing → Scout → Claim formulation → ReBattle (Red/Blue/Green) → Judge → SemanticModel → Parallel native Writers → Auditor → Semantic Revision.
- Python is invoked only between phases as mechanical proof tooling.
- `subskills/` modules carry the per-phase subskills; the project root hosts `SKILL.md` directly so the plugin loads cleanly.

**Unified L0–L5 verification + Quality Gate**
- `VerificationOrchestrator` wires L0 syntax, L1 existence, L2 interface, L3 behavior, L4 cross-language, L5 epistemic into a single `verify-docs` run.
- New `verification/quality_gate.py` aggregates layer reports into a `QualityGateResult` (`passed`, per-layer flags, `grounding_score`, `unresolved_critical/major/minor`, `revision_rounds`) and returns a CI exit code.
- Configurable thresholds: `quality.fail_on_critical`, `quality.min_grounding_score`, `quality.allow_pending_llm_layers`.

**Claim protocol with provenance**
- `Claim` now carries `provenance` (`llm_claim` vs `python_fact`) so LLM-authored claims and Python-extracted facts are distinguishable downstream.
- `ClaimSet.from_llm_json` lets the Skill inject semantic claims (workflows, personas, FAQ-topics, troubleshooting root-causes) for Python to verify but never invent.
- Stable block IDs (`getting_started.install`, `usage.scan_json`, `config.database_url`, etc.) carry identical technical blocks across languages for exact L4 mechanical parity.

**Authoritative CLI surface (mechanical-only)**
- `sizing`, `evidence` (alias `scan`), `verify-claim`, `verify-model`, `verify-docs` (alias `verify`), `parity`, `review` (standalone `CrossLanguageReviewer`, not an alias of `parity`), `semantic-review`, `validate`, `build-site`, `export` (`html|epub|all`, **rejects pdf**), `sync-bundle` (alias `sync`, **bundle-prep only**), `rebattle-diff`, `init-config`.
- `legacy-generate` (alias `generate`, deprecated) is the mechanical scaffold only — explicitly **not** the authoritative `/makewiki` flow.
- First-party console script `makewiki = "makewiki_skills.cli:app"` registered in `pyproject.toml`.

**Bootstrap version pinning**
- `scripts/bootstrap_toolkit.py` resolves a pinned `v{version}` tag instead of moving `main`.
- Honors `MAKEWIKI_TOOLKIT_VERSION` and `MAKEWIKI_TOOLKIT_SHA256`; skill `2.0.0` ↔ toolkit `2.0.0` bound by SHA256.

**Contract tests**
- `tests/contracts/test_cli_skill_contract.py` — every documented toolkit command resolves to a registered Typer command.
- `tests/contracts/test_config_consumption_contract.py` — every `MakeWikiConfig` field is either Python-consumed or explicitly annotated LLM-consumed; no dead config.
- `tests/contracts/test_subskill_cli_contract.py` — subskill flags map to actual CLI flags.
- `tests/contracts/test_pipeline_docs_contract.py` — `legacy-generate` output contains no invented FAQ/troubleshooting and uses `UNKNOWN` markers.
- `tests/contracts/test_feature_test_contract.py` — each advertised feature (`evidence-backed`, L0–L5, Quality Gate, `sync-bundle = bundle-prep`) has at least one covering test.
- `tests/contracts/test_skill_shell_safety.py` — bans `&&`, `||`, `/dev/null`, `${}`, `!` fences, raw `$ARGUMENTS` across `tasks/**/*.md` and `references/**/*.md`.

#### Changed

- **Grounding language**: replaced the marketing phrase "zero-hallucination" with **evidence-backed** / **evidence-grounded** / **layered automated verification** across docs, skills, and packaging. Grounding Score, unresolved critical counts, and L0–L5 status are the verifiable claims.
- **Config**: every field is now either LLM-consumed (read by Skill orchestrator / writers) or Python-consumed (read by the mechanical plane). New `quality.*` thresholds wire into the Quality Gate.
- **Verifier honesty**: `verify_claims_against_codebase` no longer hardcodes "passed" / "not_applicable"; L2/L3 delegate to the real layer checks, and ungrounded claims are surfaced as `pending` for LLM judgment.
- **Generator**: `LanguageGenerator` and Jinja templates render LLM-supplied FAQ/troubleshooting/usage items only — empty slots emit `UNKNOWN` markers instead of invented prose. `_SIMPLE_TRANSLATIONS` prose-generation removed where it invented content.

#### Removed

- `src/makewiki_skills/model/task_inference.py` — regex-based `TaskInferenceEngine` (cognitive logic; no legacy version).
- `_build_faq`, `_build_troubleshooting`, `_build_usage_examples`, `_build_command_groups`, `_generate_group_description`, `_is_detailed_mode`, `_DEFAULT_INSTALL_COMMANDS`, canned "Clone the repository" install step, and `UserTask` auto-synthesis from the pipeline. The corresponding `SemanticModel` fields remain as LLM-input slots.
- `export --format pdf` — the help text and code path reject `pdf`; only `html|epub|all` remain.
- Dead config fields: removed where non-mechanical and not useful to the LLM; remaining fields are tagged LLM- or Python-consumed.

#### Fixed

- Cross-language static site index links render as clickable SPA-routed anchors.
- Docker Compose configuration pages no longer expose internal YAML path keys.
- Go/Rust source extraction patterns iterate per-pattern correctly.
- Confluence sync CDATA blocks no longer double-escape HTML entities inside code samples.

### Earlier — pre-2.0 baseline

**Dynamic project sizing and subagent budgeting**
- Tier S / M / L classification based on file count, language diversity, and configuration complexity.
- Hard cap of 10 concurrent subagents; Tier S projects use 1–2 agents to avoid unnecessary overhead.

**ReBattle competitive verification**
- Three independent analysis perspectives: Red (developer/user UX), Blue (code AST/implementation), Green (deployment/ops).
- Judge agent cross-examines and resolves disagreements before any content is written.

**Offline static wiki SPA compiler** (`src/makewiki_skills/renderer/site_compiler.py`)
- Single self-contained HTML file with no external dependencies.
- Multi-language switcher, dark/light theme toggle, local full-text search.
- Hash-based URL routing with internal link navigation and external-link indicators.

**HTML print and EPUB export** (`src/makewiki_skills/renderer/exporter.py`)
- Print-ready single-file HTML with cover page, TOC, and page breaks.
- Valid EPUB 2.0 zip archive with `toc.ncx`, styled XHTML chapters, no external dependencies.

**Confluence and Notion knowledge base sync** (`src/makewiki_skills/sync/`)
- Markdown → Atlassian Confluence Storage Format (XHTML) with space import bundle.
- Markdown → Notion Block API JSON payloads (Heading, Code, Callout, Table blocks).

**Multi-language source code extractor** (`src/makewiki_skills/toolkit/source_extractor.py`)
- Go: `flag`/`pflag` CLI flags, Cobra/Urfave commands, Gin/Echo/Chi REST routes, exported functions with doc comments.
- Rust: `clap` arg attributes, Axum/Actix route macros, `pub fn` with `///` doc comments.

**Docker Compose user-friendly config extraction**
- `extract_config_keys()` detects `services.*` structures and surfaces per-service environment variables with defaults and port bindings.

**Open-source documentation**
- `CONTRIBUTING.md` — contributor workflow, code style, and test instructions.
- `SECURITY.md` — responsible disclosure policy and sandboxing statement.
- `README.md` + `README.en.md` — developer-first homepage.

---

## [0.1.0] — 2026-07-01

Initial scaffold release.

- Multilingual documentation generation (en, zh-CN, de, fr, ja) via language-specific generator modules
- Evidence collection from CLI help, README, config files, and Markdown tables
- Cross-language consistency reviewer
- Offline static wiki compiler (first iteration, no SPA routing)
- Basic Markdown structure validator
- `run_toolkit.py` dispatcher with `scan`, `build-site`, `validate`, `review`, `verify`, `sizing` commands