# Internal Toolkit CLI API Reference




The toolkit CLI is mechanical only. All comprehension and authoring decisions
are made by the LLM-driven `/makewiki` Skill layer; this CLI returns `UNKNOWN`
rather than guessing whenever something cannot be proven from source.

The first-party console script is `makewiki` (also reachable via
`python scripts/run_toolkit.py <command>` for pinned-toolkit installs).

## Authoritative command surface

| Command           | Arguments / Flags                                          | Description                                                                                                             |
| ----------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `census`          | `<target> [--format json\                                  | human]`                                                                                                                 | Extract raw verifiable repository traits (file counts, languages, manifests, entrypoints). |
| `evidence`        | `<target> [--format json\                                  | human]`                                                                                                                 | Extract structured evidence **facts** (commands, config keys, paths). No interpretation. |
| `coverage`        | `<target> [--format json\                                  | human]`                                                                                                                 | Deterministic mechanical coverage of a discovery pass: files discovered vs inspected vs skipped vs ignored, entrypoints/configs/tests/manifests found, `uncovered_categories`, `low_confidence_facts`. Pure bookkeeping; the LLM resolves the gaps. |
| `verify-claim`    | `<claim.json> [...]`                                       | Verify one or many Claims against the codebase → per-claim L0–L5 status.                                                |
| `verify-model`    | `<semantic_model.json>`                                    | Validate a SemanticModel against the schema and evidence references.                                                    |
| `verify-docs`     | `<target> [--wiki-dir <dir>] [--lang ...] [--format json\  | human] [--semantic-audit <file>] [--semantic-model <file>]`                                                             | Unified L0–L5 verification of an existing wiki directory plus the four-state Quality Gate verdict (`passed` / `failed` / `pending_semantic_review` / `pending_mechanical_verification`). `--semantic-audit <file>` merges an LLM `SemanticAuditBundle` item-level by `review_item_id` (without it, L3/L4b/L5 are PENDING); `--semantic-model <file>` supplies the current SemanticModel to prove the bundle's `semantic_model_digest` binding (unproven or stale → L3/L4b/L5 stay PENDING). |
| `parity`          | `<target> [--lang ...]`                                    | Block-ID exact parity + aligned passages for LLM prose audit.                                                           |
| `review`          | `<wiki_dir> [--lang ...]`                                  | Standalone cross-language review: runs `CrossLanguageReviewer` over existing output on disk (not an alias of `parity`). |
| `semantic-review` | `<wiki_dir> [--lang ...] [--format json\                   | human]`                                                                                                                 | Prepare aligned passages for the Auditor subagent (LLM prose audit input). |
| `validate`        | `<wiki_dir>`                                               | Markdown quality: heading hierarchy, links, empty pages, code-block language ids.                                       |
| `lint-drafts`     | `<wiki_dir> [--structural-only]`                           | Integration-time mechanical draft hygiene lint. Full Integration mode (default) fails closed: the canonical V3 artifacts (DocumentationPlan, PageSpecs, DocumentationModel) must exist and be schema-valid, and their cross-checks (plan/spec/draft drift, disposition/gap cross-references, required sections, planned-draft completeness) run. Any missing or invalid canonical artifact is blocking. `--structural-only` runs pure-Markdown checks only and reports that cross-artifact checks were not run. Never judges page quality or semantics, never changes the Quality Gate. |
| `build-site`      | `<wiki_dir> [--theme auto\                                 | light\                                                                                                                  | dark] [--output <dir>] [--title <t>]` | Compile Markdown docs into an offline SPA HTML site. |
| `export`          | `<wiki_dir> [--format html\                                | epub\                                                                                                                   | all] [--lang <code>]` | Export single-file printable HTML and EPUB e-books. **PDF is intentionally not supported.** |
| `sync-bundle`     | `<wiki_dir> [--target all\                                 | confluence\                                                                                                             | notion] [--lang <code>]` | Prepare Confluence Storage XML / Notion Block API bundles on disk. **Does NOT publish.** |
| `init-config`     | `[target] [--lang ...]`                                    | Generate a default `makewiki.config.yaml` in the target directory.                                                      |
| `rebattle-diff`   | `<claim_set_1.json> <claim_set_2.json> [...]`              | Deterministic dispute organizer: diff two or more ClaimSets into a discrepancy matrix.                                  |

## Aliases (deprecated, retained for back-compat)

| Alias      | Refers to         | Notes                                                                  |
| ---------- | ----------------- | ---------------------------------------------------------------------- |
| `sizing`   | `census`          | Deprecated alias; outputs the same facts-only repo census.             |
| `scan`     | `evidence`        | Legacy name; outputs the same facts-only evidence bundle.              |
| `verify`   | `verify-docs`     | Same unified L0–L5 + Quality Gate run.                                 |
| `sync`     | `sync-bundle`     | Bundle-prep only; the old name implied publishing, which it never did. |

`parity` has no alias. `review` is a **standalone command** (not an alias): it
runs `CrossLanguageReviewer` over existing makewiki output on disk.

## Notes

- All commands are pure Mechanical Plane: they do not invent semantic

  conclusions. Where the layer is LLM-judged (L3 behavior, L4 prose, L5
  epistemic), Python emits the evidence and returns `pending` for the Skill
  layer's Auditor to resolve.
- `verify-docs` maps the four-state Quality Gate verdict to a CI exit policy:

  `passed` → 0, `failed` → 1, `pending_semantic_review` → 0 when
  `quality.allow_pending_llm_layers` is true (else 2), and
  `pending_mechanical_verification` → 3. Human output (the default) breaks the
  checks into separate sections — **Failed Checks**, **Pending Semantic
  Reviews**, **Unknown / Insufficient Evidence**, **Warnings** — so pending or
  unknown items are never shown as "Failed".
- `verify-docs --semantic-audit <file> [--semantic-model <file>]` merges an LLM

  `SemanticAuditBundle` item-level: each verdict adjudicates exactly one
  `review_item_id` (e.g. `L3:README.md:make build`, `L4b:README:build`,
  `L5:README.md:make build`); omitted items stay PENDING; a verdict for an
  unknown `review_item_id` rejects the whole bundle. The merge only adjudicates
  items in the report's `review_items` registry, and merged checks carry
  `verification_source = "semantic_audit_bundle"` plus the Auditor's STRUCTURED
  provenance (`check.provenance`: `auditor`, `rationale_summary`,
  `evidence_refs`, `confidence`, `audited_at`). If the bundle declares a
  `semantic_model_digest` but no `--semantic-model` is supplied, the model
  binding is UNPROVEN and L3/L4b/L5 stay PENDING (never silently trusted).
- `export` rejects `--format pdf` with an explicit error.
- `sync-bundle` writes prepared bundles under `<wiki_dir>/sync/<platform>/<lang>/`.

  It does not talk to Confluence or Notion APIs; that responsibility belongs
  to a future publishing step the Skill layer may schedule.