# MakeWiki V3 DocumentationModel

## 1. Purpose

SemanticModel 与 DocumentationModel 必须分工。

SemanticModel：

```text
软件是什么？
```

DocumentationModel：

```text
哪些人为了什么目标，需要理解哪些概念、执行哪些任务、查询哪些 reference？
```

## 2. Persona

```yaml
persona:
  id: operator
  name: Operator
  goals:
    - deploy safely
    - monitor health
    - manage configuration
    - recover from failures
  permissions: []
  evidence_refs: []
  confidence: high
```

Persona 不应由固定名单强制。

可能包括：

```text
end-user
developer
administrator
operator
platform-admin
root
maintainer
SDK consumer
plugin author
```

## 3. Capability

Capability 是 persona 可使用或依赖的稳定产品能力。

```yaml
capability:
  id: channel.manage
  name: Manage channels
  personas:
    - admin
    - operator
  goal: Configure upstream provider connectivity.
  operations:
    - create
    - edit
    - test
    - disable
    - delete
  constraints: []
  evidence_refs: []
  visibility: admin
```

## 4. Journey

Journey 表达一个 user goal 的语义步骤。

不要求 UI 坐标或按钮描述。

```yaml
journey:
  id: channel.add
  persona: admin
  goal: Add an upstream provider channel.

  prerequisites:
    - provider credentials

  steps:
    - choose provider/channel type
    - provide credentials
    - configure supported models
    - save configuration
    - validate/test channel if supported

  expected_result:
    - channel becomes available to routing

  failure_conditions: []
  evidence_refs: []
```

如果无法从源码证明某一步，必须降低 confidence 或移除。

## 5. Concept

Concept 用于 explanation/mental model。

```yaml
concept:
  id: channel
  definition: ""
  why_it_matters: ""
  related:
    - model
    - group
    - routing
  evidence_refs: []
```

## 6. Reference

Reference 用于稳定查询。

例如：

```text
configuration keys
environment variables
CLI commands
permissions
model fields
file formats
compatibility
```

## 7. InterfaceReference

InterfaceReference 是接口类 reference。

包括：

```text
HTTP API
admin API
management API
RPC
webhook
event
health endpoint
metrics endpoint
CLI interface
```

HTTP 细节见 `API_REFERENCE.md`。

## 8. DocumentationGap

重要能力无法完整文档化时不要隐藏。

```yaml
documentation_gap:
  id: gap.admin-api.error-schema
  severity: major
  reason: >
    Route and request body are confirmed, but repository evidence does not
    establish a stable error response schema.
  affected_pages:
    - admin-api/channel-create
```

## 9. Audience hierarchy

V3 不使用一个 `audience: dual` 字符串解决全部受众。

Documentation Architect 应识别 persona-specific documentation。

一个页面可以服务多个 persona，但必须有明确理由。

典型不良混合：

```text
普通 API 用户教程
+
ORM 表结构
+
root-only 管理 API
+
生产运维恢复命令
```

## 10. Operator documentation

如果 operator persona 存在，DocumentationModel 必须显式检查：

```text
deployment
configuration sources and precedence
secrets/credential handling where evidence exists
health/readiness
metrics/observability
logs
admin/management interfaces
maintenance operations
upgrade/migration
backup/restore
failure recovery
rate/capacity constraints
dependency requirements
```

不是所有项目都有这些内容。

不存在或不能证明时不生成伪内容。

## 11. DocumentationModel coverage review

Reviewer 必须问：

- 每个 major persona 是否有足够入口？
- 每个 major capability 是否至少被一个 PageSpec 覆盖？
- 每个高价值 journey 是否有 how-to/tutorial/feature-guide？
- operator/admin interface 是否有 reference？
- public API 是否有 developer reference？
- internal-only facts 是否泄露到 end-user docs？
- 是否存在大量 capability 被塞进一个 overview？
