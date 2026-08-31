# Task: Read-Only Review (只读评审)

## Overview

Review is Phase 6 of the V3 pipeline. The **Reviewer** (an LLM subagent) evaluates the
cognitive quality of a drafted page against its evidence slice, the source, and the
cross-language contract — and emits a structured **`ReviewFindings`** artifact.

V3 **separates Review and Revision** (unlike V2, where the Auditor both audited and
edited in place). The Reviewer **defaults to read-only**: it does **not** edit pages.
A separate **Revision Agent** (`task: revise`) implements the findings, and a fresh
re-review decides when the loop is done (QUALITY_POLICY §2, §7).

Mechanical checks that Python already owns (syntax L0, existence L1, interfaces L2,
exact block-ID parity L4a, and the honest four-state Quality Gate) still run in the
mechanical plane; the Reviewer focuses on the cognitive layers that Python cannot judge.

---

## 1. Reviewer responsibilities (read-only)

The Reviewer reviews a drafted page and returns `ReviewFindings`:

1. **Grounding**: each command, config key, interface, path, and example is backed by

   the provided evidence slice; no unproven runtime value or behavior is stated as fact.
2. **Behavior**: workflows achieve their documented purpose; prerequisites, ordering,

   side effects, and error handling are consistent.
3. **Epistemic**: no overclaim, no fabricated guarantee, no stale or

   environment-dependent fact presented as certain.
4. **Documentation fitness**: persona / capability / journey coverage, page intent,

   page overload, reference discoverability.
5. **Audience fit**: no implementation leakage into end-user pages, no operator

   information missing, no root-only operations mixed into developer reference.
6. **API contract** (per `API_REFERENCE.md`): method/path, audience/auth, required

   params, request body, known responses/errors, side effects, idempotency /
   pagination / rate limits only where claimed; unproven fields stay `unknown` /
   `null` / omitted.

The Reviewer never fabricates a fix. A missing-evidence problem is reported as a
finding (or surfaced as a `documentation_gap`), not "resolved" by inventing content.

---

## 2. Review modes

Each review selects one or more modes (QUALITY_POLICY §3):

```text
grounding
documentation_fitness
audience_fit
api_contract
cross_language
epistemic
```

A small page may run several modes at once; a large page or a critical operator / admin
API may be split (e.g. grounding, operator-fitness, api_contract) per `SUBTASK_PROTOCOL` §6.

---

## 3. Output: `ReviewFindings` (not in-place edits)

The Reviewer emits a machine-readable `ReviewFindings` artifact (see
`ARTIFACT_CONTRACTS` §8), for example:

```yaml
review:
  page_id: channel-management
  language: zh-CN
  mode: documentation_fitness
  status: changes_required

  findings:
    - id: finding-001
      severity: major
      category: task_incompleteness
      location: "创建渠道"
      problem: "Prerequisite step omitted."
      evidence_refs: ["src/channels/create.py"]
      required_change: "Add the prerequisite step."

  passed_checks:
    - "Section IDs preserved."

  unresolved:
    - ""
```

Severity follows QUALITY_POLICY §5 (`critical | major | minor | advisory`).

---

## 4. Cross-language review & stable identity

For cross-language review (mode `cross_language`):

- **Semantic prose parity**: descriptions, explanations, and warnings convey the same

  meaning across languages; reordered sections keep informational parity; a missing
  section is a critical parity finding.
- **Stable identity**: `page_id`, `semantic_refs`, `source_claim` IDs, technical block

  IDs `[[id:<slug>]]`, and reviewable section IDs `<!-- makewiki:section=<slug> -->`
  must match across languages for blocks sharing the same stable ID.
- Mechanical alignment (exact block parity / aligned passages) is prepared by Python

  (`parity` / `semantic-review`) as supporting material only — it does not replace the
  LLM Reviewer's judgment.

---

## 5. Reviewer / Revision separation

1. **Reviewer (read-only)** → produces `ReviewFindings`.
2. **Revision Agent** (`task: revise`) → implements only the flagged pages.
3. **Re-review** → a fresh read-only review pass decides completion.

The Reviewer must **not** declare the page "passed" on the revision's behalf. The loop
is bounded: **max 2 revision rounds per page**; if a page still fails, escalate to the
Orchestrator (re-investigate or revise the `PageSpec` / `DocumentationModel`) rather
than letting the Writer / Revision Agent iterate indefinitely (QUALITY_POLICY §7).

---

## 6. Mechanical plane still owns mechanical checks

The following remain in the mechanical plane and feed the Quality Gate (they are **not**
the Reviewer's job to redo by hand):

```text
L0 syntax          L1 existence        L2 interfaces       L4a exact block parity
L5 epistemic*      SemanticAuditBundle Quality Gate (4-state honest verdict)
```

- (*) L5 epistemic accuracy is a cognitive review; the Python layer only validates the

  bundle schema / digests and merges verdicts.
- The honest four-state Quality Gate (`passed | pending_semantic_review |

  pending_mechanical_verification | failed`) remains the single decision point. The
  Reviewer's `ReviewFindings` feed the semantic side of that gate.
- The Reviewer **must not** edit Markdown in `<wiki_dir>`; any correction goes through

  the Revision Agent.

---

## 7. Prohibitions & Strict Boundaries

During a review subtask the Reviewer **MUST NOT**:
1. **Edit pages in place** — no in-place repair; emit `ReviewFindings` instead.
2. **Self-approve** — never mark its own reviewed page `passed` on the Revision Agent's
   behalf; completion is decided by re-review + the Quality Gate.
3. **Fabricate fixes or API contracts** — missing evidence becomes a finding / gap; a
   plausible-but-invented response schema or error status is never added.
4. **Let Python decide the review** — Python aligns passages / checks parity
   mechanically, but grounding, fitness, audience, API-contract, and epistemic
   judgment are LLM-owned.
5. **Change global IA or re-research the repo** — review works from the draft, the
   `PageSpec`, the relevant model/evidence slices.
6. **Exceed its scope** — only the pages / modes assigned.

---

## 8. Stop Conditions

The Reviewer **MUST STOP** when:
1. Every assigned page/mode has a `ReviewFindings` artifact with explicit findings,
   severities, `passed_checks`, and `unresolved`.
2. Unproven fields / missing evidence are surfaced as findings or gaps — never padded.
3. Stable block / section IDs and cross-language parity are checked where applicable.
4. No page was edited in place; no `passed` was self-declared on the revision's behalf.
5. `major` / `critical` items that must be corrected are clearly flagged for the
   Revision Agent.

Terminate with a single status (`completed`, `blocked`, or `needs_followup`) and report
the `artifact produced` (the `ReviewFindings` / list of reviews), `uncertainties`, and
any `scope expansions`.
