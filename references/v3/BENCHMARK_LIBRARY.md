# Benchmark Reference Library

**Runtime authority for the advisory benchmark layer.** This document defines
the corpus layout, the selection protocol, and the mechanical contracts for
the Benchmark Reference Layer — the component that lets MakeWiki Writers and
Reviewers consult a small, curated set of excellent external documentation
examples as *presentation* references.

**NOT runtime authority for anything else.** This layer changes no
verification-layer semantics: L0 - L5, the Quality Gate, evidence grounding,
and provenance honesty are all unchanged by it.

---

## 1. Purpose and the two groundings

The benchmark layer exists to make generated documentation *communicate*
better — not to know more. It supplies **reference grounding** only:

- **Evidence grounding** answers *what the target project is*: capabilities,
  parameters, contracts, behavior. It is sourced exclusively from repository
  evidence, ClaimBundles, the SemanticModel, and API contracts. It is never
  sourced from benchmarks.
- **Reference grounding** answers *how excellent documentation organizes
  similar complexity*: ordering, section shapes, progressive disclosure,
  example strategy, lookup experience. It is sourced only from the benchmark
  corpus, and only as advisory context.

Copying a benchmark's facts, terminology, API/config values, defaults,
limits, or factual claims into a target page is a **critical defect** — it
is ungrounded content by definition. The authority order is absolute:

```text
repository evidence  >  PageSpec  >  ReferenceProfile  >  benchmark examples
```

`Target intent is authoritative. Benchmark archetype is advisory.` A page
whose PageSpec says `concept` stays a `concept` even when the selected
benchmark is a quickstart; referencing Stripe never turns a page into an API
reference. Cross-category transfer is explicitly allowed and expected — the
Selector is free to pick whatever examples genuinely help the page, across
all category boundaries.

## 2. Corpus layout (four separable layers)

```text
benchmarks/
├── README.md               # layer map and curation rules
├── registry.yaml           # curated metadata: ids, providers, pointers, licensing
├── sources/<provider>/     # raw fetched pages — local cache, never required
├── normalized/<id>.yaml    # structural summaries of excellent pages
├── patterns/<id>.yaml      # distilled, source-agnostic documentation patterns
└── index/benchmark-index.json  # generated compact stage-1 index
```

The four layers must stay distinguishable: raw source material, normalized
structural summaries, distilled patterns, and retrieval metadata never
collapse into one another. The registry defaults every entry to
`acquire: metadata-only`; committing a provider's prose requires an explicit
`acquire: full` entry plus a recorded license or usage note. The library's
core value is the `patterns/` layer — distilled principles, not a mirror of
external doc sites.

## 3. Mechanical toolkit (Python plane)

| Command | Contract |
| :--- | :--- |
| `benchmark-index <corpus>` | Validate the corpus (schema + cross-links, fail closed) and deterministically (re)generate `index/benchmark-index.json`. Metadata only — never prose. |
| `benchmark-acquire <ids...> --corpus <dir>` | Fetch source pages into `sources/<provider>/` with sidecar metadata (URL, retrieval time, sha256). Refuses `metadata-only` entries outright; unlocking a fetch is a registry curation decision, never a CLI bypass. |
| `verify-reference-profile <profile>` | Mechanically validate one ReferenceProfile: schema, unknown benchmark ids, duplicate references, count ceiling, token budget. Exit 1 = blocking defect. |
| `benchmark-leakage <wiki_dir> --profile ...` | Mechanical candidate scan of generated docs for benchmark provider terms. Output is a location-annotated candidate list — review input, never a verdict. |

Python never selects: the toolkit validates, budgets, and renders; the LLM
decides what is relevant.

## 4. Selection protocol (two stages, per page)

The full subtask contract lives in `tasks/select-benchmarks.md`. In brief:

1. **Stage 1 — metadata ranking.** The Selector reads only the compact
   index and ranks candidates on transferable documentation qualities:
   information-shape similarity, mental-model construction needs, task
   sequencing, progressive disclosure, lookup/reference design, tradeoff
   explanation, integration walkthrough design, operational usability.
2. **Stage 2 — detail loading.** Only shortlisted entries are loaded:
   `normalized/<id>.yaml` plus the pattern cards named in `pattern_ids`.
   Full `sources/` prose is exceptional and justified in the profile notes.
3. **Artifact.** One ReferenceProfile per `page_id` at
   `<output_dir>/.makewiki-artifacts/reference_profiles/<page_id>.yaml`,
   validated by `verify-reference-profile` before any Writer dispatch.
4. **Budgets.** The shortlist honors `benchmark.max_examples_per_page`
   (1–3 typical; 4 only for genuinely complex pages) and the rendered
   payload honors `benchmark.max_reference_tokens`.
5. **Zero is valid.** `references: []` with a one-sentence justification is
   a first-class outcome — selection never pads.

## 5. Writer and Reviewer handoff

- **Writers** receive the rendered profile as advisory context. The
  `borrow` list is presentation guidance; the `do_not_copy` list is
  binding. Writers never change page intent, audience, or category because a
  benchmark's archetype suggests it, and never copy benchmark product
  facts, terminology, API/config values, defaults, or limits.
- **Reviewers** re-select 1–2 references for the review pass
  (`tasks/review.md`) rather than inheriting the Writer's set, and treat
  leakage candidates from `benchmark-leakage` as findings to adjudicate.
  Factual leakage is critical; mechanical imitation is minor; PageSpec
  intent always outranks benchmark similarity.

## 6. Config surface

All knobs live under `benchmark` in `makewiki.config.yaml`:

```yaml
benchmark:
  enabled: true                  # LLM-consumed; Python never gates on it
  corpus_path: benchmarks        # SHARED (Python default --corpus)
  max_examples_per_page: 3       # SHARED (mechanically enforced)
  max_reference_tokens: 5000     # SHARED (mechanically enforced budget)
  prefer_pattern_cards: true     # LLM-consumed loading preference
  allow_full_source: false       # LLM-consumed loading preference
```

Python enforces `corpus_path`, `max_examples_per_page`, and
`max_reference_tokens` mechanically in `verify-reference-profile`. Whether
selection runs at all is a Skill-layer decision alone.
