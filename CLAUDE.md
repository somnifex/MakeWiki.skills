# MakeWiki.skills v2

This repository contains the multi-agent skills and Python toolkit behind `/makewiki`.

## Architecture (LLM-First, Evidence-Backed)

MakeWiki runs on **two planes** separated by a Cognitive Authority Boundary:

- **Cognitive Plane (LLM / Skill layer)**: decides what the repository means —

  project intent, FAQ, troubleshooting, usage examples, workflows, Diátaxis
  structure, hedging. Forbidden from re-doing mechanical proof Python can do
  deterministically.
- **Mechanical Plane (Python toolkit)**: proves what can be mechanically proven —

  sizing, evidence extraction, AST / CLI / config / manifest parsing, L0 / L1 /
  L2 / L4-exact, schema validation, parity, static site, export, sync-bundle,
  Quality Gate. Forbidden from inventing narrative content; returns `UNKNOWN`
  when it cannot prove a slot.

The **Quality Gate** is the single decision point over L0 - L5. It reports an
honest four-state verdict — `passed`, `pending_semantic_review`,
`pending_mechanical_verification`, or `failed` — mapped to a CI exit policy
(0 / 1 / 0-or-2 / 3). `passed` requires every layer adjudicated and
non-blocking. It is the only place where the two planes meet.

### Cognitive Authority Boundary

LLM Agents are the authoritative decision makers for semantic work. Python
tooling MUST NOT invent semantic conclusions. When deterministic tooling
cannot mechanically establish a fact, it MUST return UNKNOWN rather than
guess. Python-generated semantic conclusions MUST NOT override LLM Agent
adjudication in the authoritative `/makewiki` path.

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

- `/makewiki` — full LLM-orchestrated flow (`sizing -> scout -> rebattle ->

  parallel writers -> auditor / quality gate -> site compile`). Authoritative.
- `/makewiki-site` — build offline static website from generated markdown

  (mechanical).
- `makewiki-export` — compile markdown into printable HTML & EPUB e-books

  (`--format html|epub|all`; rejects `pdf`).
- `makewiki-sync` — prepare Confluence Storage XML and Notion Block API sync

  payloads (bundle prep only; does NOT publish).
- `/makewiki-scan` — inspect project evidence and assess sizing tier.
- `/makewiki-review` — prepare cross-language parity and aligned passages for

  LLM semantic review.
- `/makewiki-validate` — validate markdown structure and links (L0 helper).
- `/makewiki-init` — generate default `makewiki.config.yaml`.

## Authoritative CLI surface

Python toolkit commands (mechanical only):

| Command                  | Alias      | Purpose                                                            |
| ------------------------ | ---------- | ------------------------------------------------------------------ |
| `sizing`                 | —          | Tier (S / M / L) + subagent budget                                 |
| `evidence`               | `scan`     | Deterministic fact extraction (JSON / human)                       |
| `coverage <target>`      | —          | Deterministic discovery coverage (JSON / human)                    |
| `verify-claim <json>`    | —          | Verify one or many Claims against the codebase                     |
| `verify-model <json>`    | —          | Schema + evidence-ref validation for a SemanticModel               |
| `verify-docs <target>`   | `verify`   | Unified L0 - L5 verification + Quality Gate + exit code            |
| `parity <target>`        | —          | L4 exact-block parity + aligned passages                           |
| `review <wiki_dir>`      | —          | Standalone cross-language review (runs `CrossLanguageReviewer`)    |
| `semantic-review <dir>`  | —          | Aligned passages for LLM cross-language review                     |
| `validate <wiki_dir>`    | —          | Markdown structure & link validation                               |
| `build-site <wiki_dir>`  | —          | Compile Markdown into offline SPA HTML site                        |
| `export <wiki_dir>`      | —          | `--format html                                                     | epub | all`; **rejects pdf** |
| `sync-bundle <wiki_dir>` | `sync`     | Prepare Confluence / Notion bundles; does NOT publish              |
| `init-config <target>`   | —          | Generate default `makewiki.config.yaml`                            |
| `rebattle-diff <files>`  | —          | Deterministic dispute organizer over multiple ClaimSets            |
| `legacy-generate`        | `generate` | Mechanical scaffold only (deprecated) — NOT the authoritative flow |

`legacy-generate` (alias `generate`, deprecated) is the non-authoritative
mechanical scaffold; the authoritative flow is `/makewiki` (LLM-orchestrated).
`review` is a standalone command, not an alias of `parity`.

## Working notes

- **Autonomous execution**: complete all phases end-to-end without pausing

  for intermediate confirmation.
- **Subagent budget**: Tier S (1-2 agents), Tier M (3-5 agents),

  Tier L (5-10 agents max). Honor host capability fallback.
- **ReBattle cross-examination** before writing; mechanical dispute organizer

  (`rebattle-diff`) is optional.
- **Natural human engineer tone**: ban AI clichés (`不是……而是……`, `收敛`,

  `这是`, trailing colons). See `references/anti_ai_cliche.md`.
- **Independent generation per language** from the semantic model; no machine

  translation.
- **Code blocks must match 100% across all languages.**
- **Ephemeral execution**: keep environments clean and remove temporary

  artifacts.
- **Version binding**: skill version (`2.0.0`) ↔ toolkit version (`2.0.0`)

  via the bootstrap script (`MAKEWIKI_TOOLKIT_VERSION`, plus
  `MAKEWIKI_TOOLKIT_COMMIT` for a Git install and
  `MAKEWIKI_TOOLKIT_ARCHIVE_SHA256` for an Archive install).

## Build & Test

```bash
uv sync --all-extras
uv run pytest --basetemp=.pytest_temp
```