# MakeWiki V3 Subtask Protocol

## 1. Subtask is the unit of work

SubtaskSpec 是 V3 的最基本 orchestration contract。

它必须足够简单，让不同 Coding Agent/Harness 直接理解，不依赖 Python scheduler。

推荐结构：

```yaml
id: investigate.management-api
type: investigation
goal: >
  Understand the management API as an operator/admin interface.

context:
  repository_brief: .makewiki/repository_brief.yaml

scope_hint:
  - routing-related source
  - management handlers
  - request/response models
  - auth/permission checks
  - relevant tests/docs

questions:
  - What operations are exposed?
  - Who may call them?
  - What inputs are accepted?
  - What responses/errors are proven?
  - What state-changing side effects exist?
  - Which details are internal only?

inputs:
  - repository_brief
  - relevant prior claims

expected_output:
  type: ClaimBundle
  id: claims.management-api

depends_on: []

stop_conditions:
  - major management operations identified
  - important uncertainties explicitly recorded
  - every important claim has evidence
```

## 2. Required fields

### id

稳定、可读。

例如：

```text
investigate.auth
semantic.channel
docmodel.global
plan.pages
write.channel-management.zh-CN
review.channel-management.zh-CN.grounding
revise.channel-management.zh-CN
integrate.zh-CN
```

### type

允许：

```text
orientation
investigation
semantic_synthesis
conflict_resolution
documentation_modeling
page_planning
writing
review
revision
integration
```

### goal

只能有一个 primary goal。

### context

说明为什么做这个任务。

### scope_hint

推荐起点。

不是硬文件 allowlist。

### questions

强制 Agent 回答的认知问题。

### inputs

明确依赖 artifact。

### expected_output

明确 artifact 类型。

### depends_on

表达顺序。

### stop_conditions

防止 Agent 无限探索。

## 3. Good granularity

好：

```text
Understand authentication and authorization semantics, including personas,
credential types, permission boundaries, failure behavior and related admin operations.
```

好：

```text
Write the operator-facing management API overview page from PageSpec X.
```

坏：

```text
Read auth.py.
```

坏：

```text
Understand entire repository and write all documentation.
```

## 4. Investigation splitting

一个 domain 过大时，可以拆：

```text
payments.core
payments.webhooks
payments.admin-api
payments.reconciliation
```

但不要拆成：

```text
payments.file-1
payments.file-2
```

## 5. Page writing granularity

默认：

```text
one PageSpec × one language = one writing subtask
```

允许例外：

- 2-3 个非常短、强相关 reference 页面；
- 很小项目。

不得默认：

```text
one language = entire documentation suite
```

## 6. Review granularity

小页面可以一次执行多个 review modes。

大页面/关键 operator API 可以拆成：

```text
grounding review
operator fitness review
API contract review
```

## 7. Completion

Subtask 结束时必须明确：

```text
completed
blocked
needs_followup
```

以及：

```text
artifact produced
uncertainties
scope expansions
```
