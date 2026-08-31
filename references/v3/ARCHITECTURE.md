# MakeWiki V3 Architecture

## 1. Architectural statement

MakeWiki V3 is:

> an LLM-first, evidence-backed, subtask-first documentation compiler.

它通过多智能体分工理解陌生仓库，再把“代码语义”转换成“文档语义”，最终由确定性工具验证可机械证明的边界。

V3 不把仓库理解问题编码成大量 language/framework-specific rules。

## 2. Authoritative pipeline

权威流程使用纯文本定义：

```text
User request
→ Repository Orientation
→ RepositoryBrief
→ Investigation Planning
→ Investigation Subtasks
→ ClaimBundles
→ Semantic Synthesis
→ targeted Conflict Resolution when needed
→ SemanticModel
→ Documentation Modeling
→ DocumentationModel
→ Documentation Planning
→ DocumentationPlan + PageSpecs
→ Writing Subtasks
→ Draft Pages
→ Independent Review Subtasks
→ ReviewFindings
→ Revision Subtasks when needed
→ Independent Re-review
→ Integration
→ SitePresentationPlan
→ Deterministic Verification
→ SemanticAuditBundle
→ Quality Gate
→ Site / Export / Delivery
```

## 3. Repository Orientation

Orientation 是 Main Agent 可以直接承担的少数认知任务之一，因为后续 subtask 的定义依赖它。

Orientation 的目标不是完整理解仓库。

它只需要产生足以规划调查的 `RepositoryBrief`。

Orientation 应：

- 阅读高信息量入口；
- 观察目录；
- 阅读已有 docs；
- 识别 project hypothesis；
- 识别初步用户；
- 识别 major semantic domains；
- 记录不确定性。

它可以调用机械 Census 作为辅助，但 Census 不是必经前置条件。

## 4. Investigation Planning

Main Agent 根据 RepositoryBrief 生成 InvestigationPlan。

InvestigationPlan 由“语义域”组织，而不是固定 Scout 名单。

示例：

```text
authentication
provider/channel management
routing
billing
tokens
public API
management API
deployment
observability
```

真实 domain 由项目决定。

陌生项目即使使用未知目录命名，也应由 LLM 理解后动态形成 domain。

## 5. Investigation Subtasks

每个 coherent semantic domain 对应一个或多个 independent investigation subtasks。

一个好的 subtask 能形成独立认知闭环。

例如：

```text
Understand how channel/provider management works as a user-visible administrative capability:
actors, lifecycle, configuration, dependencies, public behavior, operational effects,
and which implementation details should stay internal.
```

而不是：

```text
Read channel.go
```

每个 Investigation Subtask 输出 ClaimBundle。

## 6. Semantic Synthesis

Semantic Analyst 接收：

- RepositoryBrief；
- InvestigationPlan；
- relevant ClaimBundles。

它负责：

- claim normalization；
- entity identification；
- relationship synthesis；
- user-visible capability identification；
- public/internal classification；
- abstraction classification；
- conflict detection；
- confidence；
- uncertainty。

SemanticModel 是系统语义的 canonical model。

SemanticModel 不负责决定最终页面布局。

## 7. Conflict Resolution

Conflict Resolution 是按需路径。

顺序：

```text
conflict discovered
→ Semantic Analyst re-checks evidence
→ if still ambiguous, create targeted conflict-resolution subtask
→ if still genuinely disputed, optional adversarial ReBattle
→ result returns to Semantic Synthesis
```

ReBattle 不再是所有仓库的固定 Phase。

Main Agent 不应默认亲自 Judge 每个争议。

## 8. Documentation Modeling

这是 V3 的核心新增层。

Documentation Architect 把：

```text
What the software is
```

转换成：

```text
What each audience must understand or accomplish
```

DocumentationModel 包含：

```text
Personas
Capabilities
Journeys
Concepts
References
InterfaceReferences
DocumentationGaps
```

## 9. Operator persona is first-class

如果项目存在生产部署、管理面、运维接口或管理 API，应识别 `operator` / `administrator` / `platform-admin` 等 persona。

文档不能只在 deployment page 中顺便提到运维。

可能的 operator 文档需求包括：

```text
deployment
configuration
secrets
health/readiness
metrics
logs
backup/restore
upgrade/migration
failure recovery
capacity/rate limits
admin API
management API
maintenance CLI
operational runbooks
```

