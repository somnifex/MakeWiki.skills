# V2 Baseline at fda0ebf26a9f01db80b5342d7e0a3ebe69f97aca

> **Contributor / historical reference — NOT runtime authority.**
>
> It does not describe current behavior and must not be used by the Main
>
> the runtime V3 references (`references/v3/README.md`).

本文件固定 V3 重构的比较基线。它不是对 V2 的否定，而是用于防止 V3 在重构过程中丢失已经正确完成的能力。

## 1. 已确认的仓库形态

基线 commit：

`fda0ebf26a9f01db80b5342d7e0a3ebe69f97aca`

GitHub 页面显示该 commit 下仓库包含：

```text
.claude-plugin/
assets/
evals/
examples/
references/
scripts/
src/makewiki_skills/
subskills/
tasks/
templates/
tests/
AGENTS.md
CHANGELOG.md
CLAUDE.md
README.en.md
README.md
SKILL.md
makewiki.config.yaml
pyproject.toml
...
```

项目版本为 `2.0.0`。

`SKILL.md` 为约 639 行的大型 authoritative skill。

当前 `tasks/` 主要包含：

```text
build_site.md
export.md
rebattle.md
review.md
scan.md
sync.md
write.md
```

当前 `references/` 主要包含：

```text
anti_ai_cliche.md
api.md
architecture.md
claim_schema.md
diataxis_matrix.md
grounding_policy.md
schema.md
```

当前 `src/makewiki_skills/model/` 包含：

```text
claim.py
document_artifact.py
orchestration_state.py
rebattle.py
search_ledger.py
semantic_model.py
site_presentation.py
```

当前 scanner 是机械证据辅助层：

```text
coverage.py
evidence_bundle.py
evidence_collector.py
evidence_registry.py
project_detector.py
```

当前 verification 保留 L0-L5 独立模块、orchestrator、quality gate、report 和 semantic audit。

## 2. V2 已经做对的能力

这些能力是 V3 的保护对象。

### 2.1 Cognitive Authority Boundary

当前仓库已经明确：

- LLM 是 semantic authority；
- Python 不能发明 FAQ、workflow、troubleshooting、IA 等认知内容；
- 机械工具无法证明时必须返回 UNKNOWN / pending；
- Python evidence 与直接源码阅读冲突时，LLM 必须重新调查。

V3 必须保留并进一步强化这个边界。

### 2.2 Python cognitive generator 已被移除

当前 architecture contract 明确禁止恢复旧的 Python cognitive pipeline / generator / revision package。

V3 不得重新引入 Python narrative generation。

### 2.3 SemanticAuditBundle 是可靠资产

当前 SemanticAuditBundle 已具备：

- document digest 绑定；
- semantic model digest 绑定；
- item-level `review_item_id`；
- stale bundle rejection；
- Python 只校验/聚合、不重新裁决 LLM semantic verdict。

V3 应继续使用该机制。

### 2.4 L0-L5 和 honest Quality Gate

当前层级：

```text
L0 syntax               mechanical
L1 existence            mechanical
L2 interface            mechanical
L3 behavior             LLM judgment + mechanical evidence
L4 exact parity         mechanical
L4 prose parity         LLM
L5 epistemic            LLM
```

Quality Gate 使用：

```text
passed
pending_semantic_review
pending_mechanical_verification
failed
```

不得把 pending 假装成 passed。

### 2.5 Site IA 已从 Python 规则中移除

当前 site renderer 只消费 LLM-authored `SitePresentationPlan`。

Python 不再根据 filename/keyword 推断：

- Overview；
- Getting Started；
- FAQ；
- Deployment；
- nav group；
- ordering。

这是正确边界。

### 2.6 Config ownership contract 很强

当前每个 config field 必须属于：

```text
PYTHON_ONLY
LLM_ONLY
SHARED
```

contract test 还要求 LLM_ONLY 字段必须在 authoritative Skill layer 实际被引用。

这个“无死配置”原则值得保留。

### 2.7 Eval 已经考虑陌生项目陷阱

现有 eval traps 包括：

```text
hidden-entrypoint
nested-monorepo
misleading-readme
config-override
tool-failure-recovery
fork-residue
stale-example
unsupported-claim
multilingual-reorder
incomplete-scan
```

V3 应增加 documentation-quality eval，而不是替代这些 grounding traps。

## 3. 当前仍需要 V3 解决的结构问题

### 3.1 Census 仍然是 authoritative Phase 0 起点

`tasks/scan.md` 当前要求 Main Agent 先运行 `makewiki census .`，再根据 Census 动态合成 Scout topology。

这虽然比 Python 直接做语义判断好，但仍让机械信息过早决定调查入口。

V3 目标：

```text
Repository Orientation by LLM
→ RepositoryBrief
→ InvestigationPlan
→ optional mechanical evidence assistance
```

Census 可以继续存在，但降级为辅助证据。

