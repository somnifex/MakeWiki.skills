# Anti-AI Cliché Review Rules

These rules are enforced by the LLM-driven Auditor (L5 over-assertion
audit) and cross-checked against `references/anti_ai_cliche.md` — the
authoritative writing-style guide covering register (语体), sentence
discipline, AI-tic phrasings, banned words, and the rewrite boundary. They
are part of the Quality Gate pipeline; a failure here blocks PASS unless the
writer revises or the offending claim is dropped.

## Banned Phrasing

- Binary antitheses: `不是……而是……`, `不仅……而且……`, `不仅仅是……更是一个……`
- AI-tic frames: `一句话总结`, `简单来说`, `换句话说`, `说到底`,
  `你有没有想过`, `你是否发现`, `值得注意的是`, `显然`, `不可否认`
- Verbal-noun padding: `对……进行了优化`, `实现了……的提升`, `起到了……作用`
  (`进行 / 实现 / 完成 / 开展 / 起到 / 具有` + 动名词)
- Buzzwords and AI jargon: `收敛` / `赋能` / `对齐` / `闭环` / `底层逻辑` / `抓手` /
  `深度赋能` / `沉淀` / `打法` / `势能` / `生态位` / `顶层设计` / `全链路` / `拉齐` /
  `打通` / `对标` / `勾兑` / `倒逼` / `引爆点` / `重塑格局` / `价值闭环`
- Jargon replacements: `颗粒度` → 单位 / 层级 / 精度 / 拆分口径 (by context)
- Vague references: `东西` / `那一套` / `这种感觉` / `那么回事` (replace with the
  actual referent)
- Formulaic openings: `这是……` / `这是一个……` / `以下是……` / `在本文档中我们将……`
- Slogan closings: `让我们一起……`, `共同期待……`
- Redundant colons in titles (`## 步骤 1：安装` → `## 步骤 1 安装`)
- Unfounded sources: `研究表明` / `数据显示` / `专家指出` without a real
  citation — drop the framing, keep only the judgment that stands without it;
  never invent a source
- Fabricated scene detail: invented time, weather, objects, or expressions
  (凌晨三点、凉掉的咖啡) presented as observed fact
- Unfounded praise (`powerful`, `robust`, `seamless`, `enterprise-grade`,

  …) unless backed by a cited benchmark; see
  `documentation_policy.banned_descriptors` in `makewiki.config.yaml`.

The word lists govern the move, not the literal string: reworded inflation,
empty promises, and speaking for the reader are rewritten the same way;
words carrying real meaning, domain-fixed terms (打日志、落盘), or quoted
material stay.

## Pipeline Linkage

- The Python `semantic-review` command produces aligned passages across
  languages; the Auditor reads them and applies these rules together with
  the full style guide — register (chat tone / officialese / translation
  tone), machine-polished uniform rhythm, banned words, and the rewrite
  boundary.
- The rewrite boundary governs every in-place revision: change the wording,
  never the facts — add no numbers, examples, or sources the original lacks;
  drop no core fact; keep terms, commands, code, and quotations verbatim.
- When a section cannot be grounded in evidence, the prose should render

  `UNKNOWN` rather than rewrite itself to sound more confident.
