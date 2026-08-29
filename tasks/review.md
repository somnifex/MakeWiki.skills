# Task: Adversarial Review & Auto-Correction (质量审计与自愈)

## Overview

Review is Phase 4 of MakeWiki. The Reviewer Subagent validates generated Markdown documents against the actual codebase, audits cross-language parity, and performs autonomous self-healing in-place.

---

## 1. Audit Checkpoints

1. **Codebase Ground-Truth Check**:
   - Every file path in Markdown must exist on disk.
   - Every CLI command must exist in Makefile, package.json scripts, or pyproject CLI definitions.
   - Every config key must exist in scanned YAML/JSON/ENV files.
2. **Cross-Language Consistency Check**:
   - Ensures no language version has missing pages or omitted commands.
   - Checks code block parity across all languages.
3. **Markdown Quality & Anti-AI-Cliché Check**:
   - Validates heading hierarchies (single H1, no skipped heading levels).
   - Validates internal and relative markdown link destinations.
   - Scans and flags banned AI cliché words ("不是而是", "收敛", redundant colons).

---

## 2. Autonomous Self-Healing Protocol

If minor issues are detected:
- Missing command $\rightarrow$ Synchronize and insert command block into affected language file.
- Typo in path $\rightarrow$ Update relative link to valid disk path.
- AI cliché found $\rightarrow$ Rewrite sentence in-place to natural engineering tone.

---

## 3. Toolkit Review Commands

```bash
# Codebase ground-truth check
python scripts/run_toolkit.py verify <target_path> --format json

# Cross-language consistency and parity review
python scripts/run_toolkit.py review <target_path> --lang en --lang zh-CN

# Markdown structure and link validation
python scripts/run_toolkit.py validate <target_path>/makewiki
```