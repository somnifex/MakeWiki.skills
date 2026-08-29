# Grounding Hierarchy & Verification Policy

## Overview

MakeWiki adopts a **Layered Verification Model (L0 - L5)** to ensure all documented capabilities are evidence-backed.

---

## 1. The L0 - L5 Verification Hierarchy

| Level  | Name               | Scope & Check Criteria                                                                                                          | Mechanical Tool                                   |
| ------ | ------------------ | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| **L0** | **Syntax**         | Markdown AST, single H1, heading hierarchy, valid internal relative links.                                                      | `OutputValidator` (`run_toolkit.py validate`)     |
| **L1** | **Existence**      | Every referenced file path, command executable, and config key exists in repository files.                                      | `CodebaseVerifier` (`run_toolkit.py verify`)      |
| **L2** | **Interface**      | CLI argument names, parameter flags, default values, environment variable keys, and type constraints match source declarations. | `CodeGroundingVerifier` + AST Parser              |
| **L3** | **Behavior**       | Documented exit codes, error conditions, log locations, and execution workflows trace to source handlers.                       | AST Extractor + ReBattle Cross-Examination        |
| **L4** | **Cross-Language** | 100% character-for-character parity of all code blocks, commands, and config keys across all language versions.                 | `CrossLanguageReviewer` (`run_toolkit.py review`) |
| **L5** | **Epistemic**      | All unconfirmed or derived claims carry consistent hedging caveats across all languages.                                        | `RevisionEngine`                                  |

---

## 2. Automated Grounding Assurance

Instead of unprovable claims of "zero-hallucination", MakeWiki provides **evidence-backed documentation with automated grounding verification**:
- **Grounding Level A**: 100% structural claims verified, 100% CLI interfaces verified, 100% config defaults verified, behavioral claims source-traced, 0 unresolved contradictions.
