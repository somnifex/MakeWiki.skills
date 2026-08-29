# Anti-AI Cliché Review Rules

These rules are enforced by the LLM-driven Auditor (L5 over-assertion
audit) and cross-checked against `references/anti_ai_cliche.md`. They are
part of the Quality Gate pipeline; a failure here blocks PASS unless the
writer revises or the offending claim is dropped.

## Banned Phrasing

- `不是……而是……`
- `不仅……而且……`
- `收敛` / `赋能` / `闭环` / `底层逻辑` / `抓手`
- `这是……` / `以下是……`
- Redundant colons in titles (`## 步骤 1：安装` → `## 步骤 1 安装`)
- Unfounded praise (`powerful`, `robust`, `seamless`, `enterprise-grade`,

  …) unless backed by a cited benchmark; see
  `documentation_policy.banned_descriptors` in `makewiki.config.yaml`.

## Pipeline Linkage

- The Python `semantic-review` command produces aligned passages across

  languages; the Auditor reads them and applies these rules.
- When a section cannot be grounded in evidence, the prose should render

  `UNKNOWN` rather than rewrite itself to sound more confident.