# NewAPI V3 Documentation Benchmark Rubric

## Purpose

NewAPI 用作 MakeWiki V3 的大型产品文档 benchmark。

本 rubric 不要求：

- 运行 NewAPI；
- 截图；
- 浏览器自动化；
- 在线 API probing。

重点检查源码/仓库可推导的 documentation quality。

## Evaluation dimensions

每项评分：

```text
excellent
acceptable
poor
not_applicable
```

并要求 reviewer 给 evidence/examples。

## 1. Repository understanding

Excellent：

- 正确识别 NewAPI 是 API gateway/management platform；
- 区分 public API、admin/operator management、deployment、UI/product management；
- 未被目录结构或旧 README 误导。

Poor：

- 只把它当普通 Go API；
- 漏掉主要 management/product domains。

## 2. Persona discovery

应合理识别例如：

```text
API consumer
regular user
administrator
operator/platform admin
developer/maintainer when applicable
```

Excellent：

不同 persona 的文档需求被明确分离。

Poor：

所有内容混入一个 “Usage”。

## 3. Capability coverage

检查重要 capability 是否被识别并进入 DocumentationModel/PageSpecs。

例如可能包括：

```text
token management
channel/provider management
routing
model mapping
groups
pricing/quota
logs
management operations
public API use
deployment/operations
```

具体列表以 benchmark commit 实际仓库为准，不硬编码为 MakeWiki 规则。

## 4. Journey coverage

至少检查：

- 一个 regular-user/API-consumer journey；
- 一个 admin journey；
- 一个 operator journey。

Excellent：

journey 有 prerequisite、semantic steps、result。

Poor：

只有字段枚举，没有 task flow。

## 5. Page granularity

Excellent：

独立 major user goals 被合理拆页。

Poor：

大量 capability 塞在 `usage/overview.md` 一页。

## 6. Task orientation

Excellent：

feature/how-to 页面围绕“我要完成什么”。

Poor：

按源码 package/struct 顺序讲解。

## 7. Operator documentation

检查：

```text
deployment
configuration
health/readiness if present
logs/observability if present
admin/management interfaces
failure/recovery guidance when source-supported
maintenance operations if present
```

Excellent：

operator 是显式 persona，不是 deployment 附录。

## 8. Public API reference

检查 public API 是否有稳定 reference。

HTTP operation 页应尽量包含：

```text
method
path
auth
parameters
request
response
error behavior
examples
```

只评价仓库有证据的内容。

## 9. Management/Admin API reference

这是 V3 重点。

Excellent：

管理 API 按资源/能力组织，有 Swagger-like lookup experience，并明确：

```text
role/permission
state-changing side effects
required inputs
known responses/errors
operational notes
```

Poor：

只在一张 endpoint 表列 method/path。

## 10. API epistemic accuracy

Excellent：

无法证明的 response schema、error code、idempotency、rate limit 被留空/UNKNOWN 或明确限制。

Poor：

为了页面完整而虚构标准 400/401/500 schema。

## 11. Concept quality

检查：

```text
channel
model
group
routing
token/quota
```

等核心概念是否解释关系，而不是只复制字段。

## 12. Implementation leakage

Excellent：

普通 user/admin guide 不被 ORM、数据库表、Go module 内部细节淹没。

内部实现只在 architecture/developer reference 中出现。

Poor：

internal constants 被写成产品规则。

## 13. Navigation quality

Excellent：

可以从：

```text
getting started
user guide
admin/operator guide
API/reference
operations
```

等用户心智路径找到内容。

实际分组由生成模型决定，不要求固定命名。

## 14. Reference discoverability

配置、CLI、API、权限等稳定查阅内容容易定位。

## 15. Troubleshooting quality

Excellent：

只给有 evidence 的 symptom/cause/recovery。

Poor：

产生泛化“检查网络/重启服务”模板。

## 16. Grounding

不得低于 V2 baseline。

重要 factual claim 有 provenance/evidence。

## 17. Cross-language parity

技术块、参数、接口 method/path、config key 一致。

自然语言可以本地化。

## 18. Documentation completeness vs hallucination balance

Excellent：

重要内容覆盖率高，同时 UNKNOWN discipline 好。

Poor 的两种极端：

```text
非常保守但漏掉大量重要功能
非常完整但充满未经证明的细节
```

## Suggested benchmark report

```yaml
newapi_v3_benchmark:
  commit: ""
  run_id: ""

  dimensions:
    repository_understanding:
      rating: excellent
      notes: ""

    persona_discovery:
      rating: ""
      notes: ""

    capability_coverage:
      rating: ""
      notes: ""

    journey_coverage:
      rating: ""
      notes: ""

    page_granularity:
      rating: ""
      notes: ""

    task_orientation:
      rating: ""
      notes: ""

    operator_documentation:
      rating: ""
      notes: ""

    public_api_reference:
      rating: ""
      notes: ""

    management_api_reference:
      rating: ""
      notes: ""

    api_epistemic_accuracy:
      rating: ""
      notes: ""

    implementation_leakage:
      rating: ""
      notes: ""

    navigation_quality:
      rating: ""
      notes: ""

    grounding:
      rating: ""
      notes: ""

    multilingual_parity:
      rating: ""
      notes: ""

  overall:
    strengths: []
    regressions: []
    blocking_issues: []
```
