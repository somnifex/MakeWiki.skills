# MakeWiki V3 Cognitive Authority Boundary

## Principle

最简单的判定规则：

> 需要回答“它意味着什么”的问题属于 LLM。
> 只需要回答“这个确定性条件是否成立”的问题可以属于 Python。

## LLM authority

以下判断必须由 LLM/Agent 完成。

### Repository cognition

- 项目主要目的；
- 项目类型；
- 哪些目录/文件真正重要；
- major semantic domains；
- runtime mental model；
- existing docs 是否 stale；
- fork/upstream 差异的语义含义。

### Product cognition

- persona；
- capability；
- user/operator goal；
- workflow/journey；
- privilege/role meaning；
- user-visible behavior；
- operator-visible behavior；
- internal implementation boundary。

### Documentation cognition

- 哪些内容值得写；
- 哪个 persona 需要看；
- 页面应该如何拆分；
- tutorial/how-to/reference/concept 的实际用途；
- API endpoint 是否属于 public/developer/operator/admin reference；
- 一个字段是否应该暴露给普通用户；
- 一个 implementation fact 是否会误导用户；
- troubleshooting 因果是否合理；
- documentation completeness。

### Semantic audit

- behavior correctness；
- epistemic standing；
- implementation leakage；
- abstraction mismatch；
- persona mismatch；
- task incompleteness；
- unsupported product rule；
- response/error semantics 的业务解释。

## Mechanical authority

Python 可以权威决定：

- JSON/YAML 是否 parse；
- schema 是否有效；
- path 是否存在；
- Markdown heading/link 是否满足确定规则；
- stable block ID 是否存在/重复；
- 两语言相同 block ID 的代码是否字节一致；
- section ID 是否存在；
- digest 是否一致；
- bundle 是否 stale；
- 已声明 config key 是否存在于可验证 source；
- CLI flag 字面是否存在；
- static site 是否成功 build；
- export 是否成功生成。

## Mechanical evidence is not semantic authority

机械工具输出：

```text
route: POST /admin/channels
field: priority
validator: min=0
```

不等于：

```text
这是给普通用户使用的公开 API。
priority 越高越优先。
这个 endpoint 是幂等的。
失败时返回 409。
```

后者都需要 LLM 从上下文/evidence 判断。

## No framework-specific semantic rules

禁止新增类似：

```text
if path contains /controllers/ then API
if React Router exists then user-facing UI
if filename contains admin then operator feature
if function name starts with health then health endpoint
```

作为 canonical semantic decisions。

这些可以成为 evidence hints，但不能直接生成最终 semantic fact。

## OpenAPI/Swagger boundary

如果存在 OpenAPI/Swagger specification：

Python 可以验证：

- 文件存在；
- YAML/JSON 可 parse；
- schema 基本结构；
- operationId/path 字面。

LLM 决定：

- spec 是否 stale；
- operation 对 persona 的意义；
- endpoint 的实际业务目的；
- 哪些错误/side effects 对 operator 重要；
- 如何组织 reference；
- 哪些接口属于 public/admin/internal。

## Runtime-only information

没有实际运行证据时，禁止写成确定事实的示例：

- 实际 UI 按钮位置；
- 实际 dashboard 截图内容；
- 动态 runtime values；
- 生产环境延迟；
- 实际 QPS；
- 当前外部服务状态；
- runtime-generated defaults unless source proves them。

源码可证明的静态行为仍然可以写。

## Conflict rule

当 Python evidence 与 LLM 直接源码阅读冲突：

```text
do not automatically trust Python
→ reopen investigation
→ inspect primary sources
→ record conflict
→ resolve or mark uncertainty
```

## UNKNOWN discipline

LLM 也不能为了“完成文档”猜测。

如果 API endpoint 能确认：

```text
POST /v1/items
body has name
```

但不能确认：

```text
exact 400 response JSON
```

则 reference 应：

- 省略具体响应 schema；
- 或明确标记未从仓库证据确认。

不能生成漂亮但虚假的 Swagger response。
