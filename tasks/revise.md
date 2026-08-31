# Task: Revision (修订)

## Overview

Revision is the corrective half of the V3 review loop. The **Revision Agent** takes the
**`ReviewFindings`** produced by a read-only **Reviewer** and produces a **revised draft**
for the pages the Reviewer flagged — and only those pages. It does **not** adjudicate the
review, does **not** re-review its own work, and does **not** self-declare the result
`passed`.

V3 separates Review and Revision (unlike V2, where the Auditor both audited and edited in
place). The Reviewer defaults to read-only and emits findings; the Revision Agent
implements them; a fresh re-review decides whether the loop is done.

---

## 1. Input / Output

```text
ReviewFindings  (from a read-only Reviewer)
+ the specific PageSpec(s) / slice(s) the findings reference
+ relevant SemanticModel / DocumentationModel slices
+ source claims / evidence
→ revised draft (targeted pages only)
```

The Revision Agent works from the findings and their targeted slice, never from "the
whole repo". Scope is bounded to the flagged pages and the findings addressed.

---

## 2. Address exactly what the findings specify

- Fix **only** the pages and passages named in the `ReviewFindings`.
- Do not "improve" unflagged pages, styles, or structures unless a finding asks for it.
- Take the reviewer's severity (`critical | major | minor | advisory`) into account:
  - `critical`: wrong destructive-operator instructions, wrong auth/permission guidance,

    wrong endpoint method/path, fabricated required parameter, critical workflow —
    must be corrected before the page may proceed;
  - `major`: major capability missing, operator API largely undocumented, page serves

    wrong persona, important prerequisite omitted;
  - `minor`: related link missing, small explanation gap, non-critical naming;
  - `advisory`: reported for awareness; a reasoned "keep as-is" is an acceptable response.
- For each finding, either make the correction grounded in the slice or return the

  finding with an explicit disposition (`fixed`, `fixed_with_note`, `disputed`,
  `not_addressed_reason`) — never silently drop it.

---

## 3. Grounding discipline

Every correction must remain grounded in the PageSpec slice, the referenced
SemanticModel / DocumentationModel slices, and the source claims / evidence:

- every command, flag, config key, and interface stays backed by the slice;
- do not fabricate a fix when the Reviewer flags missing evidence — record a

  `documentation_gap` (see `DocumentationModel`) instead of inventing content;
- do not weaken a true, evidence-backed statement just to silence a reviewer;
- if a Reviewer finding is wrong (e.g. demands a fabricated detail), return it

  `disputed` with the evidence ref, rather than complying.

---

## 4. Preserve stable identity

Keep the cross-language stable identity intact while revising:

- **technical block IDs** `[[id:<slug>]]` — identical across languages;
- **reviewable section IDs** `<!-- makewiki:section=<slug> -->` above reviewable H2s;
- `page_id`, `semantic_refs`, and `source_claim` references must keep matching the

  `PageSpec`.

A revision may reword or reorder within a page, but must not break, renumber, or
de-duplicate the block/section IDs, and must not rename `page_id`.

---

## 5. Do not change global IA or API contracts

- No new major pages, no global navigation changes, no persona / capability changes.
- Do not promote an internal fact to a public rule, do not leak implementation into an

  end-user page.
- Revise API material only per `API_REFERENCE.md`: leave unproven fields at `UNKNOWN`,

  `null`, or omitted; correct only what evidence and the findings support.

---

## 6. Do not self-declare `passed`; re-review is mandatory

- The Revision Agent **must not** decide that the page now `passed`. Completion of a

  revision means the revised draft is ready for review — nothing more.
- Every revised page must go through a **fresh re-review** (a new ReviewFindings pass)

  before it can be considered reviewed.
- The review loop is bounded: **max 2 revision rounds per page** (QUALITY_POLICY §7).

  If a page has not passed after the allowed rounds, **escalate to the Orchestrator** —
  re-investigate or revise the `PageSpec` / `DocumentationModel` — rather than letting
  the Writer / Revision Agent iterate indefinitely.

---

## 7. Prohibitions & Strict Boundaries

During a revision subtask the Revision Agent **MUST NOT**:
1. **Judge the review** — findings are input, not something to re-litigate wholesale;
   a finding is either implemented, disputed with evidence, or escalated.
2. **Self-approve** — never declare the revised page `passed` or skip re-review.
3. **Exceed the flagged pages** — no edits outside the findings' scope.
4. **Re-research or redesign** — work from the slice; no new semantic truth, no new
   global IA, no new API contracts.
5. **Fabricate fixes** — a missing-evidence finding becomes a `documentation_gap`,
   never invented content.
6. **Let Python author or judge the revision** — revision and its grounding judgment
   are LLM-owned; Python only validates structure.
7. **Loop forever** — respect the 2-round cap and escalate to the Orchestrator instead
   of unbounded self-repair.

---

## 8. Stop Conditions

The Revision Agent **MUST STOP** when:
1. Every finding is explicitly disposed of (`fixed`, `fixed_with_note`, `disputed`
   with evidence, `not_addressed_reason`), and all `major`/`critical` items that could
   be corrected are.
2. Only the flagged pages were touched; unflagged pages and global IA are unchanged.
3. Block IDs and section IDs remain stable and matching.
4. Corrections stay grounded in the slice; missing evidence is recorded as a gap, not
   fabricated.
5. The revised draft is handed back for a **fresh re-review** — no self-declared `passed`.
6. Loop bound respected: if the page has had its allowed revision rounds, the subtask
   terminates with an escalation rather than another silent retry.

Terminate with a single status (`completed`, `blocked`, or `needs_followup`) and report
the `artifact produced`, per-finding `dispositions`, `uncertainties`, and any `scope
expansions`.
