---
name: makewiki-benchmark
description: "Curate the Benchmark Reference Library and issue per-page advisory ReferenceProfiles for MakeWiki runs. Use when: maintaining the excellent-docs benchmark corpus (registry, normalized summaries, patterns, index), acquiring source pages under licensing rules, or selecting advisory writing references for a page. Mechanical commands only; selection judgment is LLM-owned."
version: "3.2.0"
argument-hint: "[index|acquire <ids...>|verify <profile>]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Glob Grep
---

# MakeWiki Benchmark - Reference Library Curation & Selection

Maintain the four-layer benchmark corpus under `benchmarks/` and issue the
per-page advisory ReferenceProfiles consumed by Writers and Reviewers.
Benchmarks are **advisory writing references, never a fact source** — the
authority order is repository evidence > PageSpec > ReferenceProfile >
benchmark examples (`references/v3/BENCHMARK_LIBRARY.md`).

## Arguments

- `index` (default): validate the corpus and regenerate
  `benchmarks/index/benchmark-index.json`.
- `acquire <ids...> [corpus]`: fetch source pages into `sources/<provider>/`;
  entries marked metadata-only are refused without `--force`.
- `verify <profile>`: mechanically validate one ReferenceProfile YAML.

## Execution

### Step 1: Bootstrap the home-scoped toolkit

```bash
python scripts/bootstrap_toolkit.py
```

If the script prints a path, refer to it as `<makewiki_root>`.

### Step 2: Run the mechanical commands

```bash
python <makewiki_root>/scripts/run_toolkit.py benchmark-index benchmarks
python <makewiki_root>/scripts/run_toolkit.py benchmark-acquire <ids...> --corpus benchmarks
python <makewiki_root>/scripts/run_toolkit.py verify-reference-profile <profile.yaml> --corpus benchmarks
python <makewiki_root>/scripts/run_toolkit.py benchmark-leakage <wiki_dir> --profile <profile.yaml>
```

`verify-reference-profile` exit code 1 is a blocking defect: unknown
benchmark id, duplicate reference, count over
`benchmark.max_examples_per_page`, or a rendered payload over
`benchmark.max_reference_tokens`. Fix the selection; never bypass the gate.

### Step 3: Authoring rules (LLM-owned layers)

- Edit `normalized/<id>.yaml` and `patterns/<id>.yaml` as structural
  summaries in your own words — never paste provider prose. A fetched raw
  page may be consulted only when the entry records a compatible license or
  usage note.
- Every benchmark id must resolve in `registry.yaml`; `benchmark-index`
  fails closed on dangling `pattern_ids` or `source_examples`.

### Step 4: Selection subtask per page

For per-page selection (two stages, budgets, `references: []` outcomes),
follow `tasks/select-benchmarks.md`. The output artifact lands at
`<output_dir>/.makewiki-artifacts/reference_profiles/<page_id>.yaml`.
