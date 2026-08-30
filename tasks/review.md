# Task: LLM Semantic Audit & Cross-Language Review (语义审查与质量门禁)

## Overview

Review is Phase 4 of MakeWiki. The **LLM Auditor** evaluates the cognitive layers
of documentation quality (L3 behavior meaning, L4b prose parity, L5 epistemic accuracy),
while the Python toolkit mechanically measures syntax (L0), existence (L1), interfaces (L2),
and exact block-ID parity (L4a).

The LLM Auditor produces an authoritative, machine-readable **`SemanticAuditBundle`**
JSON, which is consumed by the Python Quality Gate (`verify-docs --semantic-audit <file>`).

---

## 1. LLM Auditor Responsibilities

The LLM Auditor reviews the authored documentation against the source repository and SemanticModel:

1. **Behavioral Meaning (L3)**:
   - Evaluates whether documented commands and workflows accurately achieve their described purpose.
   - Identifies omitted prerequisites, incorrect step orders, or flawed execution logic.
2. **Semantic Prose Parity (L4b)**:
   - Evaluates whether descriptions, explanations, and warnings convey identical semantic meaning across all target languages.
   - Ensures that reordered sections maintain comprehensive informational parity.
   - Flags missing sections as critical parity failures.
3. **Epistemic Standing & Overclaim Review (L5)**:
   - Detects ungrounded speculation, fabricated guarantees, or unverified claims.
   - Ensures proper hedging for provisional or environment-dependent behaviors.
4. **Troubleshooting & Incident Logic**:
   - Audits error handling guides to ensure symptoms accurately trace to root causes with verifiable recovery steps.

---

## 2. Review Protocol & SemanticAuditBundle

1. **Mechanical Pre-alignment**:
   - Python extracts aligned passages and pending semantic checks via `python run_toolkit.py review <wiki_dir>` or `verify-docs <target>`.
   - Each reviewable item receives a deterministic `review_item_id` (e.g. `L3:README.md:make build`, `L4b:README:build`, `L5:README.md:myapp run`).
2. **Auditor Adjudication**:
   - The LLM Auditor evaluates each pending item.
   - In-place repairs: if a minor error is detected, the Auditor edits the Markdown files directly in `<wiki_dir>`.
3. **Bundle Emission (Must be Last)**:
   - The Auditor generates `semantic_audit.json` matching the `SemanticAuditBundle` schema:

```json
{
  "schema_version": "1",
  "documents_digest": "sha256:...",
  "semantic_model_digest": "sha256:...",
  "auditor": "LLM Auditor",
  "audited_at": "2026-08-30T10:30:00Z",
  "verdicts": [
    {
      "review_item_id": "L4b:README.md:getting_started",
      "layer": "L4b",
      "status": "passed",
      "rationale_summary": "Semantic prose and instructions match identically between EN and ZH.",
      "evidence_refs": ["README.md", "README.zh-CN.md"],
      "confidence": "high"
    }
  ]
}
```

4. **Quality Gate Verification**:
   - Run `python run_toolkit.py verify-docs <target> --wiki-dir <wiki_dir> --semantic-audit <wiki_dir>/semantic_audit.json`.
   - Python validates document digests, merges verdicts item-by-item into the Quality Gate, and reports the honest four-state verdict (`passed`, `pending_semantic_review`, `pending_mechanical_verification`, `failed`).

---

## 3. Main Agent Termination Decision

Python never decides "completion". The Main Agent evaluates:
- Coverage metrics & unresolved questions
- Tool health and recovery status
- Semantic audit results & Quality Gate verdict
- User requirements

And decides the final outcome:
- **Continue Search**: If critical coverage gaps or unproven facts remain.
- **Continue Debate**: If unresolved disputes persist.
- **Revise**: If the Quality Gate is pending or failed.
- **Deliver**: If Quality Gate is `passed` and all deliverables are compiled.
