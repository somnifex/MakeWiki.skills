# MakeWiki V3 Operator & API Reference Requirements

## 1. Goal

V3 生成的项目文档应在证据允许时提供类似 Swagger/OpenAPI 的接口参考体验。

目标不是生成一个看起来完整的假 OpenAPI。

目标是：

> 从仓库中可证实的接口 contract 出发，由 LLM 形成准确、按 persona 组织、可检索的 interface reference。

尤其重视：

```text
operator
administrator
developer
platform integrator
```

## 2. Interface kinds

Documentation Architect 应判断项目是否存在：

```text
public HTTP API
admin/management HTTP API
internal-but-operator-facing HTTP API
RPC
webhook
event/message contract
health/readiness endpoint
metrics endpoint
CLI
configuration interface
```

## 3. HTTP API operation contract

对于每一个被纳入文档的 HTTP operation，应尽量建立：

```yaml
operation:
  id: channel.create
  audience:
    - admin
    - operator

  method: POST
  path: /...

  purpose: ""

  auth:
    scheme: ""
    required: unknown
    permissions: []

  path_parameters: []
  query_parameters: []
  headers: []

  request_body:
    required: unknown
    content_types: []
    schema: []
    example: null

  responses:
    - status: 200
      meaning: ""
      schema: []
      example: null

  errors: []

  side_effects: []

  idempotency: unknown

  pagination: null
  filtering: []
  sorting: []

  rate_limits: unknown

  operational_notes: []

  evidence_refs: []

  confidence: medium
```

字段没有证据时：

```text
UNKNOWN
null
omit
```

禁止猜测。

## 4. Evidence sources

LLM 可以综合：

```text
route registration
handler/controller
request/response structs or schemas
validation definitions
auth/permission middleware
tests
existing docs
OpenAPI/Swagger spec
client SDK
examples
error types
service layer
```

不存在 OpenAPI spec 不影响生成 reference。

## 5. Existing OpenAPI/Swagger

如果仓库已有 spec：

LLM 必须判断：

- spec 与 route 是否一致；
- spec 是否 stale；
- server/base URL 是否环境相关；
- schema 是否实际对应 handler；
- deprecated endpoint 是否仍存在。

不能简单复制 spec 并认为全部正确。

## 6. Swagger-like page archetype

HTTP endpoint 页面建议包含：

```text
Operation title
Method + path
Purpose
Audience / permission
Authentication
Path parameters
Query parameters
Headers
Request body
Request example
Responses
Error conditions
Side effects
Idempotency / retry notes
Pagination / filtering / sorting
Operational notes
Related operations
Evidence/uncertainty note when needed
```

页面显示方式可以是 Markdown tables、tabs 或 renderer component。

内容语义不依赖 renderer。

## 7. Grouping

接口 reference 建议按资源/能力分组，而不是按源码文件。

例如：

```text
Management API
  Channels
    List channels
    Create channel
    Update channel
    Test channel
    Delete channel

  Tokens
  Users
  Models
```

具体分组由 Documentation Architect 决定。

## 8. Operator-specific API documentation

对于 operator/admin 接口，应额外关注：

```text
required role/permission
state-changing side effects
safe retry / idempotency
bulk operations
health impact
reload/restart requirements
eventual consistency if proven
pagination for large administrative lists
destructive operations
audit/log behavior if proven
rate limiting
maintenance windows if source-supported
```

## 9. Health and observability reference

如果存在 health/readiness/metrics：

页面应尽量说明：

```text
method/path or command
purpose
authentication
healthy condition
failure semantics
dependencies reflected in health
response fields
operator action when unhealthy
```

“operator action”必须有证据或清晰标注为建议性运维指导，不能伪装成软件 contract。

## 10. CLI as interface reference

对于运维 CLI：

每个 command reference 可包含：

```text
synopsis
audience
arguments
options
required permissions
inputs
outputs
exit behavior
side effects
examples
related commands
```

CLI 不是低于 HTTP API 的二等 reference。

## 11. Error documentation

不要因为 handler 存在 `return error` 就编造 HTTP status。

只有当：

- mapper；
- error type；
- test；
- spec；
- handler；

能支持具体 status/schema 时才写。

不能确认时可以写：

```text
The repository confirms this operation can fail when X, but does not establish
a stable public response schema in the inspected sources.
```

## 12. Examples

示例优先级：

```text
existing repository example
test fixture
SDK/example client
LLM-constructed syntax example from fully proven contract
```

最后一种必须只使用已确认字段，不生成未经证明的 response payload。

## 13. Coverage

Documentation Review 对接口应计算/判断语义 coverage：

```text
major public operations documented
major management operations documented
auth documented where applicable
required params documented
known response/error behavior documented
operator side effects documented
```

这个 coverage 首先由 LLM Reviewer 判断。

Python 可以未来辅助统计已有 operation IDs，但不能决定哪些 operation 是“major”。

## 14. Runtime exclusion

V3 不要求：

- Try it out；
- live server；
- online Swagger UI；
- runtime probing；
- screenshot。

如果后续 renderer 支持 interactive API UI，那是 presentation enhancement，不是 V3 semantic prerequisite。
