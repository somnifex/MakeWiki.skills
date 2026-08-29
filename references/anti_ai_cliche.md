# Anti-AI Cliché & Natural Voice Style Guide (去 AI 腔准则)

MakeWiki is **evidence-backed**, not "zero-hallucination": every claim is
audited through the L0–L5 verification pipeline and the Quality Gate, and
documentation reads as if a senior engineer wrote it. The rules below keep
that voice consistent across all Language Writers.

## 1. Banned Constructs

- **Binary Antitheses**: `不是……而是……`, `不仅……而且……`, `不仅仅是……更是一个……`
- **Abstract Buzzwords**: `收敛`, `赋能`, `对齐`, `闭环`, `底层逻辑`, `抓手`
- **Formulaic Openings**: `这是……`, `这是一个……`, `以下是……`, `在本文档中我们将……`
- **Trailing Colons in Headings**: `## 步骤 1：安装` → `## 步骤 1 安装`
- **Unfounded Praise**: `powerful`, `robust`, `blazing-fast`, `seamless`, `enterprise-grade` (unless backed by cited benchmark data; `documentation_policy.banned_descriptors` is the source of truth).
- **Marketing for the Toolkit Itself**: never describe `/makewiki` or its subskills with promotional adjectives — they are tools, not products.

## 2. Recommended Engineering Prose

- Active verbs first: `安装依赖`, `启动开发服务`, `配置环境变量`.
- Direct statements of factual capability without promotional hedging.
- Clean tables for parameters, configs, and status codes.
- When evidence is missing, the section renders `UNKNOWN` — do not paper over

  the gap with confident-sounding filler.

## 3. Quality Gate Linkage

The `semantic-review` command prepares aligned passages across languages for
the LLM-driven Auditor. The Auditor checks this style guide alongside the
L0–L5 layer statuses; failures surface as `hedged` L5 claims that block
PASS unless the writer revises them or the claim is dropped.