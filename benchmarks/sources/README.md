# sources — local fetch cache

This directory holds raw pages fetched by
`python scripts/run_toolkit.py benchmark-acquire`. It is a local cache that
supports deeper analysis of a benchmark, never a distribution channel.

Rules:

- The corpus ships empty of fetched prose and with `acquire: metadata-only` on
  every row. Nothing in `sources/` is required for the corpus to validate.
- Provider prose may be committed here only when the page's stated license is
  documented in the matching registry row's `license_or_usage_note` and that
  license permits redistribution. Attribution to the provider stays intact.
- Fetched content stays in its original language, records its fetch date in the
  normalized file's `retrieved_at`, and keeps its provider's formatting intact
  enough to trace claims back to the source.
- Structural summaries in `normalized/` cover nearly every corpus use; when a
  license is unclear, do not commit prose at all.
