# MakeWiki V3 Migration Plan

## Strategy

迁移必须是“先建立新路径，再切 authoritative flow，最后清理 legacy 描述”。

不要先改根 `SKILL.md`。

## Phase A — Design authority

已由本 design pack 提供。

目标：

```text
V3 architecture frozen before implementation.
```

验收：

- `references/v3/` 已提交；
- baseline commit 被记录；
- 本地 Agent 能按规范施工。

## Phase B — Add V3 cognitive tasks without switching V2

新增 task files：

```text
tasks/orient.md
tasks/investigate.md
tasks/semantic.md
tasks/document-model.md
tasks/plan-pages.md
tasks/write-page.md
tasks/revise.md
tasks/integrate.md
```

此阶段：

- 不删除 scan/write/rebattle/review；
- 不改 authoritative SKILL；
- 主要是 prompt contracts。

## Phase C — Artifact validation layer

新增最小 schema/serialization。

推荐优先：

```text
RepositoryBrief
InvestigationPlan
SubtaskSpec
ClaimBundle
DocumentationModel
PageSpec
ReviewFindings
```

原则：

- Python 只 validate/serialize；
- 不 infer content；
- 每个 model 有明确 docstring 声明 LLM-authored。

可以新建：

```text
src/makewiki_skills/model/v3_artifacts.py
```

或按职责拆文件。

不要一开始改现有 SemanticModel。

## Phase D — OrchestrationState V3 compatibility

当前 OrchestrationState 只有 search_plan/agent records。

增量加入：

```text
subtasks
repository_brief
investigation_plan
documentation_model
page_specs
```

或创建新 V3 state。

不要实现 Python scheduler。

Python 只负责 state serialization/validation。

## Phase E — ClaimBundle compatibility

保留 SearchLedger。

新增：

```text
SearchLedger -> ClaimBundle compatibility conversion
```

注意：

转换只迁移已有结构化字段。

不得由 Python推断 visibility/abstraction。

缺失字段保持 unknown。

## Phase F — Semantic synthesis task

让 `tasks/semantic.md` 成为 V3 semantic model 生成合同。

ReBattle 改为 escalation。

此阶段可以保留旧 ReBattle CLI。

## Phase G — DocumentationModel

新增 persona/capability/journey/concept/reference/interface reference。

不要立即删除 SemanticModel 中旧 user_tasks/faq/troubleshooting。

先定义 compatibility：

```text
old fields remain readable
new V3 authoritative documentation planning uses DocumentationModel
```

## Phase H — Operator/API Reference

新增：

```text
InterfaceReference
HttpOperationReference
```

仅做 schema/contract。

不要写 framework-specific extractors。

更新 Documentation Architect prompt，让它在 applicable 时主动规划：

```text
operations/
management API/
API reference/
health and observability/
```

## Phase I — PageSpec-driven writing

切换 Writer：

```text
PageSpec × language
```

保留：

```text
stable block IDs
section markers
native multilingual writing
anti-cliché policy
```

停止“一个 language writer 写完整 suite”作为默认。

## Phase J — Independent review

重构 `tasks/review.md`：

```text
read-only Reviewer
```

新增 `tasks/revise.md`：

```text
ReviewFindings → revision
```

更新原有 contract tests：

原 contract：

```text
Auditor edits Markdown in place
```

应被新的 V3 contract 替换为：

```text
Reviewer must not edit
Revision is separate
```

这是有意 breaking architecture change，需要同步测试。

## Phase K — Documentation planning and SitePresentationPlan

DocumentationPlan 成为 IA 上游 artifact。

Integrator 将 DocumentationPlan 映射到 SitePresentationPlan。

Python SiteCompiler 仍只 render plan。

处理当前“两层 child lookup”的限制，允许递归 navigation。

这属于 renderer structural capability，不是 semantic inference。

## Phase L — Switch authoritative SKILL

当 B-K 全部可运行后，再重写根 `SKILL.md`。

新 authoritative flow：

```text
Orientation
Investigation
Semantic
DocumentationModel
PagePlan
Write
Review
Revise
Integrate
Verify
Deliver
```

Census/scan/rebattle/write legacy task 变 compatibility reference。

## Phase M — Config cleanup

处理：

```text
delivery.audience
documentation_policy.audience
```

目标转向 persona-aware planning。

不要直接删除旧字段导致 config break。

可先 deprecated 或版本迁移。

同时把 max parallelism 默认值调整到更保守值。

## Phase N — Quality contracts

保留 L0-L5。

新增 LLM Documentation Fitness review policy。

不要立即让 Python假装能计算 semantic coverage。

如果未来需要 coverage 数值，应来自 LLM-authored review artifact，Python只记录/校验结构。

## Phase O — Eval

保留原 10 个 grounding traps。

增加：

```text
NewAPI-style documentation quality
operator coverage
API reference coverage
persona separation
page granularity
implementation leakage
```

## Phase P — Documentation sync

最后更新：

```text
README.md
README.en.md
AGENTS.md
CLAUDE.md
CHANGELOG.md
references/architecture.md
```

只有已经实现的能力才能写进去。

## Full-suite checkpoints

建议在以下阶段结束跑完整 suite：

```text
C
D
G
J
L
N
P
```

其余阶段执行最小相关 tests。

## Explicitly deferred

V3 初次重构不要求：

```text
live browser screenshots
runtime API probing
interactive Swagger Try-It
framework-specific AST route generators
host-specific adapters
Python semantic scheduler
full OpenAPI emitter
```
