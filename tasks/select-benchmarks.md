# Task: Benchmark Selection (基准参考选择)

## Overview

Benchmark Selection is the optional advisory phase between Page Planning and
Writing. For each `page_id`, a dedicated **Benchmark Selector** subagent picks
a very small set of excellent external documentation examples whose
*information shape* can improve how the page communicates — organization,
sequencing, progressive disclosure, example placement, lookup experience. It
never supplies target-project facts: every factual claim about the target
stays grounded in repository evidence, ClaimBundles, and the SemanticModel.

Two groundings, strictly separated:

- **Evidence grounding** — what the target project is (capabilities,
  parameters, contracts, behavior). Sourced only from repository evidence.
- **Reference grounding** — how excellent documentation organizes similar
  complexity. Sourced only from the Benchmark Reference Library.

Authority order is absolute:

```text
repository evidence  >  PageSpec  >  ReferenceProfile  >  benchmark examples
```

`Target intent is authoritative. Benchmark archetype is advisory.`

When `benchmark.enabled` is false, this phase is skipped and every page
writes exactly as before. The layer is additive and advisory; no verification
semantics change.

---

## 1. Selector inputs (small by design)

The Selector receives a narrow slice, not the corpus:

```yaml
page_id: retrieval-engine
page_type: concept
title_intent: Retrieval Engine
audience: [developer, operator]
user_goal: Understand retrieval strategies and their tradeoffs
covers: [hybrid-search, ranking, reranking]
required_sections: [strategies, tuning, fallbacks]
known_constraints:
  - no benchmark product terminology may leak into the page
```

## 2. Two-stage selection

**Stage 1 — metadata ranking.** Read only
`benchmarks/index/benchmark-index.json`. Rank candidates on transferable
documentation qualities:

```text
information shape similarity      mental-model construction needs
task sequencing                   progressive disclosure
lookup / reference design         tradeoff explanation
integration walkthrough design    operational usability
```

Produce a shortlist of 1–3 (4 only for genuinely complex pages). Prefer few
strongly relevant examples over many weak ones.

**Stage 2 — detail loading.** For the shortlist only, load
`benchmarks/normalized/<id>.yaml` and the pattern cards named in its
`pattern_ids`. Full `sources/` prose is exceptional and must be justified in
the profile `notes`.

**Budgets** (from `makewiki.config.yaml` → `benchmark`):

- `benchmark.max_examples_per_page` — hard ceiling on the shortlist.
- `benchmark.max_reference_tokens` — ceiling for the rendered payload.

## 3. Output artifact

Exactly one profile per page:

```text
<output_dir>/.makewiki-artifacts/reference_profiles/<page_id>.yaml
```

```yaml
page_id: retrieval-engine
language: null            # selection is language-neutral
selected_by: benchmark-selector
references:
  - benchmark_id: weaviate-search-concepts
    relevance:
      - mental-model-first
      - compare-search-strategies
    borrow:
      - explain strategies before parameters
      - separate concepts from tuning reference
    do_not_copy:
      - Weaviate terminology
      - Weaviate product facts
notes: >
  Why these transfer: cite the shape being borrowed, not the source's
  product claims.
```

An empty selection is a first-class outcome:

```yaml
page_id: cli-cheatsheet
references: []
notes: No benchmark materially improves this page; PageSpec is a compact lookup.
```

## 4. Verification gate

```bash
python <makewiki_root>/scripts/run_toolkit.py verify-reference-profile \
  <profile.yaml> --corpus benchmarks
```

Exit code 1 blocks dispatch: unknown `benchmark_id`, duplicate reference,
count over `benchmark.max_examples_per_page`, or an over-budget render.
Fix the selection; never bypass the check.

## 5. Writer / Reviewer handoff

- **Writers** receive the rendered profile as advisory context. The
  `borrow` list is presentation guidance; the `do_not_copy` list is
  binding. Writers never change page intent, audience, or category because a
  benchmark's archetype suggests it, and never copy benchmark product
  facts, terminology, API/config values, defaults, or limits.
- **Reviewers** re-select 1–2 references for the review pass
  (`tasks/review.md`) instead of inheriting the Writer's set. Leakage
  candidates from `benchmark-leakage` are findings to adjudicate — factual
  leakage is critical, mechanical imitation minor, and PageSpec intent
  always outranks benchmark similarity.

## 6. Prohibitions & strict boundaries

During a selection subtask the Selector **MUST NOT**:

1. Load the whole corpus — the compact index plus shortlisted files bound
   its input.
2. Treat benchmark categories as target-page classifications or generation
   constraints; cross-category transfer is explicitly allowed.
3. Let benchmark facts become target-project facts; target claims stay
   grounded in target-project evidence.
4. Exceed the configured count or token budgets.
5. Spawn further agents; selection is one level of delegation.
6. Let Python choose relevance — the toolkit validates and renders; the LLM
   selects.

## 7. Stop conditions

The Selector **MUST STOP** when:

1. The profile exists at
   `<output_dir>/.makewiki-artifacts/reference_profiles/<page_id>.yaml`.
2. Every `benchmark_id` resolves against the registry and passes
   `verify-reference-profile`.
3. The selection honors `benchmark.max_examples_per_page` and
   `benchmark.max_reference_tokens`.
4. A `references: []` decision carries a one-sentence justification.

Terminate with a single status (`completed`, `blocked`, or `needs_followup`)
and report the artifact produced, uncertainties, and any scope expansions.
