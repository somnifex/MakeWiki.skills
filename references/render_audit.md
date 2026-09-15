# Rendered-Output Audit (`verify-html`)

Post-render mechanical audit over the artifacts the skill ships. Rendering is
mechanical, so a renderer change can regress silently: a leftover build marker,
escaped content, dropped table cells, an unrendered fence. This audit makes the
toolkit answerable for its outputs instead of trusting the renderer.

Status: **post-render mechanical audit, not a new L0-L5 layer.** The Quality
Gate's four-state semantics are untouched. Like `lint-drafts`, the check
**fails closed**: exit 1 blocks delivery.

## What it audits

| Target | Unit | Segmentation |
| :--- | :--- | :--- |
| `site/index.html` (single-file SPA) | every `(language, document)` body embedded in the `docsContent` JSON payload, recovered from the real artifact | preamble + H2 sections |
| `export/documentation[.<lang>].html` | each `<section class="chapter">` | same |
| `export/documentation[.<lang>].epub` | each `OEBPS/chapter_NN_<slug>.xhtml` body | preamble + H2 sections |

Both sides — source Markdown and rendered HTML — are split by the same H2
boundaries and paired by position WITHIN one language version of one document
(render order always equals source order there). Stable
`<!-- makewiki:section=<id> -->` markers carry the identity when authored;
cross-language alignment by `section_id` stays with L4 / L4b, which pair by
`section_id`, never by heading text or position.

## Checks (per language × document × section)

| Check | Severity | What it proves |
| :--- | :--- | :--- |
| `marker_leak` | critical | `[[id:...]]`, `[[parity:ignore ...]]`, `<!-- makewiki:section=... -->` (raw or escaped), internal artifact paths (`.makewiki-artifacts/`, `12-drafts/`, `14-revision-results/`), writer frontmatter echo keys, or visible callout markers never reach a reader |
| `heading_parity` | major | every source section heading survives at the same level; segment counts match; the source H1 exists as a rendered `<h1>` |
| `prose_coverage` | major | every substantive source prose line (normalized to case-folded alphanumerics; images, link labels, callout tokens and list markers normalized) appears in the rendered segment's visible text — catches content loss and escaping bugs |
| `code_block_parity` | major | source fenced-block count equals rendered `<pre>` count per segment |
| `table_integrity` | major | source rows/cells match rendered `<tr>`/`<td>`+`<th>` counts, and every source table maps to one `<table>` element (catches per-row table shells) |
| `link_residue` | major | no unrendered markdown link syntax (`](`) in rendered prose |
| `fence_residue` | major | no unrendered ``` fence marker outside code blocks |
| `callout_fidelity` | minor | source `> [!TYPE]` count matches rendered `blockquote.callout` count; recorded but does not block |
| `artifact_completeness` | major | every exported chapter has a matching source chapter, and vice versa |
| `artifact_missing` | critical | an artifact the requested target covers does not exist (fails closed, never a silent pass) |

Severity semantics: `critical`/`major` fail the audit (exit 1, delivery
blocked); `minor` findings are recorded but do not block.

## Known boundaries (documented, not hidden)

- `prose_coverage` skips fenced code content and table rows (both are covered
  by their own count-parity checks) and skips lines whose normalized key is
  shorter than 6 characters, so syntax-only stretches do not false-positive.
- Indented (4-space) code blocks also render as `<pre><code>` and can make
  code-block parity over-count on documents mixing both styles; generated
  writers use fenced blocks exclusively.
- The audit proves formatting and content survival. Whether the prose is
  well-written stays with the LLM Review plane.

## Workflow position

1. `build-site` / `export` produce artifacts.
2. `verify-html --target site|export` audits them (blocking).
3. Blocking findings locate the offending Markdown source via
   `language/document_id#section_id`. Fix the source, rebuild, re-run — the
   loop is bounded by `agent.max_audit_rounds`. Never hand-edit generated HTML.
4. `verify-html` does not change the Quality Gate verdict; the four-state
   semantics of `verify-docs` are untouched.

Finding locations follow the L4b review-item grammar:
`HTML:<document_id>:<section_id>` (section id empty for preambles).
