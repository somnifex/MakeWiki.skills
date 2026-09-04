# Contributor Maintenance Rules (small diffs, tests, stop discipline)

> **Contributor / historical reference — NOT runtime authority.**
>
> describes construction of the V3 refactor. It is maintenance guidance for
>
> **future bug fixes, benchmark-backed maintenance, and small contract
>
> frozen architecture, or running the MakeWiki documentation-generation
>
> defined by `SKILL.md`, the runtime V3 references, and the source/tests.

## 1. 永久总提示

每个维护任务前附加：

```text
你正在修改 MakeWiki.skills（3.0.0，架构已冻结）。

这是小步维护，不允许自由重写项目。

架构权威：
SKILL.md
references/v3/ARCHITECTURE.md
references/v3/COGNITIVE_BOUNDARY.md

必须遵守：

1. LLM-first：不要新增语言/框架特定的语义推断规则。
2. Python 只做确定性工作。
3. 不新增 Claude/Codex/Pi/DeepSeek 等平台专用 adapter。
4. Skill 使用 subagent/subtask 的宿主无关语义。
5. 保留 Evidence、L0-L5、SemanticAuditBundle、Quality Gate、site/export。
6. 不做无关重构。
7. 不主动执行下一个 task。
8. 修改前读取相关现有文件。
9. 修改后运行最小相关测试。
10. 发现后续问题只记录。
```

## 2. 每次只做一个 Maintenance Task

禁止把一个宽泛目标当作单个任务：

```text
重构 verification 层
```

应拆成：

```text
修复 lint X 的判定
补充 contract test Y
同步 reference 文档 Z
...
```

## 3. 修改规模

普通 task：

```text
1-2 production files
0-2 test files
```

目标 changed lines：

```text
< 200
```

明显超过时拆分。

## 4. Allowed-file prompt

每个任务都应明确：

```text
READ
MODIFY ONLY
DO NOT MODIFY
```

## 5. Stop discipline

完成后只报告：

```text
files changed
what changed
tests run
test result
unhandled findings
```

然后停止。

## 6. Test discipline

优先运行：

```text
single affected test
affected contract file
small test group
```

不要每个小任务都默认跑整个 suite。

一轮维护结束后再跑完整 suite。

## 7. Diff review prompt

每个维护任务后可以再用一个只读 Agent：

```text
Review only the current diff.
Check scope, architecture boundary, compatibility and tests.
Do not modify files.
```

## 8. 不允许弱 Agent 自主改架构

如果实现发现规范有矛盾：

```text
stop
report conflict
cite files
```

不要自己重定义 V3。

## 9. Python 修改判断

先问：

```text
如果不写 Python，这个问题会导致语义理解错误，
还是只会导致格式/确定性约束无法保证？
```

如果是语义理解：

```text
优先改 Skill/task/LLM contract
```

如果是确定性约束：

```text
可以改 Python
```

## 10. API reference 特别规则

不要让弱 Agent 编写：

```text
framework-specific route parsers
```

来“自动生成 Swagger”。

API Reference 的 canonical content 由 LLM Investigation + Documentation Architect 构造。

Python 可以未来：

- validate artifact schema；
- render tables；
- check duplicate operation IDs；
- validate known literal paths。

## 11. Commit discipline

一个 commit 一个概念。

推荐：

```text
docs(v3): add repository orientation task
docs(v3): add investigation artifact contract
model(v3): add documentation model validation
skill(v3): switch writing to PageSpec
review(v3): separate reviewer and revision
```

## 12. Architecture Freeze

MakeWiki 3.0.0 架构已冻结（release candidate 判定后正式冻结）。

维护者（含受约束预算的 agent）不得：

```text
新增 Agent role family
新增 graph engine
新增 host adapter
新增 framework-specific scanner
新增 Python semantic inference
重构整个 model hierarchy
新增 verification level
```

不得为了让代码"更漂亮"改动这里冻结的架构默认：
authoritative V3 pipeline、stable role families、SubtaskSpec、
RepositoryBrief / InvestigationPlan / ClaimBundle、SemanticModel boundary、
DocumentationModel / DocumentationPlan / PageSpec、Reviewer / Revision split、
InterfaceReference hierarchy、L0-L5、SemanticAuditBundle、
SitePresentationPlan authority boundary。

**解除 freeze 的 evidence 只有五种**（benchmark 内可重复问题 / artifact
无法表达真实语义 / contract 导致明确错误 / portability failure /
architecture-level bottleneck）。一般 prompt wording 问题改
task/reference，不改 architecture。
