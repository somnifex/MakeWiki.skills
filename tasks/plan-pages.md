# Task: Page Planning (页面规划)

## Overview

Page Planning takes the **`DocumentationModel`** (who needs what) and produces the
**`DocumentationPlan`** and the concrete **`PageSpec`** set — the direct contracts handed
to Writers. The **Documentation Architect** owns this phase.

Planning decides **what documented intents exist and how they are grouped into pages**,
then yields one `PageSpec` per page. Planning does **not** write prose and does not decide
the renderer's physical site tree (that is Integration).

Diátaxis (Tutorials, How-To, Reference, Explanation) is used strictly as a **cognitive
rubric**, never as a mandatory list of filenames.

---

## 1. Input / Output

```text
DocumentationModel (+ SemanticModel, relevant claims/evidence)
→ DocumentationPlan
→ PageSpec[]   (one per page)
```

`DocumentationPlan` expresses structure:

```yaml
documentation_plan:
  sections:
    - id: admin-guide
      title_intent: Administrator Guide
      persona:
        - admin
        - operator
      pages:
        - admin/channel-management
        - admin/channel-routing

  relations:
    - from: admin/channel-management
      to: reference/management-api/channels
      type: related

  rationale:
    - ""
```

`PageSpec` follows `PAGE_SPEC.md` §2 (core `page_spec`), with `page_id`, `page_type`,
`title_intent`, `audience`, `user_goal`, `covers`, `required_sections`, required/optional
facts, forbidden topics, source/semantic/documentation refs, `related_pages`, and
`language`.

---

## 2. Split pages by user intent / persona / capability

A page is a unit of **documented intent**. Split pages when any of these differ:

```text
different primary persona
different independent user goal
different operational risk level
large standalone reference surface
too many unrelated major capabilities
an API resource with many independent operations
```

Do **not** use a fixed command count as the sole split rule, and do not split by source
file. Diátaxis informs page *types* and content shape, not a mandatory page list.

---

## 3. Page types (rubric vocabulary)

`PAGE_SPEC.md` §3-§4 defines the page-type vocabulary and per-type requirements:

```text
landing
tutorial
how_to
feature_guide
concept
reference
api_reference
troubleshooting
runbook
```

Only the types a project actually needs are used. Each type carries its own required
sections (e.g. `tutorial` needs a learning goal, prerequisites, progressive steps,
checkpoint, next step; `runbook` is operator-facing with trigger, preconditions,
procedure, verification, rollback, risk notes). When causality cannot be proven (e.g.
troubleshooting "likely cause"), it is not written as certain fact.

---

## 4. API reference page granularity

API reference follows `API_REFERENCE.md` and can be split by resource/endpoint:

- Small API: one resource page.
- Large API: `API landing/index → resource group → endpoint operation pages`.

```text
reference/management-api/
  index
  channels/
    index
    list
    create
    update
    test
    delete
```

The exact granularity is the Architect's judgment, driven by persona, operation count, and
risk — not by a fixed rule. Operator/admin API pages must surface roles, side effects,
idempotency, pagination, and destructive operations where proven.

### 4.1 Resolve every interface disposition to a page

Every important interface operation modeled in Documentation Modeling carries a
`disposition` (`documented`, `grouped`, `omitted`, or `unresolved`). Page Planning must
resolve each one:

- `documented` / `grouped` → the recorded `page_id` must actually be produced as a
  `PageSpec` (or an intentional, recorded exception).
- `omitted` → no page; the `reason` must remain recorded (the omission is deliberate, not a
  silent gap).
- `unresolved` → the referenced `documentation_gap` must be carried forward; it cannot be
  silently dropped at planning time.

Python may later validate that every important operation has a disposition and that every
`documented`/`grouped` one has a corresponding `PageSpec`, but it must never decide which
operations are important or invent a page target.

---

## 5. PageSpec is the Writer's contract

Each `PageSpec` fully specifies what a Writer is (and is not) responsible for. It binds
the Writer to that single page and its `required_sections`, `covers`, and forbidden topics,
so a Writer never "understands the repo and decides what to document."

PageSpec must carry stable `source_claims` / `semantic_refs` / `documentation_refs` so the
Writer (and later reviewers) can trace every assertion back to evidence.

---

## 6. Multilingual handling

Different languages are authored independently and natively. PageSpec / planning keeps the
cross-language stable identities: `page_id`, `semantic_refs`, `source_claim IDs`,
`technical block IDs`, `reviewable section IDs`. Headings and paragraph order may be
localized per language.

---

## 7. Prohibitions & Strict Boundaries

During page planning the Architect **MUST NOT**:
1. **Write final prose** — no end-user narrative, manual text, or runbook content.
2. **Treat Diátaxis as a mandatory file list** — it is a rubric only.
3. **Fix the renderer's physical site tree / routes** — `DocumentationPlan` is a semantic
   structure; Integration maps it to `SitePresentationPlan`.
4. **Let Python decide page type or page split** — page type validation only checks the
   allowed vocabulary.
5. **Split mechanically by file or fixed command count** — page boundaries follow intent.
6. **Invent page content or API schema** — pages map existing, evidence-backed coverage to
   intents; unknown contracts stay out or become `documentation_gaps`.

---

## 8. Stop Conditions

The Architect **MUST STOP** when:
1. The `DocumentationPlan` covers every major capability and persona with a clear rationale.
2. Every required documented intent has a `PageSpec`.
3. Operator/admin and management/API reference pages are explicitly planned where warranted.
4. Each `PageSpec` states audience, user goal, covered capabilities, required sections,
   forbidden topics, and evidence refs.
5. Diátaxis is used as a rubric, not a forced file list.
6. No final prose has been written and no renderer route tree decided.

Terminate with a single status (`completed`, `blocked`, or `needs_followup`) and report
the `artifact produced`, `uncertainties`, and any `scope expansions`.
