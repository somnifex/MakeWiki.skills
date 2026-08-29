# Diátaxis & Enterprise Delivery Mapping

The page set below is produced by the Skill layer's parallel Language Writers.
Each page is rendered from the unified `SemanticModel` and verified through
the L0–L5 pipeline; empty LLM-populated sections render an `UNKNOWN` marker
rather than fabricated prose.

| Document Page        | Diátaxis Quadrant | Enterprise Delivery Equivalent | Source                          | Purpose & Content                                                                                               |
| -------------------- | ----------------- | ------------------------------ | ------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `README.md`          | —                 | Delivery Overview              | LLM                             | Quick navigation, one-sentence purpose, core features                                                           |
| `getting-started.md` | **Tutorial**      | —                              | LLM (from claims)               | 5-minute zero-to-hero onboarding workflow                                                                       |
| `installation.md`    | Reference         | **Deployment Runbook**         | python + LLM                    | Multi-platform setup, compatibility matrix, smoke test. `verify_command` is `UNKNOWN` unless a Claim proves it. |
| `configuration.md`   | **Reference**     | **Configuration Matrix**       | python (keys) + LLM (semantics) | All config keys, env vars, defaults, production advice                                                          |
| `usage/overview.md`  | **Explanation**   | Capability Map                 | LLM                             | Architecture surface, functional workflow breakdown                                                             |
| `usage/<module>.md`  | **How-To**        | Operations Manual              | LLM                             | Step-by-step business tasks with concrete commands                                                              |
| `faq.md`             | —                 | Known Limits                   | LLM-populated optional          | Empty → `UNKNOWN`. Never invented by Python.                                                                    |
| `troubleshooting.md` | —                 | **Incident Runbook**           | LLM-populated optional          | Empty → `UNKNOWN`. Symptom→Root cause→Fix steps.                                                                |
| `index.md`           | —                 | Multilingual Portal            | python                          | Language switcher and sitemap navigation                                                                        |

The Mechanical Plane (Python) produces the structural shell: frontmatter,
heading scaffolding, navigation, and machine markers. The LLM fills the
semantic content of every page directly from the verified Claims.