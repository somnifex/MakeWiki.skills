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

## 13.1 Interface coverage disposition

对每个被视为重要的 interface operation，Documentation Architect 必须显式给出
disposition，而不是静默遗漏：

```yaml
interface_disposition:
  operation_id: channel.create
  disposition: documented   # documented | grouped | omitted | unresolved
  page_id: reference/management-api/channels/create
  reason: ""                # omitted 时必填（如 internal-only）
  gap_id: ""                # unresolved 时必填
```

- `documented` / `grouped`：必须记录 `page_id`。
- `omitted`：必须有语义理由（internal-only、不适合 persona、利益低等）。
- `unresolved`：必须指向一个 `documentation_gap`。

这保证“哪些操作进文档、哪些不进”是显式决策，Python 以后只能验证 disposition
是否存在/是否完整，不能决定哪个 operation 重要或该放哪页。

## 14. Runtime exclusion

V3 不要求：

- Try it out；
- live server；
- online Swagger UI；
- runtime probing；
- screenshot。

如果后续 renderer 支持 interactive API UI，那是 presentation enhancement，不是 V3 semantic prerequisite。

## 15. Presentation — static renderer contract

InterfaceReference → renderer 的映射是**纯机械**的：静态 renderer 只把已建模的
`InterfaceReference` / `PageSpec` 数据展开成页面元素，不做任何语义推断，也不回读
源码。

### 15.1 The renderer is mechanical

renderer：

- 不读取源码；
- 不推断 auth / permission；
- 不补写 errors / responses；
- 不改变 confidence；
- 不生成任何缺失字段；
- 不决定接口重要性、分组或页面归属。

它只消费 `DocumentationModel.interface_references` 与对应的 `PageSpec`。所有被
展示的内容都必须在语义层先由 LLM 确立为事实；renderer 只负责呈现，不是证据通道。

### 15.2 Static InterfaceReference → presentation mapping

对每个 `InterfaceReference`（HTTP operation / CLI command / config item /
operational endpoint），renderer 按页面目标输出固定区域。每个区域都来自 artifact
中已经存在的字段；字段缺失或为 UNKNOWN 时，renderer 输出"未提供"或隐藏该区域，
绝不填充猜测值：

```text
operation header   <- operation id / title（来自 PageSpec.title_intent）
method + path      <- method + path（CLI/config 用 kind 专属呈现，字段已建模）
audience/permission<- audience + required role（仅当已建模）
authentication     <- auth（仅当已建模，不推断）
parameter table    <- path/query/header 参数（name、type、required、description）
request schema     <- request body（SchemaField / schema_items）
responses          <- status + response schema（来自已建模 responses）
errors             <- error conditions（ApiErrorSpec）
examples           <- 已建模的 request/response 示例
operator notes     <- operational_notes / side effects / idempotency / pagination
evidence note      <- evidence_refs + confidence 原样呈现
```

### 15.3 What the renderer must NOT do

renderer 不得：

- 从路径/方法名猜测 auth、purpose 或错误语义（见 COGNITIVE_BOUNDARY

  "Mechanical evidence is not semantic authority"）；
- 为缺失的 response/error 生成"漂亮但虚假"的 Swagger 形状；
- 提升或改写 confidence；
- 把 disposition 为 `omitted` / `unresolved` 的 operation 渲染成已文档化页面；
- 实现 interactive Try It / live probing。

### 15.4 Unmodeled fields stay unmodeled

语义层未确认的字段（例如确切的具体 400 响应 JSON）在 renderer 中只能：

- 省略对应区域；或
- 明确标注"未从仓库证据确认"（UNKNOWN discipline）。

renderer 不得生成猜测数据来补全版面。

### 15.5 Confidence and evidence are preserved verbatim

renderer 必须原样呈现 `evidence_refs` 与 `confidence`，不做数值变更、不做摘要
重写。这些由建模层设定，renderer 只是展示通道。

### 15.6 Interactive Try It is out of scope

V3 的静态 renderer 不实现 Try it out / live server / online Swagger UI（见 §14
Runtime exclusion）。若未来支持 interactive UI，那是 presentation enhancement，
不改变本契约。
