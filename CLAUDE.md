# MakeWiki.skills v3

This repository contains the multi-agent skills and Python toolkit behind `/makewiki`.

## Architecture (LLM-First, Evidence-Backed)

MakeWiki runs on **two planes** separated by a Cognitive Authority Boundary:

- **Cognitive Plane (LLM / Skill layer)**: decides what the repository means —

  project intent, FAQ, troubleshooting, usage examples, workflows, Diátaxis
  structure, hedging. Forbidden from re-doing mechanical proof Python can do
  deterministically.
- **Mechanical Plane (Python toolkit)**: proves what can be mechanically proven —

  census, evidence extraction, AST / CLI / config / manifest parsing, L0 / L1 /
  L2 / L4-exact, schema validation, parity, static site, export, sync-bundle,
  Quality Gate. Forbidden from inventing narrative content; returns `UNKNOWN`
  when it cannot prove a slot.

The **Quality Gate** is the single decision point over L0 - L5. It reports an
honest four-state verdict — `passed`, `pending_semantic_review`,
`pending_mechanical_verification`, or `failed` — mapped to a CI exit policy
(0 / 1 / 0-or-2 / 3). `passed` requires every layer adjudicated and
non-blocking. It is the only place where the two planes meet.

### Cognitive Authority Boundary

Main Agent LLM is the sole runtime orchestrator. Subagents own cognitive work.
Python owns no scheduling or semantic decisions. Python is an auditable
evidence channel, not an infallible authority. If Python evidence conflicts with
direct source inspection, the Main Agent must investigate. When deterministic
tooling cannot mechanically establish a fact, it MUST return UNKNOWN rather than
guess. Mechanical tool failures produce degraded mechanical verification,
never cognitive failure; the Main Agent may spawn Recovery Explorers for direct
inspection.

When a host has **no subagent API**, MakeWiki runs sequentially on one agent —
the Main Agent assumes each role in sequence. No semantics are lost, only
wall-clock changes.

## What is in the repo

- `SKILL.md` — authoritative LLM-orchestrated skill definition
- `subskills/` — modular subskills (`makewiki-scan`, `makewiki-site`,

  `makewiki-review`, `makewiki-validate`, `makewiki-init`, `makewiki-export`,
  `makewiki-sync`)
- `src/makewiki_skills/` — Python toolkit (scanner, claim model, semantic

  model, verification L0 - L5, Quality Gate, site compiler, exporter,
  sync tools, bootstrap)
- `tests/` — automated unit, integration, and contract tests

## Available skills

- `/makewiki` — full LLM-orchestrated flow (Repository Orientation ->

  InvestigationPlan -> Investigation Subtasks -> ClaimBundles -> Semantic
  Synthesis -> DocumentationModel -> DocumentationPlan/PageSpecs -> Page
  Writing -> Independent Review -> Revision -> Integration -> Verification ->
  Quality Gate -> Site). Authoritative.
- `/makewiki-site` — build offline static website from generated markdown

  (mechanical).
- `makewiki-export` — compile markdown into printable HTML & EPUB e-books

  (`--format html|epub|all`; rejects `pdf`).
- `makewiki-sync` — prepare Confluence Storage XML and Notion Block API sync

  payloads (bundle prep only; does NOT publish).
- `/makewiki-scan` — inspect project evidence and repository fact census.
- `/makewiki-review` — prepare cross-language parity and aligned passages for

  LLM semantic review.
- `/makewiki-validate` — validate markdown structure and links (L0 helper).
- `/makewiki-init` — generate default `makewiki.config.yaml`.

## Authoritative CLI surface

Python toolkit commands (mechanical only):

| Command                  | Alias    | Purpose                                                                                                         |
| ------------------------ | -------- | --------------------------------------------------------------------------------------------------------------- |
| `census`                 | `sizing` | Raw verifiable repo traits census (file counts, langs, manifests)                                               |
| `evidence`               | `scan`   | Deterministic fact extraction (JSON / human)                                                                    |
| `coverage <target>`      | —        | Discovery coverage report: files/tests/configs/manifests discovered vs read, pruned paths, uncovered ecosystems |
| `verify-claim <json>`    | —        | Verify one or many Claims against the codebase                                                                  |
| `verify-model <json>`    | —        | Schema + evidence-ref validation for a SemanticModel                                                            |
| `verify-docs <target>`   | `verify` | Unified L0 - L5 verification + Quality Gate + exit code                                                         |
| `parity <target>`        | —        | L4 exact-block parity + aligned passages                                                                        |
| `review <wiki_dir>`      | —        | Standalone cross-language review (runs `CrossLanguageReviewer`)                                                 |
| `semantic-review <dir>`  | —        | Aligned passages for LLM cross-language review                                                                  |
| `validate <wiki_dir>`    | —        | Markdown structure & link validation                                                                            |
| `build-site <wiki_dir>`  | —        | Compile Markdown into offline SPA HTML site                                                                     |
| `export <wiki_dir>`      | —        | `--format html                                                                                                  | epub | all`; **rejects pdf** |
| `sync-bundle <wiki_dir>` | `sync`   | Prepare Confluence / Notion bundles; does NOT publish                                                           |
| `init-config <target>`   | —        | Generate default `makewiki.config.yaml`                                                                         |
| `rebattle-diff <files>`  | —        | Deterministic dispute organizer over multiple ClaimSets                                                         |

`review` is a standalone command, not an alias of `parity`.

## Working notes

- **Autonomous execution**: complete all phases end-to-end without pausing

  for intermediate confirmation.
- **Subtask-first planning**: The workflow uses stable role families (Explorer,

  Semantic Analyst, Documentation Architect, Writer, Reviewer, Integrator; Main
  Agent = Orchestrator). The Main Agent **dynamically synthesizes SubtaskSpecs**
  from the authored InvestigationPlan / DocumentationPlan within
  `agent.max_subagents` and host `max_parallelism` — it never synthesizes new
  architecture-level role families from an Archetype Library.
- **ReBattle = hard-conflict escalation**: ordinary ambiguity is resolved by
  re-checking evidence or a targeted `conflict_resolution` subtask; only a
  genuinely hard dispute escalates to adversarial ReBattle. The mechanical
  dispute organizer (`rebattle-diff`) is optional and never decides truth.
- **Natural human engineer tone**: ban AI clichés (`不是……而是……`, `收敛`,

  `这是`, trailing colons). See `references/anti_ai_cliche.md`.
- **Independent generation per language** from the semantic model; no machine

  translation.
- **Code blocks must match 100% across all languages.**
- **Ephemeral execution**: keep environments clean and remove temporary

  artifacts.
- **Version binding**: skill version (`3.0.0`) ↔ toolkit version (`3.0.0`)

  via the bootstrap script (`MAKEWIKI_TOOLKIT_VERSION`, plus
  `MAKEWIKI_TOOLKIT_COMMIT` for a Git install and
  `MAKEWIKI_TOOLKIT_ARCHIVE_SHA256` for an Archive install).

## Build & Test

```bash
uv sync --all-extras
uv run pytest --basetemp=.pytest_temp
```