### 3.2 Main Agent 责任仍然过重

当前 Main Agent 仍拥有：

- Scout topology；
- Search Loop；
- ReBattle dispatch；
- debate convergence；
- Judge；
- SemanticModel compilation；
- IA；
- writer division；
- delivery decision。

V3 要让 Main Agent 更接近 Orchestrator。

### 3.3 SearchLedger 是 Scout-centric，不是 Subtask-centric

当前 `SearchLedger` 主要表达：

- role；
- searched areas；
- paths inspected；
- claims；
- unresolved；
- unexplored；
- follow-ups。

缺少 V3 需要的：

- subtask identity；
- domain；
- user/public/internal visibility；
- abstraction level；
- evidence rationale；
- newly discovered domains；
- explicit stop condition result。

V3 应引入 ClaimBundle，同时保留 SearchLedger 兼容。

### 3.4 OrchestrationState 没有真正的一等 Subtask

当前 `OrchestrationState` 有：

```text
search_plan
active_agents
completed_agents
claims
conflicts
semantic_model
documentation_plan
...
```

但没有清晰的 SubtaskSpec 列表与 dependency semantics。

V3 不一定要实现 Python scheduler，但必须让 LLM orchestration 显式维护 subtasks。

### 3.5 ReBattle 仍然以 Main Agent Judge 为中心

当前 hard dispute 最终仍由 Main Agent 直接 Judge 并 compile SemanticModel。

V3 应让：

```text
normal ambiguity
→ Semantic Analyst re-investigation
→ targeted conflict-resolution subtask
→ only hard disputes use adversarial ReBattle
```

ReBattle 从阶段变成 escalation。

### 3.6 IA 仍然由 Main Agent 一次性拥有

当前 `tasks/write.md` 明确 Main Agent 设计 exact page set / nesting / writer division。

这容易回退到通用 8 页 Wiki。

V3 要加入：

```text
SemanticModel
→ DocumentationModel
→ DocumentationPlan
→ PageSpecs
```

### 3.7 Writer 粒度仍偏大

当前 Writer prompt 可以要求某语言 writer “write the complete documentation suite”。

V3 改成：

```text
one page (page_id) × one language
```

从共享的 **language-neutral PageSpec**（一个 `page_id` 一个 canonical PageSpec）取值。

或少量强相关 pages。

### 3.8 Auditor 仍然审核并原地修改

当前 Auditor 可以直接 edit Markdown，并继续决定问题是否解决。

这存在 self-confirmation 风险。

V3 要分离：

```text
Reviewer
→ ReviewFindings
→ Revision subtask
→ independent re-review
```

### 3.9 SemanticModel 混合“系统语义”和“文档语义”

当前 SemanticModel 同时包含：

- identity/config/commands；
- user_tasks；
- usage_examples；
- FAQ；
- troubleshooting；
- compatibility；
- health checks；
- deployment notes；
- log paths；
- command groups。

其中后半部分大量属于“如何文档化系统”，而不是系统自身 canonical semantics。

V3 需要渐进拆分到 DocumentationModel。

### 3.10 缺少成熟的项目接口 Reference Model

当前 `references/api.md` 是 MakeWiki 自己的内部 Toolkit CLI reference。

生成目标项目的文档并没有一等的 Swagger/OpenAPI-like endpoint contract。

尤其缺少面向 operator/admin 的：

- management API；
- auth/RBAC；
- health/readiness；
- metrics；
- maintenance endpoints；
- mutation side effects；
- pagination/filter；
- error semantics；
- idempotency；
- rate limit；
- request/response schema。

V3 必须补齐。

### 3.11 Audience 配置存在语义重叠

基线 config 同时存在：

```text
delivery.audience: dual
documentation_policy.audience: end-user
```

这会给 LLM 带来目标漂移。

V3 应逐步统一为 persona-aware documentation planning，而不是继续增加更多 audience 字符串。

### 3.12 SitePresentationPlan 当前语义上偏浅

当前模型注释假定页面树不超过两层的直接 child lookup。

V3 的成熟文档站可能需要：

```text
Guide
  Admin
    Channels
      Routing
```

后续 renderer 应支持递归层级，而不是把 IA 深度限制在两层。

## 4. V3 不允许退化的指标

重构后必须至少保持：

```text
Evidence/provenance integrity
L0-L5 honesty
SemanticAuditBundle digest binding
Stable block ID parity
Stable section ID parity
No Python semantic IA inference
No Python narrative generation
Existing CLI compatibility unless explicitly versioned
Existing site/export capabilities
Config consumption accountability
Unknown/pending discipline
```

## 5. V3 新增指标

V3 需要新增人工/LLM语义指标：

```text
Persona coverage
Capability coverage
Journey coverage
Operator coverage
API reference coverage
Page intent clarity
Page granularity
Implementation leakage rate
Audience mismatch rate
Unsupported contract field rate
Cross-page consistency
```