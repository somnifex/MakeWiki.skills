# MakeWiki V3 References

本目录包含 V3 的运行时权威文档与 contributor/migration 历史。

V3 的核心定义：

> MakeWiki 是 LLM-first、evidence-backed、subtask-first 的 Documentation Compiler。

## Runtime authority set（运行时权威）

以下文档是 MakeWiki 运行时 progressive disclosure 的权威来源。Main Agent
在执行 `/makewiki` 时按任务加载它们：

- `ARCHITECTURE.md`：V3 authoritative architecture。
- `COGNITIVE_BOUNDARY.md`：认知/机械权威边界。
- `MULTI_AGENT_PROTOCOL.md`：subagent 协作规则。
- `SUBTASK_PROTOCOL.md`：SubtaskSpec 和工作颗粒度。
- `ARTIFACT_CONTRACTS.md`：阶段 handoff。
- `DOCUMENTATION_MODEL.md`：persona/capability/journey/reference。
- `API_REFERENCE.md`：面向 operator/admin/developer 的接口文档规范。
- `PAGE_SPEC.md`：PageSpec 与 writer contract。
- `QUALITY_POLICY.md`：质量与 review 规则。

## Contributor / historical（非运行时权威）

以下文档记录 V2 baseline、迁移施工与本地维护规范。它们**不是**运行时
authority：Main Agent 不应使用它们决定当前 pipeline，实现状态以
`SKILL.md` + 上述 runtime authority set + `src/` / `tests/` 为准。

- `BASELINE.md`：V2 baseline 快照（迁移前现状记录）。
- `MIGRATION_PLAN.md`：V3 migration completion record（全部 Phase 已完成）。
- `config-migration.md`：config 迁移设计记录。
- `LOCAL_AGENT_RULES.md`：contributor maintenance 规范。