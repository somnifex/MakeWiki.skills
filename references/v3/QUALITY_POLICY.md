# MakeWiki V3 Quality Policy

## 1. Preserve V2 quality assets

必须保留：

```text
L0-L5
SemanticAuditBundle
item-level review_item_id
documents_digest
semantic_model_digest
stale audit rejection
stable code block IDs
stable section IDs
honest four-state Quality Gate
```

## 2. Reviewer/Revision separation

V2 的 Auditor 可以边审边原地修改。

V3 改为：

```text
Reviewer
→ ReviewFindings
→ Revision Agent
→ re-review
```

Reviewer 默认只读。

## 2A. Page Reviewer vs Final Semantic Auditor

降低重复：Page Review（页面级）与 Final Semantic Audit（最终语义审定）职责收敛。

### Page Reviewer 只负责页面级 fitness/completeness

Page Review 负责：

```text
documentation fitness
audience fit
task completeness
operator completeness
API contract completeness
obvious unsupported/grounding defects
page-local cross-language issues (适用时)
```

Page Reviewer 不负责生成最终 authoritative：

```text
L3 behavior verdict registry
L4b final semantic parity verdict
L5 final epistemic verdict
SemanticAuditBundle
```

这些属于 **Final Semantic Auditor**。

仍然允许 Reviewer 发现明显 behavior/epistemic 问题（作为 finding 上报），
但不要求它完成整套 final semantic audit。

### Final Semantic Auditor 只负责最终 semantic assurance

Final Semantic Auditor 负责：

```text
L3 behavior verdicts
L4b cross-language semantic parity
L5 epistemic standing
cross-page semantic consistency
SemanticAuditBundle
stale/digest-sensitive final review
```

不要求再次全面检查：

```text
页面是否应该拆分
persona IA 是否合理
每个 how-to 是否有漂亮结构
PageSpec 是否应该存在
```

这些属于前面的 Documentation/Page Review 阶段。

Quality Gate 语义保留不变。

## 3. Review dimensions

### grounding

检查：

- source support；
- commands；
- config keys；
- interfaces；
- paths；
- examples。

### behavior

检查：

- workflow 是否达到文档声明目的；
- prerequisite；
- order；
- side effect；
- error handling。

### epistemic

检查：

- overclaim；
- guarantee；
- stale docs；
- uncertain facts；
- environment-dependent behavior。

### documentation fitness

检查：

- persona coverage；
- capability coverage；
- journey completeness；
- page intent；
- page overload；
- reference discoverability。

### audience fit

检查：

- 普通用户页面是否泄露 implementation；
- operator 信息是否足够；
- developer reference 是否混入 root-only 运维内容；
- 页面技术深度是否合适。

### abstraction correctness

新 categories：

```text
implementation_leakage
abstraction_mismatch
persona_mismatch
unsupported_product_rule
```

### task completeness

检查：

```text
goal
prerequisites
steps
expected result
recovery/caveat when important
```

### API contract review

检查：

```text
method/path
audience/auth
required params
request body
known responses/errors
side effects
idempotency when claimed
pagination/rate limit when claimed
examples
```

字段缺失本身不一定是错误。

“有证据但漏写”才是 completeness 问题。

“无证据却补写”是 grounding/epistemic 问题。

## 4. Documentation Fitness result

V3 初期建议作为 LLM review artifact，不立即硬编码成新的 Python L6。

原因：

这些判断主要是语义判断。

可以在 ReviewFindings 中表达：

```text
persona_coverage
capability_coverage
journey_coverage
operator_coverage
api_reference_coverage
page_overload
implementation_leakage
```

未来证明某些部分可机械验证后再加入工具。

## 5. Severity

建议：

```text
critical
major
minor
advisory
```

Critical 示例：

- destructive operator action documented incorrectly；
- auth/permission guidance wrong；
- endpoint method/path wrong；
- fabricated required parameter；
- critical workflow wrong。

Major：

- major capability missing；
- operator API largely undocumented；
- page serves wrong persona；
- important prerequisite omitted。

Minor：

- related link missing；
- small explanation gap；
- non-critical naming inconsistency。

## 6. Shipping policy

可以交付 pending 的行为继续由现有 Quality Gate config 控制。

但 completion report 必须区分：

```text
mechanical pending
semantic pending
documentation fitness findings
known documentation gaps
```

不能只报 grounding score。

## 7. Review loop

默认：

```text
max 2 revision rounds per page
```

仍然失败：

```text
escalate to Orchestrator
→ re-investigate or revise PageSpec/DocumentationModel
```

不能让 Writer 无限自修。

## 8. NewAPI benchmark criteria

详见：

`evals/newapi-v3-rubric.md`
