# AGENTS.md

Instructions for AI coding assistants using MakeWiki.skills v2.

## What this is

MakeWiki.skills is a **multi-agent skill set + Python toolkit** that compiles
evidence-backed, multilingual user documentation and an interactive offline
static website. The architecture is **LLM-first**: the Skill layer (cognitive
plane) decides what the repository means; the Python toolkit (mechanical
plane) proves what can be mechanically proven. Documentation is
evidence-backed via layered automated verification (L0 - L5) and a single
Quality Gate.

---

## Two-Plane Architecture (双平面拓扑)

```yaml
cognitive_plane:
  owner: "LLM (Skill + Subagents)"
  decides: "Project intent, FAQ, troubleshooting, workflows, Diátaxis structure, hedging"
  forbidden: "Mechanical proof Python can do deterministically"

mechanical_plane:
  owner: "Python toolkit (run_toolkit.py)"
  proves: "Sizing, evidence extraction, L0/L1/L2/L4-exact, schema, parity, site, export, sync-bundle"
  forbidden: "Inventing narrative content (FAQ / troubleshooting / usage)"

bridge:
  decision: "Quality Gate (honest four-state verdict: passed / pending_semantic_review / pending_mechanical_verification / failed; CI exit code 0 / 1 / 0-or-2 / 3)"
```

### Cognitive Authority Boundary

LLM Agents are the authoritative decision makers for semantic work. Python
tooling MUST NOT invent semantic conclusions. When deterministic tooling
cannot mechanically establish a fact, it MUST return UNKNOWN rather than
guess. Python-generated semantic conclusions MUST NOT override LLM Agent
adjudication in the authoritative `/makewiki` path.

- Python MUST NOT invent semantic conclusions. When Python cannot prove

  something it returns `UNKNOWN`, never a guess.
- LLM MUST trust Python's mechanical proofs and only add semantic

  interpretation on top.
- The Quality Gate is the single cross-plane decision point.

### Host Capability Fallback

| Capability                    | parallel      | sequential | solo (no subagents) |
| ----------------------------- | ------------- | ---------- | ------------------- |
| `supports_subagents`          | yes           | yes        | no                  |
| `supports_parallel_subagents` | yes           | no         | no                  |
| `max_parallelism`             | host-reported | 1          | 1                   |
| `supports_file_write`         | yes           | yes        | host-dependent      |
| `supports_web`                | yes           | yes        | host-dependent      |

The Main Agent inspects host capability and adapts the topology without
losing semantics. "No subagent API" means "MakeWiki runs sequentially on
one agent", not "MakeWiki cannot run."

---

## Skills

```bash
claude --plugin-dir /path/to/MakeWiki.skills

/makewiki --lang en --lang zh-CN          # Full LLM-orchestrated flow: Sizing -> Scout -> ReBattle -> Writers -> Auditor -> Quality Gate -> Site
/makewiki-site ./makewiki                 # Compile Markdown docs into offline static HTML website (mechanical)
/makewiki-scan                            # Inspect evidence, assess Tier (S/M/L), and view project brief
/makewiki-review                          # Cross-language parity + semantic review (mechanical pre-alignment + LLM judgment)
/makewiki-validate ./makewiki             # Markdown structure & link validation
/makewiki-init                            # Generate makewiki.config.yaml with agent, site, delivery, quality options
/makewiki-export                          # Compile Markdown into printable HTML & EPUB e-books (--format html|epub|all; rejects pdf)
/makewiki-sync                            # Prepare Confluence Storage XML / Notion Block API sync bundles (bundle prep only; does NOT publish)
```

The authoritative CLI commands (from the Python toolkit, mechanical only):

```bash
python scripts/run_toolkit.py sizing <target>
python scripts/run_toolkit.py evidence <target> --format json     # alias: scan
python scripts/run_toolkit.py verify-docs <target>                # alias: verify
python scripts/run_toolkit.py verify-claim <claim.json>
python scripts/run_toolkit.py verify-model <semantic_model.json>
python scripts/run_toolkit.py parity <target> --lang ...
python scripts/run_toolkit.py review <wiki_dir>            # standalone CrossLanguageReviewer (NOT an alias of parity)
python scripts/run_toolkit.py semantic-review <wiki_dir>
python scripts/run_toolkit.py validate <wiki_dir>
python scripts/run_toolkit.py build-site <wiki_dir> --theme auto
python scripts/run_toolkit.py export <wiki_dir> --format html|epub|all --lang <code>
python scripts/run_toolkit.py sync-bundle <wiki_dir> --target confluence|notion --lang <code>
python scripts/run_toolkit.py rebattle-diff <claim_files...>
python scripts/run_toolkit.py init-config <target>
python scripts/run_toolkit.py legacy-generate <target>     # alias: generate (deprecated)
```

`export` rejects `--format pdf`. `sync-bundle` prepares bundles on disk
and does NOT publish. `legacy-generate` (alias `generate`, deprecated) is the
mechanical scaffold only — it is **not** the authoritative `/makewiki` flow.
`review` is a standalone command (runs `CrossLanguageReviewer`), not an alias
of `parity`.

---

