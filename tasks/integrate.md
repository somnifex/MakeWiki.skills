# Task: Integration (站点整合)

## Overview

Integration is the step that turns the reviewed, passed document set into the
**`SitePresentationPlan`** — the single authoritative statement of the site's
Information Architecture (IA) and visual direction — and the compiled site's
navigation and cross-links. The **Site Designer / Integrator** (Main Agent or a
delegated subagent) authors the plan; the Python `SiteCompiler` renders it
mechanically and verbatim.

Integration works from the **`DocumentationPlan`** and the **passed reviewed
drafts** only. It does **not** re-research the source, does **not** add new major
product facts, and does **not** decide documentation truth — that was settled in
Semantic Synthesis / Documentation Modeling / Page Planning and adjudicated in
Review.

---

## 1. Input / Output

```text
DocumentationPlan
+ PageSpec set / DocumentationModel (structure, relations)
+ passed revised drafts (reviewed, approved)
+ language set / locale info
→ SitePresentationPlan
→ integrated site (navigation, related links, localized rendering)
```

Integration is a **presentation / assembly** activity. The site tree it produces is
the physical rendering of an already-decided semantic structure — it is not a second
place to re-decide what gets documented.

---

## 2. Integrate only passed drafts

- Only drafts that have **passed review** (Quality Gate / review loop) are integrated.
- A page that is `pending`, `failed`, or blocked is **not** placed into the final

  navigation; it stays out or is surfaced as explicitly not integrated. Do not
  quietly ship an unreviewed page.
- Record which pages were integrated and which were held back, so the reader / runner

  can tell the final site apart from the reviewed-but-pending set.

---

## 3. Author the SitePresentationPlan (IA is LLM-owned)

The `SitePresentationPlan` is the **only** thing the mechanical compiler reads to
decide navigation, page roles, ordering, and hierarchy. The Integrator authors it
from the `DocumentationPlan` and PageSpecs:

- **navigation**: one `SiteNavItem` per `document_id` — stable id (relative path,

  no language suffix), URL `route`, localized `title` / per-language `titles`,
  `nav_group`, `ordering`, and `children` for hierarchy. Navigation depth should
  follow the `DocumentationPlan` structure and usability needs — there is **no
  fixed two-level limit** (the `SiteCompiler` recurses `children` without a depth
  cap, so the plan may nest as deep as the documentation tree requires). The
  Integrator must **not** flatten, re-target, or otherwise change the IA just for
  display convenience. Groups and ordering come from the `DocumentationPlan`
  structure and page intent — never inferred from the filename or its keywords.
- **languages / default_language**: the set to render and the default; the language

  switcher is built from this.
- **visual**: `SiteVisualPreferences` — theme, include_search, accent_color,

  brand_label — presentation direction only, no page semantics.
- **project_title / project_description**: site-level identity, from the

  SemanticModel / DocumentationModel identity.

Python **must not** infer any of these fields (no Overview / Getting Started / FAQ /
Deployment / nav-group / ordering / hierarchy heuristics); if no plan exists, the
compiler refuses to fabricate one and the site build enters `unavailable` /
`pending`. The Integrator therefore always supplies the plan.

---

## 4. Navigation & related links

- **Navigation** derives from the `DocumentationPlan`'s section / page structure:

  group pages under their planned sections, order by the plan's `relations` / intent,
  and nest only where the plan expresses hierarchy.
- **Related links** come from the `PageSpec` `related_pages` / `DocumentationPlan`

  `relations` — not from the Integrator's invention. Wire the documented
  cross-references so users can move between related pages.
- Keep the stable identity intact while assembling: `page_id`, block IDs, section

  IDs, and localized content per language resolve mechanically from the wiki tree.

---

## 5. Do not re-research or invent product facts

- No re-reading of source to "add" facts — the semantic truth is already fixed.
- No new major pages, no new major capabilities, no promotion of internal facts to

  public rules, no persona / capability changes.
- If integration reveals a genuine missing piece, record it as a follow-up / gap for

  the earlier phases, rather than authoring new product content here.

---

## 6. Prohibitions & Strict Boundaries

During integration the Integrator **MUST NOT**:
1. **Decide what gets documented** — that is Documentation Modeling / Page Planning;
   integration only renders the planned, reviewed set.
2. **Integrate unreviewed / non-passed drafts** into the final navigation.
3. **Infer IA from filenames or keywords** — the plan states structure explicitly;
   Python renders it verbatim, never guesses it.
4. **Add new product facts, pages, personas, or capabilities.**
5. **Re-research the repository** to author content.
6. **Invent related links** beyond the planned `related_pages` / `relations`.
7. **Let Python decide IA** — Python validates the plan schema, resolves the
   localized document files, and renders; the Integrator authors the plan.

---

## 7. Stop Conditions

The Integrator **MUST STOP** when:
1. A `SitePresentationPlan` exists that maps every integrated (passed) page to a nav
   item with route, localized titles, group, ordering, and (where planned) children.
2. Only passed drafts are integrated; held-back pages are explicitly surfaced.
3. Navigation groups / ordering / hierarchy follow the `DocumentationPlan` structure;
   related links follow the planned `related_pages` / `relations`.
4. No source re-research and no new major product facts / pages / personas were added.
5. Languages / default and visual preferences are set, with IA authored by the LLM,
   never inferred by Python.
6. The plan is schema-valid (loads via the mechanical plane) and ready for the
   `SiteCompiler` to render.

---

## 8. Draft hygiene lint (mechanical, pre-verification)

After assembling the deliverable markdown tree and BEFORE Final Verification
(L0–L5), run the mechanical draft lint:

```bash
makewiki lint-drafts <wiki_dir>
```

This is a deterministic check owned by Integration (not a new pipeline stage
and not a Quality Gate state). It proves only mechanical structure:

- **writer frontmatter leak** — deliverable drafts must not carry writer

  YAML frontmatter (`page_id:` / `audience:` / `page_type:` /
  `source_claims:` keys). Frontmatter with other keys is legitimate site
  metadata the renderer strips mechanically.
- **internal artifact path leak** — deliverable prose must not reference

  `.makewiki-artifacts/…` or other internal orchestration paths.
- **section-marker grammar** — markers immediately precede their heading; no

  orphan markers; no duplicate section ids; every `PageSpec.required_sections`
  id has a marker in the draft.
- **stable block-ID structure** — no duplicate `[[id:...]]` within one

  document; the en/zh block-ID sets of a page pair are equal (byte-parity of
  bodies stays in L4a).
- **disposition / plan / page cross-references** — every

  `documented|grouped` disposition `page_id` exists in the planned page set;
  no duplicate `operation_id`; `unresolved.gap_id` exists in
  `documentation_gaps`; every planned page has an assembled draft per
  declared language; the existing plan↔PageSpec consistency report.

Blocking (`error`) issues mean **Integration is incomplete**: fix the drafts /
artifacts and re-run until the lint passes, or surface the failure explicitly.
Page quality, persona fit, and API semantics are NEVER linted here — they
belong to the Reviewer and the L0–L5 layers.

Terminate with a single status (`completed`, `blocked`, or `needs_followup`) and report
the `artifact produced` (the plan / integrated site), `uncertainties`, and any `scope
expansions`.
