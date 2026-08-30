# Task: Subagent Adversarial Review & Self-Healing (审查员审计与自愈)

## Overview

Review is Phase 4 of MakeWiki. The **Auditor Subagent** executes an
autonomous cognitive audit and in-place self-healing pass, ensuring 100%
cross-language parity, evidence-backed grounding, and natural technical
prose. The Python toolkit supplies the mechanical half: `verify-docs` runs
the unified L0–L5 verification, `parity` checks block-ID exact-match across
languages, and `semantic-review` produces aligned passages for the Auditor.

The Quality Gate aggregates the result into PASS / FAIL and maps to the CI
exit code (0 / 1). MakeWiki is **evidence-backed**, not "zero-hallucination";
every status reflects a concrete check, not marketing.

---

## 1. Auditor Subagent Responsibilities

1. **L3 Behavior Judgment**:
   - For each documented command, decide whether the described behavior is

     consistent with what the source actually does.
   - Python supplies evidence; the Auditor renders the L3 verdict.
2. **L4 Prose Parity Judgment**:
   - Python enforces exact block-ID parity (L4a) across languages. Matching is

     keyed on stable block IDs (`[[id:<slug>]]`) and stable H2 section markers
     (`<!-- makewiki:section=<slug> -->`), never on heading text or heading
     position; section ORDER may differ per language.
   - The Auditor judges prose parity (L4b) from the aligned passages produced

     by `semantic-review`.
3. **L5 Over-Assertion & Anti-AI-Cliché Audit**:
   - Flags claims more confident than their evidence warrants.
   - Enforces `references/anti_ai_cliche.md`: bans binary tropes

     ("不是……而是……"), buzzwords ("收敛", "赋能", "对齐"), trailing colons
     in headings, and unfounded praise.
4. **Side-by-Side Cross-Language Audit**:
   - Compares English and Chinese Markdown documents side-by-side.
   - Verifies that all code blocks, command arguments, and config keys

     match character-for-character across all languages for blocks carrying
     the same stable ID.
5. **Codebase Ground-Truth Verification**:
   - Verifies that every documented CLI command, file path, and env var

     actually exists in the target repository.
6. **Emit the SemanticAuditBundle**: After judging, write a machine-readable

   `SemanticAuditBundle` JSON capturing the L3 / L4b / L5 verdicts (schema:
   `schema_version`, `documents_digest` (sha256 over the audited markdown
   set), optional `semantic_model_digest`, `auditor`, `audited_at`, and a
   list of verdicts whose entries carry `review_item_id`, `layer` (L3 / L4b /
   L5), `status` (passed / failed), `rationale_summary`, `evidence_refs`, and
   `confidence`. Emit it last, after all
   in-place edits, so `documents_digest` matches the final markdown set; a
   stale bundle (digest mismatch after documents change) is rejected and must
   be re-audited. `verify-docs --semantic-audit <file>` (a flag on
   `verify-docs`) consumes it, and Python never re-judges the verdicts.

---

## 2. In-Place Autonomous Self-Healing

When discrepancies or defects are found, the Auditor Subagent immediately
uses `Edit` to correct the Markdown files in-place without pausing to ask
the user. The Semantic Revision step reruns the affected L-layers until
the Quality Gate passes (within the configured `revision.max_rounds`
budget).