## Autonomous & Subagent-First Rules

1. **LLM-First Cognitive Plane**: All code comprehension, multi-perspective

   extraction, ReBattle debate, writing, and review are driven by
   autonomous **Subagents** using their LLM reasoning and inspection tools
   (`Glob`, `Grep`, `Read`, `Edit`). Python is strictly reserved as
   mechanical proof tooling (sizing, evidence extraction, L0 / L1 / L2 / L4-
   exact, parity, site, export, sync-bundle).
2. **Cognitive Authority Boundary**: Python never invents FAQ / troubleshooting

   / usage / workflow content; it returns `UNKNOWN` instead. The LLM fills
   those slots or marks them absent.
3. **Dynamic Subagent Role Synthesis**: The orchestrator dynamically

   configures specialized subagent roles based on repository characteristics
   (monorepos, FFI bindings, plugin ecosystems) within an elastic budget
   capped at 10, honoring host capability (parallel / sequential / solo).
4. **Mandatory 4D Self-Reflection**: Every subagent runs an internal self-

   critique loop before submitting claims or writing documents:
   - Grounding check: every command / key cited with real code lines.
   - Parity check: 100% code block and parameter match.
   - Anti-cliché check: strip binary tropes ("不是而是"), buzzwords ("收敛"),
     and trailing colons.
   - Adversarial defense: hedge or retract unprovable assertions.
5. **Zero Human Intervention**: Execute end-to-end autonomously from the

   initial skill invocation. Never pause to ask intermediate confirmation
   questions (e.g. outline approval, scan mode choices). Auto-select defaults
   and self-heal in place.
6. **No AI Clichés**: Ban binary tropes ("不是而是"), abstract buzzwords

   ("收敛"), and trailing colons. Write natural, professional engineer prose.
7. **Code Block Parity (keyed on stable IDs)**: Every technical fenced code

   block MUST carry a stable block ID `[[id:<slug>]]` (an untagged technical
   block is an **L4a failure**; exemption only via
   `[[parity:ignore reason="..."]]`). Every multilingual REVIEWABLE H2
   section MUST carry a stable section marker `<!-- makewiki:section=<slug> -->`;
   single-language output may omit markers. Duplicate section or block IDs
   within one document are L4a failures. Section ORDER may differ
   per language (native independent writing); all cross-language parity and
   review is keyed on stable block + section IDs, never on heading text or
   heading position.
8. **Quality Gate Before Shipping**: Run `verify-docs` and read the

   `QualityGateResult`; resolve failed or pending layers before presenting
   the final report. The LLM Auditor persists its L3 / L4b / L5 verdicts into a
   machine-readable `SemanticAuditBundle` JSON, consumed by
   `verify-docs --semantic-audit <file>` (a flag, not a separate command);
   a stale bundle (its `documents_digest` no longer matches the documents) is
   rejected and must be re-audited.
9. **Zero Pollution**: Skill-first; run Python tools in temporary isolated

   environments when needed, and clean up immediately.

---

## Quality Gate

The single decision over all verification layers, reported as an honest
four-state verdict (`passed` / `pending_semantic_review` /
`pending_mechanical_verification` / `failed`) mapped to a CI exit policy.
Owned by `verify-docs`; consumed by the Skill's audit step and CI.

```yaml
quality_gate:
  verdict: "passed | pending_semantic_review | pending_mechanical_verification | failed"
  # ci_exit_code: passed -> 0, failed -> 1, pending_semantic_review -> 0 (allow_pending_llm_layers) or 2,
  #               pending_mechanical_verification -> 3
  layers:
    - L0 syntax (mechanical)
    - L1 existence (mechanical)
    - L2 interface (mechanical)
    - L3 behavior (LLM-judged; Python provides evidence list)
    - L4 cross_language (Python exact + LLM prose)
    - L5 epistemic (LLM over-assertion review)
  thresholds:
    quality.min_grounding_score: 1.0
    quality.allow_pending_llm_layers: true
  result_fields:
    passed: bool
    syntax_passed, existence_passed, interface_passed,
    behavior_passed, cross_language_passed, epistemic_passed: bool
    grounding_score: float
    unresolved_critical, unresolved_major, unresolved_minor: int
    revision_rounds: int
    details: dict
```

---

## Structure

```
SKILL.md                 Main skill definition
tasks/                   Phase task definitions (scan, rebattle, write, review, site, export, sync)
subskills/               Modular subskills (scan, site, review, validate, init, export, sync)
scripts/                 Toolkit launcher and bootstrapping scripts
references/              Architecture, Diátaxis, Anti-cliché, Schemas, API docs, Grounding policy
templates/               Config and report templates
examples/                Usage examples & sample test fixtures
src/makewiki_skills/     Python toolkit implementation
tests/                   Automated test suite (unit, integration, contracts)
```

The project root holds `SKILL.md` directly (not under `skills/`) so it sits
at the plugin's load path. `subskills/` hosts the per-phase subskill
modules (`makewiki-scan`, `makewiki-site`, etc.).

---

## Tests

```bash
uv sync --all-extras && uv run pytest --basetemp=.pytest_temp
```