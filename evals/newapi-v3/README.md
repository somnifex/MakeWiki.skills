# NewAPI V3 — Benchmark Run Notes

> **Human / LLM rubric benchmark — not Python-scored.**
>
> `newapi-v3` is the V3 product-documentation benchmark. It evaluates the
>
> 18-dimension rubric in [`evals/newapi-v3-rubric.md`](../newapi-v3-rubric.md).
>
> Python regex scorer. The deterministic evals in `evals/*/` (scored by
>
> benchmark.

## Why this is separate from the deterministic traps

The deterministic traps (`evals/hidden-entrypoint/`, `evals/nested-monorepo/`,
...) measure whether the mechanical plane can *prove* facts about a repo. They
have `rubric.yaml` + gold JSONs and are scored mechanically.

`newapi-v3` measures *semantic document quality*: persona discovery, journey
coverage, task orientation, operator documentation, API epistemic accuracy,
cross-language parity, and the balance between completeness and hallucination.
These are judgment calls that resist a mechanical scorer, so the rubric is
rated `excellent | acceptable | poor | not_applicable` by a human/LLM — see
`Benchmark` in [`evals/README.md`](../README.md).

This directory intentionally contains **no `rubric.yaml`** at its root, so the
deterministic trap checker (`check_fixtures` in
`src/makewiki_skills/evals/runner.py`) does not enumerate it as a mechanical
trap, and `test_ten_benchmark_eval_traps_exist` (a fixed canonical list) is
unaffected.

## Run protocol

1. **Pin a NewAPI commit.** Note the exact `commit` (and `run_id`) in the

   report. A benchmark result is only meaningful against a reproducible repo
   state.
2. **Run the authoritative V3 flow** on the NewAPI checkout:

   `/makewiki` → Orientation → Investigation → Semantic Synthesis →
   Documentation Modeling → Page Planning → Writing → Review → Revision →
   Integration → Verify → Deliver.
3. **Collect the artifacts** the evaluator scores:
   - `RepositoryBrief` / `SemanticModel` (persona & capability evidence)
   - `DocumentationModel.personas` and each `PageSpec` (page set, audience)
   - the generated Markdown document collection
   - the compiled site navigation (`SitePresentationPlan`)
   - the Quality Gate verdict and any `UNKNOWN` emissions
4. **Score each of the 18 dimensions** with the rating vocabulary

   `excellent | acceptable | poor | not_applicable`. Fill
   `benchmark-run-template.yaml` (one file per run):
   - `rating`: the verdict for the dimension.
   - `evidences`: concrete artifacts / page ids / diff hunks that support the
     rating. Must reference real output — a rating with no evidence is not a
     report.
   - `notes`: what worked, what regressed, what needs a follow-up run.

   Human and LLM judges are both allowed. Whatever the judge is, record it in
   the report metadata so results are comparable across runs.
5. **Guard against the two "Poor" extremes** the rubric warns about:
   - a conservative doc set that silently drops important capability surfaces;
   - a complete doc set full of **unproven** details (implementation leakage /

     hallucinated contract, missing `UNKNOWN` discipline).

   These are exactly the `api_epistemic_accuracy`, `implementation_leakage`,
   `grounding`, and `completeness_vs_hallucination_balance` dimensions — treat a
   low rating there as the highest-severity finding.
6. **Report** `overall.strengths`, `overall.regressions`, and

   `overall.blocking_issues`. Only a dimension scored `not_applicable` may be
   absent from `strengths`/`regressions`; a `blocking_issues` entry should name
   the severity and the dimension(s) it affects.

## What is NOT here (and must not be added)

- **No Python scorer, no regex over generated prose.** The rubric is a rubric,

   not a program. Do not add `run_evals.py`-style mechanical scoring for these
   dimensions; that would break the cognitive-authority boundary (the LLM
   judges meaning, Python proves mechanics) and violate the M1 requirement.
- **No `rubric.yaml` in this dir** — keep it out of the deterministic trap

   set. The rubric reference lives at `evals/newapi-v3-rubric.md`.

## Files

- `README.md` — this run protocol.
- `benchmark-run-template.yaml` — one report per run; copy to `runs/newapi-v3-<run_id>.yaml`.