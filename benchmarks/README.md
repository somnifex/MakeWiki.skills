# Benchmark Reference Library

A curated corpus of excellent external documentation pages, kept as structural
summaries and distilled patterns. The Benchmark Selector reads this corpus when
planning a page and recommends proven information architectures for it; Writers
and Reviewers borrow information shape from it, never prose or provider
facts.

## The four layers

| Layer | Location | Content |
| ----- | -------- | ------- |
| Registry | `registry.yaml` | Curated metadata: ids, providers, source URLs, pattern links, licensing posture |
| Normalized benchmarks | `normalized/<id>.yaml` | Structural summaries of excellent pages, written in our own words |
| Documentation patterns | `patterns/<id>.yaml` | Source-agnostic patterns distilled across benchmarks: when to use, ordered shape, traits, anti-patterns |
| Compact index | `index/benchmark-index.json` | Generated stage-1 ranking input (metadata only) |

`sources/<provider>/` holds raw fetched pages. It is a local cache, not a
distribution channel; see `sources/README.md` before putting anything there.

## Authority order

1. `registry.yaml` decides identity. A benchmark id exists only if a row lists
   it, and the row is the source of truth for provider, title, and source URL.
2. Pattern cards decide vocabulary. Every pattern id referenced from a registry
   row or a normalized file must be declared in the registry's `patterns` list.
3. Normalized files carry analysis prose and verification state. Each must agree
   with its registry row on id, provider, and title, or the corpus fails to load.
4. The index is a derived artifact. It carries no authority of its own and is
   regenerated deterministically from the other three layers.

Seed summaries are marked `verification: unverified-structural-summary`. That
honesty marker stays until a fetch from the live page backs the analysis, at
which point `retrieved_at` and `content_path` are filled in.

## Metadata-only default

Every registry row ships with `acquire: metadata-only`. Under this default the
toolkit never fetches or stores full provider prose, which keeps the corpus
redistributable. `acquire: full` is reserved for pages whose stated license
clears inclusion of fetched content in `sources/`, and the license must be
recorded in the row's `license_or_usage_note`.

## Regenerating the index

```bash
python scripts/run_toolkit.py benchmark-index benchmarks
```

The command validates schema and cross-links, then writes
`index/benchmark-index.json`. Treat that file as build output: do not hand-edit
it and do not add prose to it. A stale committed index fails the corpus contract
test, so re-run the command after every corpus change.
