# MakeWiki Agent-Behavioral Evals

These are **LLM agent-behavioral evals**, not Python unit tests. They measure
whether the MakeWiki agent (the authoritative LLM writer/auditor path) behaves
correctly when the repository is deliberately designed to *trip* it. The Python
mechanical plane is strong and deterministic; these evals target the **weak
semantic plane** the code is forbidden to guess about (the gap layer).

## How to run

There is no heavyweight runner. Each `evals/<trap>/` is a self-contained,
tiny synthetic repository plus gold files. Run each trap N>=3 times with a real
model and record the per-run pass/variance (see **Section 33**):

```
makewiki <path>/evals/<trap>        # full authoritative flow on the trap repo
```

then compare the produced docs against the gold files. A lightweight, optional,
dependency-free checklist printer lives in `evals/run_evals.py`; it walks every
trap and prints the gold-file checklist so a human or agent can execute each one.

## Gold format — never a single gold article

A well-behaved agent can produce many *correct* article forms (different
heading orders, different prose, different examples). Gold files are therefore
**structured, multi-choice claims**, not one `expected_full_document.md`. A doc
passes only when it satisfies every:

- `verified_facts.json`   — facts the facts doc MUST contain.
- `required_claims.json`  — claims the claims doc MUST make.
- `forbidden_claims.json` — claims the doc MUST NOT make.
- `expected_unknowns.json`— things the doc SHOULD mark `UNKNOWN` (never invent).
- `rubric.yaml`           — weighted scoring criteria.

A correct article is *one valid form*; a doc that contains all required facts,
makes all required claims, makes no forbidden claims, and marks every expected
unknown as UNKNOWN is accepted regardless of its exact wording.

## Metric list (Section 32)

Each trap is scored against the following metrics. Not every trap engages every
metric; `rubric.yaml` sets the weights per trap (zero weight = N/A there):

1. **Evidence Grounding** — every stated fact traces to a cited source.
2. **Unsupported Claim Rate** — fraction of asserted claims with no evidence.
3. **Required Claim Recall** — fraction of required claims actually made.
4. **Unknown Discipline** — correctness of marking UNKNOWN vs inventing.
5. **Task Discovery** — the features/workflows the agent surfaced.
6. **Workflow Correctness** — documented workflows match the real commands.
7. **ReBattle Conflict Detection** — conflicts (contradictory config, stale docs)

   are surfaced before writing.
8. **Judge Correctness** — the adjudicator resolves conflicts toward the

   stronger evidence, not the noisier source.
9. **SemanticModel Quality** — the folded semantic model is accurate + complete.
10. **Native-language Quality** — each language reads as if written natively

    (no translationese for ZH; see Section 3).
11. **Cross-language Semantic Parity** — same meaning + byte-identical technical

    blocks across languages (L4a mechanical + L4b semantic).
12. **Troubleshooting Correctness** — troubleshooting captures the real cause /

    solution from evidence, not a plausible-sounding one.
13. **Epistemic Calibration** — claimed confidence matches the underlying evidence.
14. **Documentation Usefulness** — a reader acting on the doc succeeds.

## Trap index

| Trap                    | What it trips                                        |
| ----------------------- | ---------------------------------------------------- |
| `misleading-readme/`    | README contradicts source on a default value         |
| `ambiguous-install/`    | no explicit install instructions -> must say UNKNOWN |
| `undocumented-feature/` | experimental flag -> forbidden to call it stable     |
| `multilingual-parity/`  | EN/ZH reorder sections -> must pair by stable ID     |
| `stale-cli-doc/`        | README documents a command removed from source       |
| `platform-specific/`    | Linux-only Makefile -> must not infer WSL            |
| `contradictory-config/` | two configs disagree -> must raise a dispute         |
| `unsupported-claim/`    | a claim with no evidence -> must be absent/hedged    |
| `monorepo/`             | multiple packages -> scope claims to the right path  |
| `troubleshooting/`      | reproducible error -> capture the real cause         |