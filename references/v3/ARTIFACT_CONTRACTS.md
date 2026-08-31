# MakeWiki V3 Artifact Contracts

本文件定义认知阶段的 handoff。

初始实现优先使用 YAML/JSON/Markdown 等简单结构。

不要求立即为每个 artifact 建立复杂 Python model。

## 1. RepositoryBrief

目的：

减少后续 subagents 重复从零理解仓库。

建议：

```yaml
repository_brief:
  project_hypothesis:
    name: ""
    purpose: ""
    type: ""
    confidence: medium

  likely_users:
    - persona_hint: ""
      reason: ""

  major_areas:
    - id: ""
      meaning_hypothesis: ""
      likely_paths: []
      confidence: medium

  high_information_sources:
    - path: ""
      reason: ""

  existing_documentation:
    - path_or_url: ""
      standing: current|possibly_stale|unknown

  important_unknowns: []

  orientation_notes: []
```

全部字段由 LLM Orientation 产生。

## 2. InvestigationPlan

```yaml
investigation_plan:
  project_hypothesis: ""

  domains:
    - id: channel-management
      why_important: ""
      goal: ""
      scope_hint: []
      related_domains: []

  subtasks:
    - id: investigate.channel-management
      type: investigation
      goal: ""
      questions: []
      expected_output: claims.channel-management

  coverage_questions:
    - ""

  known_uncertainties:
    - ""
```

## 3. ClaimBundle

```yaml
claim_bundle:
  id: claims.channel-management
  domain: channel-management
  producer_subtask: investigate.channel-management

  summary: ""

  claims:
    - id: channel.create
      statement: ""
      semantic_key: channel.create
      confidence: high

      visibility:
        - admin
        - operator

      abstraction: workflow

      evidence:
        - path: ""
          symbol_or_location: ""
          rationale: ""

      uncertainty: null

  unresolved: []

  newly_discovered_areas: []

  recommended_followups: []

  scope_expansions:
    - path: ""
      reason: ""
```

### Visibility vocabulary

推荐：

```text
public
user
developer
admin
operator
root
internal
unknown
```

可以组合。

### Abstraction vocabulary

推荐：

```text
product
workflow
interface
architecture
implementation
internal
unknown
```

这是 LLM classification，不是 Python inference。

## 4. SemanticModel

V3 暂不强制一次性替换现有 Python `SemanticModel`。

语义要求：

SemanticModel 回答：

```text
What the software is.
What stable behavior/interfaces it exposes.
How major concepts relate.
Which behaviors are public/operator/developer/internal.
What remains uncertain.
```

它不应成为最终页面目录。

## 5. DocumentationModel

详见 `DOCUMENTATION_MODEL.md`。

最小：

```yaml
documentation_model:
  personas: []
  capabilities: []
  journeys: []
  concepts: []
  references: []
  interface_references: []
  documentation_gaps: []
```

## 6. DocumentationPlan

```yaml
documentation_plan:
  sections:
    - id: admin-guide
      title_intent: Administrator Guide
      persona:
        - admin
        - operator
      pages:
        - channel-management
        - routing

  relations:
    - from: channel-management
      to: routing
      type: related

  rationale:
    - ""

  no_documentation_reason: null
```

这不是 site renderer 专用 schema。

它先表达文档结构。

随后 Integrator 将它映射为 SitePresentationPlan。

**空计划必须显式解释**：当 `sections` 与 `pages` 都为空时，
`no_documentation_reason` 必须是非空文本（说明为何不需要文档）。计划只要
有实际内容（任意 `sections` 或 `pages`），`no_documentation_reason` 可以为
空——极小项目可能只有简单 page plan 而没有 relation，因此不强制
`relations` / `rationale` 非空。Python 只验证“空计划必须带 LLM-authored
explanation”，从不判断项目是否真的需要文档、哪些页面应当存在。

## 7. PageSpec

详见 `PAGE_SPEC.md`。

## 8. ReviewFindings

```yaml
review:
  page_id: channel-management
  language: zh-CN
  mode: documentation_fitness
  status: changes_required

  findings:
    - id: finding-001
      severity: major
      category: task_incompleteness
      location: "创建渠道"
      problem: ""
      evidence_refs: []
      required_change: ""

  passed_checks:
    - ""

  unresolved:
    - ""
```

Reviewer 不修改页面。

## 9. RevisionResult

```yaml
revision:
  page_id: channel-management
  language: zh-CN
  source_review: review.channel-management.zh-CN
  changes:
    - finding_id: finding-001
      action: ""

  unresolved: []

  requires_rereview: true
```

## 10. InterfaceReference

详见 `API_REFERENCE.md`。

InterfaceReference 是 DocumentationModel 的一部分，而不是 Python 自动生成的 OpenAPI。

## 11. Artifact invariants

所有关键认知 artifact 应满足：

- producer 明确；
- source/evidence 可追溯；
- uncertainty 不丢失；
- lower-confidence 不能在后续 silently 升级为 certainty；
- 后阶段不能无痕改写前阶段事实；
- LLM 可以修订 artifact，但必须有原因和新 evidence。