只生成源码可支撑的部分。

## 10. Interface Reference

DocumentationModel 中的 InterfaceReference 对稳定接口进行建模。

接口类型可以包括：

```text
HTTP API
management/admin HTTP API
RPC
webhook/event
CLI
configuration surface
health/readiness
metrics endpoint
```

Swagger/OpenAPI-like HTTP reference 是 presentation style，不意味着必须存在 OpenAPI 文件。

如果仓库已有 OpenAPI/Swagger spec：

- LLM 应把它当作高价值证据；
- 仍应核对实际实现和版本漂移。

如果没有：

- LLM 从 route/controller/schema/validation/tests/docs 综合理解；
- 缺失字段保持 UNKNOWN；
- 不为了完整页面猜测 response/error/auth。

## 11. Documentation Planning

Documentation Architect 基于 DocumentationModel 设计 DocumentationPlan。

计划的单位是 user intent。

不要求固定：

```text
Overview
Getting Started
Installation
Configuration
Usage
API
FAQ
Troubleshooting
```

成熟项目通常应按 persona + task + reference 拆分。

## 12. PageSpec

PageSpec 是 **language-neutral** 的 Writer 直接合同：一个 `page_id` 只有一个
canonical PageSpec，所有目标语言 Writer 共享它。target language + LanguageProfile
属于 Writing Subtask，不是 PageSpec 的一部分
（`PageSpec × target language × LanguageProfile → draft`）。

Writer 不读取“全部仓库 + 一句写好文档”。

Writer 获得：

- one PageSpec（canonical，全语言共享）；
- relevant semantic slice；
- relevant documentation slice；
- source claims/evidence；
- target language + language profile（由 subtask 指定，非 PageSpec 字段）。

Writer 只写一个页面（一个 `page_id` 的一个语言 draft），或明确允许的一小组强相关页面。

## 13. Review

Review 与 Revision 分离。

Reviewer 只产生 ReviewFindings。

Review dimensions：

```text
grounding
behavior
epistemic standing
documentation fitness
audience fit
abstraction level
operator completeness
API contract completeness
cross-language parity
cross-page consistency
```

Revision Agent 只根据 findings 修复。

修复后由独立 Reviewer 再审。

## 14. Integration

Integrator 只处理已通过页面。

负责：

- path；
- navigation；
- related pages；
- terminology consistency；
- SitePresentationPlan；
- final document set。

Integrator 不重新研究整个仓库，也不添加大段新事实。

## 15. Mechanical plane

V3 继续允许 Python：

```text
census/evidence as optional evidence channels
schema validation
path existence
CLI/config/interface exact checks
Markdown syntax/link checks
stable block parity
stable section alignment
digest validation
Quality Gate aggregation
site/export/sync packaging
```

Python 不负责：

```text
semantic-domain discovery
persona inference
capability inference
journey inference
IA
page-type inference
API business-purpose inference
troubleshooting causality
operator relevance
```

## 16. Host-neutral multi-agent behavior

Skill 只规定语义：

```text
Create isolated subagents for independent cognitive subtasks when supported.
Use native host delegation mechanisms.
Run independent subtasks in parallel when supported.
If no subagent mechanism exists, execute the same SubtaskSpecs sequentially.
```

Skill 不规定工具名称。

## 17. No nested delegation by default

默认：

```text
Orchestrator
→ one level of delegated subagents
```

Subagent 不再继续无限拆 agent。

如果某宿主天然支持 agent teams，也不改变 MakeWiki 的 artifact/subtask contract。

## 18. Authority chain

```text
Repository evidence
→ LLM claim interpretation
→ SemanticModel
→ DocumentationModel
→ PageSpec
→ Draft
→ Review
→ Verification
```

后层不能反向篡改前层权威：

- Writer 不能改 SemanticModel；
- Writer 不能改 global IA；
- Reviewer 不能暗中改 draft；
- Integrator 不能发明产品事实；
- Python 不能重新裁决 semantic truth。

## 19. Completion definition

V3 只有在以下条件满足时才算完成：

```text
critical semantic domains investigated
canonical SemanticModel produced
DocumentationModel produced
operator/reference needs explicitly considered
PageSpecs cover required documentation intents
all deliverable drafts independently reviewed
required revisions re-reviewed
SemanticAuditBundle current
mechanical verification complete or honestly pending
Quality Gate reported honestly
site/export outputs produced when requested
```