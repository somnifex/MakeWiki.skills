# Diátaxis Quality Rubric & Information Architecture

In MakeWiki.skills, Diátaxis serves strictly as a **cognitive quality rubric**
(Learning-oriented Tutorials, Task-oriented How-To Guides, Understanding-oriented
Explanations, and Information-oriented References) to ensure comprehensive user
guidance, rather than enforcing a rigid physical file layout or mandatory templates.

The Main Agent evaluates repository traits, audience persona, and user goals to
synthesize a bespoke Information Architecture (IA).

---

## 1. The Four Diátaxis Quadrants as Cognitive Rubrics

| Quadrant                                 | Focus                               | User Need                          | Representative Content                                                 |
| ---------------------------------------- | ----------------------------------- | ---------------------------------- | ---------------------------------------------------------------------- |
| **Tutorials** (Learning-oriented)        | Onboarding & Rapid Path-to-Value    | "Help me start as a beginner"      | Zero-to-first-run walkthroughs, sample project setups, smoke tests     |
| **How-To Guides** (Task-oriented)        | Operational Procedures & Recipes    | "Help me solve a specific problem" | Step-by-step business workflows, deployment recipes, incident recovery |
| **Reference** (Information-oriented)     | Technical Specifications & Catalogs | "Give me exact technical facts"    | CLI flags, config schemas, API endpoints, env vars matrix              |
| **Explanation** (Understanding-oriented) | Architecture & Design Rationale     | "Help me understand why"           | Architecture diagrams, component interactions, design tradeoffs        |

---

## 2. Dynamic Information Architecture (IA) Synthesis

The Main Agent designs the document hierarchy, page names, and nesting based on repository shape:
- **CLI Utilities / Tools**: e.g., `README.md`, `quickstart.md`, `commands/reference.md`, `configuration.md`.
- **Libraries / SDKs**: e.g., `README.md`, `getting-started.md`, `api/reference.md`, `architecture.md`.
- **Enterprise Services / Backends**: e.g., `README.md`, `operations/runbook.md`, `configuration.md`, `deployment/kubernetes.md`.

---

## 3. Multilingual Parity & Stable ID Rules

- **Stable Block IDs**: Every technical fenced code block across all pages carries `[[id:<slug>]]` (or `[[parity:ignore reason="..."]]`).
- **Stable Section Markers**: In multilingual output, every reviewable H2 section carries `<!-- makewiki:section=<slug> -->`.
- **Flexible Flow**: Sections may be reordered natively per language to optimize reading flow; parity is keyed on stable IDs, never on heading strings or position.