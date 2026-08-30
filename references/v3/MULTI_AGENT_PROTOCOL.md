# MakeWiki V3 Multi-Agent Protocol

## 1. Goal

多智能体的目的不是“多开几个 Agent”。

它用于：

- 隔离上下文；
- 减少一个 Agent 同时理解整个仓库的认知负载；
- 并行处理独立 semantic domains；
- 让 Writer/Reviewer 保持独立；
- 让不同阶段通过 artifact 而不是隐式记忆协作。

## 2. Stable role families

V3 推荐只使用少量稳定 role families：

```text
Explorer
Semantic Analyst
Documentation Architect
Writer
Reviewer
Integrator
```

Main Agent 扮演 Orchestrator。

项目特异性体现在 SubtaskSpec，而不是不断创造新的职业名称。

例如：

```text
Role: Explorer
Subtask: investigate authentication

Role: Explorer
Subtask: investigate channel/provider management

Role: Explorer
Subtask: investigate management API
```

## 3. Mandatory delegation

当宿主支持 isolated subagents/delegated workers 时，以下认知任务原则上必须 delegation：

- 独立 semantic domain investigation；
- domain-level semantic synthesis；
- hard conflict resolution；
- documentation modeling（大型项目可独立）；
- independent page writing；
- independent review；
- revision；
- integration（大型文档集可独立）。

Main Agent 不得为了省事亲自完成所有 investigation + writing + review。

## 4. Parallelism

以下任务可并行：

```text
independent investigation domains
independent page writing
independent review dimensions/pages
independent language page writing
```

以下任务通常有依赖：

```text
Semantic Synthesis depends on ClaimBundles
Documentation Modeling depends on SemanticModel
Page Planning depends on DocumentationModel
Writing depends on PageSpec
Revision depends on ReviewFindings
Integration depends on passed drafts
```

## 5. Sequential fallback

如果宿主：

- 没有 subagent；
- 只能串行；
- 只有一个 child slot；

流程语义不改变。

执行：

```text
same SubtaskSpec
same artifact contract
same stage order
```

只是串行完成。

## 6. Default depth

默认 agent delegation depth：

```text
1
```

Main Agent 可以创建 child Agent。

child Agent 默认不再创建 grandchild Agent。

如果一个 child 发现新 domain：

```text
report recommended follow-up
→ Main Agent decides whether to create a new subtask
```

## 7. Context isolation

Main Agent 给 subagent 的 context 应包含：

- role instruction；
- SubtaskSpec；
- RepositoryBrief；
- 当前任务需要的前置 artifact；
- 必要配置；
- repo access。

不要自动发送：

- 完整聊天历史；
- 所有其它 subagent 的输出；
- 整个 SemanticModel（如果只需一个 slice）；
- 全部 drafts。

## 8. Repository expansion

`scope_hint` 不是硬白名单。

Explorer 如果发现必要依赖可以扩展阅读范围。

必须在输出中记录：

```text
scope expansion
reason
new paths/domains
```

避免因为初始规划不完整而漏掉未知架构。

## 9. Role boundaries

### Explorer

允许：

- 阅读 repo；
-追踪相关 dependency；
- 提出 claims；
- 提出 follow-up。

禁止：

- 写正式 docs；
- 设计全站 IA；
- 宣布 final SemanticModel。

### Semantic Analyst

允许：

- merge claims；
- normalize semantics；
- classify visibility/abstraction；
- identify conflicts；
- produce semantic fragment/model。

禁止：

- 决定完整文档页面；
- 写最终 prose。

### Documentation Architect

允许：

- persona/capability/journey/reference；
- DocumentationPlan；
- PageSpecs。

禁止：

- 改变已经确认的 source semantics；
- 用没有 evidence 的“最佳实践”填满产品能力。

### Writer

允许：

- 按 PageSpec 写页面；
- 报告 PageSpec/evidence gap。

禁止：

- 重做全站 IA；
- 修改 SemanticModel；
- 发明新 major capability。

### Reviewer

只读。

禁止直接修 draft。

### Integrator

只处理 passed/revised artifacts。

不重新研究项目并发明事实。

## 10. Reviewer independence

最低要求：

```text
Writer context != Reviewer context
```

Reviewer 应接收：

- page；
- PageSpec；
- relevant model/evidence；
- review mode。

而不是 Writer 的完整思考过程。

## 11. Failure

Subagent 无法完成时，应返回：

```text
status: blocked
reason
what was checked
what is missing
recommended follow-up
```

不得伪造 completed。

## 12. Budget behavior

`max_subagents`、`max_parallelism` 是 ceiling，不是目标。

不要为了“充分多智能体”强行开满。

轻量仓库可以少量 subtasks。

大型仓库按 domain/page 扩展。
