# MakeWiki V3 PageSpec

## 1. Purpose

PageSpec 是 **language-neutral 的语义写作合同**。

一个 `page_id` 只有一个 canonical PageSpec，所有目标语言共享同一个 semantic
PageSpec。语言选择不属于 PageSpec：它属于 Writing Subtask。

```text
PageSpec (canonical, per page_id, language-neutral)
× target language
× LanguageProfile
→ language-specific draft
```

PageSpec 把全局文档设计与 Writer 分离。

Writer 的任务不是：

```text
Understand the repository and decide what docs to write.
```

而是：

```text
Write this documented intent accurately from these semantic inputs.
```

## 2. Core PageSpec

```yaml
page_spec:
  page_id: admin/channel-management
  page_type: feature_guide

  title_intent: Channel Management

  audience:
    - admin
    - operator

  user_goal: >
    Configure and validate upstream provider channels.

  covers:
    - channel.create
    - channel.edit
    - channel.test
    - channel.disable
    - channel.delete

  required_sections:
    - overview
    - prerequisites
    - create
    - configuration-fields
    - test-or-validate
    - update-or-disable
    - delete
    - operational-notes
    - related

  required_facts: []
  optional_facts: []

  forbidden_topics:
    - ORM implementation details
    - database indexes unless operationally relevant

  source_claims: []
  semantic_refs: []
  documentation_refs: []

  related_pages:
    - admin/channel-routing
    - reference/management-api/channels

  # compatibility / legacy: NOT authoritative for V3 target-language selection.
  # A PageSpec is language-neutral; the rendering language belongs to the Writing
  # Subtask (target language) + LanguageProfile, not to the PageSpec.
  language: null
```

## 3. Page types

建议 vocabulary：

```text
landing
tutorial
how_to
feature_guide
concept
reference
api_reference
troubleshooting
runbook
```

不需要所有项目都使用全部类型。

## 4. Page type requirements

### tutorial

必须有：

```text
learning goal
prerequisites
progressive steps
expected checkpoint/result
next step
```

### how_to

必须有：

```text
goal
prerequisites
steps
expected result
constraints/caveats when relevant
```

### feature_guide

必须有：

```text
purpose
audience
capabilities
major workflows
configuration/constraints
related reference
```

### concept

必须强调：

```text
definition
mental model
relationships
when it matters
```

避免塞长操作步骤。

### reference

必须优先：

```text
stable lookup information
types
defaults when proven
constraints
meaning
```

### api_reference

遵循 `API_REFERENCE.md`。

### troubleshooting

建议：

```text
symptom
likely cause
verification
recovery
when to escalate
```

因果无法证明时不能写成确定因果。

### runbook

面向 operator：

```text
trigger
preconditions
procedure
verification
rollback/recovery
risk notes
```

## 5. Page splitting

LLM Architect 应主动拆页，当出现：

```text
different primary persona
different independent user goal
different operational risk level
large standalone reference surface
too many unrelated major capabilities
API resource with many independent operations
```

不要使用固定 command 数量作为唯一 split rule。

## 6. API page granularity

小 API 可以一个 resource page。

大型 API 推荐：

```text
API landing/index
resource group
endpoint operation pages
```

例如：

```text
reference/management-api/
  index
  channels/
    index
    list
    create
    update
    test
    delete
```

实际颗粒度由 Architect 判断。

## 7. Writer permissions

Writer 可以：

- 调整自然段顺序；
- 使用适合目标语言的标题措辞；
- 补充经过 evidence 支持的解释；
- 报告 gap。

Writer 不可以：

- 改 global nav；
- 新建 major page；
- 修改 persona；
- 修改 canonical capability；
- 把 internal fact 提升成 public rule；
- 为了完整性猜 API schema。

## 8. Multilingual

**PageSpec 本身是 language-neutral。** 一个 `page_id` 只有一个 canonical PageSpec，
中文 Writer、英文 Writer、日文 Writer 等共享同一个 semantic PageSpec。target
language 属于 Writing Subtask，LanguageProfile 属于 Writing Subtask/context —— 二者都
不是 PageSpec 的一部分。

```text
PageSpec (canonical) × target language × LanguageProfile → language-specific draft
```

一个 canonical PageSpec 可以产生多个 language drafts。

不同语言独立母语写作。

以下 stable identity 必须由 **所有语言** 共享（Writer 不可为某个语言修改）：

```text
page_id
covers
semantic_refs
source_claim IDs
technical block identity requirements (stable [[id:...]] block IDs)
reviewable section IDs
```

Writer 不得为不同语言修改 canonical capability / page intent / persona。

只有自然语言标题和 prose 可以本地化：

```text
标题措辞
自然段顺序
```