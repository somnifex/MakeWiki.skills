# Task: Subagent Adversarial Review & Self-Healing (审查员审计与自愈)

## Overview

Review is Phase 4 of MakeWiki. The **Auditor Subagent** executes an autonomous cognitive audit and in-place self-healing pass, ensuring 100% cross-language parity, code grounding, and natural technical prose.

---

## 1. Auditor Subagent Responsibilities

1. **Side-by-Side Cross-Language Parity**:
   - Compares English and Chinese Markdown documents side-by-side.
   - Verifies that all code blocks, command arguments, and config keys match character-for-character across all languages.
2. **Codebase Ground-Truth Verification**:
   - Verifies that every documented CLI command, file path, and env var actually exists in the target repository.
3. **Anti-AI Cliché & Natural Human Voice Audit**:
   - Identifies and rewrites formulaic templates ("不是……而是……", "不仅……而且……").
   - Purges empty corporate buzzwords ("收敛", "赋能", "对齐").
   - Cleans up trailing colons in headings.

---

## 2. In-Place Autonomous Self-Healing

When discrepancies or defects are found, the Auditor Subagent immediately uses `Edit` to correct the Markdown files in-place without pausing to ask the user.