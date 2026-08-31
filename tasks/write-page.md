# Task: Single-Page Writer (单页撰写)

## Overview

Writing is where a `PageSpec` becomes a native-language draft page. Each writing subtask
(`type: writing`) produces exactly **one `PageSpec` × one `language`** (small projects may
bundle 2-3 very short, tightly-related reference pages by exception, never one language =
the entire suite).

The Writer is a **Language Writer subagent** (or the Main Agent in solo fallback). The
Writer's job is *not* to understand the repo and decide the documentation; it is to write
this one documented intent accurately from the semantic inputs it is given.

---

## 1. Contract & isolated input

A Writer receives a narrow, targeted slice — **not** "the whole repo + write good docs":

```text
one PageSpec
+ the relevant SemanticModel slice
+ relevant DocumentationModel slice
+ source claims / evidence
+ language profile
→ one native-language draft page
```

Write only what the slice supports. Scope is bounded to this page, this language.

---

## 2. Native-language independent writing

Each language version is authored **independently and natively** — never machine-translated
from another language. Use natural, correct phrasing for the target language (e.g. natural
Chinese / English engineer prose), the writer tone from the language profile, and direct,
concise, professional engineer tone.

Self-review before finishing (grounding / parity / anti-AI-cliché / tone):
- every command, flag, and config key is backed by the given model/evidence slice;
- technical blocks match the model character-for-character;
- no AI-trope phrasing or redundant trailing colons;
- no fabrication of runtime values, UI specifics, or unproven behavior.

---

## 3. Preserve stable identity (block ID / section ID)

Keep the cross-language stable identity intact:
- **technical block IDs** `[[id:<slug>]]` on fenced code blocks — identical across languages;
- **reviewable section IDs** `<!-- makewiki:section=<slug> -->` above reviewable H2 headings.

Within a page you may reorder natural paragraphs and rephrase headings for readability,
but the block/section IDs, `page_id`, `semantic_refs`, and `source_claim` references must
match the `PageSpec`. Code, config keys, commands, flags, and env vars must match
identically across languages for blocks sharing the same stable ID.

---

## 4. Do not change global IA

The Writer does **not** redesign or add to the global information architecture:
- no new major pages, no global navigation changes;
- no changing personas or canonical capabilities;
- no promoting an internal fact to a public rule;
- `related_pages` come from the `PageSpec`, not from Writer invention.

---

## 5. Do not guess API contracts

Follow `API_REFERENCE.md`. Use only evidence-backed contracts from the slice:
- method, path, purpose, audience, params, request/response, errors, side effects only
  where the source claims/tests/spec support them;
- unproven fields stay `UNKNOWN`, `null`, or omitted;
- examples use (in priority) repository examples, test fixtures, SDK examples, then only
  LLM-constructed examples built strictly from fully-proven fields;
- never write a plausible but fake response schema.

---

## 6. Insufficient information → return a gap

When the slice cannot support a required section or capability, the Writer does **not**
pad it. It records a `documentation_gap` (see `DocumentationModel`) and/or reports the
missing evidence in its completion status rather than inventing content. A page may
explicitly note "the repository confirms X can fail, but does not establish a stable
public response schema."

---

## 7. Prohibitions & Strict Boundaries

During a writing subtask the Writer **MUST NOT**:
1. Read the entire repository and decide the documentation — work from the slice.
2. Modify the `SemanticModel`, the `DocumentationModel`, or the global IA.
3. Change personas or canonical capabilities.
4. Add new major pages / global navigation.
5. Invent API contracts, response payloads, error schemas, or runtime specifics.
6. Write beyond the allowed page set (the one page, or the permitted 2-3 short related
   reference pages).
7. Let Python author or judge prose — writing and its grounding judgment are LLM-owned.

---

## 8. Stop Conditions

The Writer **MUST STOP** when:
1. The page covers the `PageSpec`'s `covers`, `required_sections`, and audience with the
   intended `page_type` shape.
2. Every command / flag / config key is grounded in the provided slice.
3. Block IDs and section IDs are preserved and match the specs.
4. Native language is correct and no machine-translation artifact remains.
5. Missing evidence is recorded as a gap, not fabricated.
6. Only the permitted page(s) were written; global IA untouched.

Terminate with a single status (`completed`, `blocked`, or `needs_followup`) and report
the `artifact produced`, `uncertainties`, and any `scope expansions`.
