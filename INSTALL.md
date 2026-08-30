# MakeWiki V3 Design Pack

基线仓库：

- Repository: `somnifex/MakeWiki.skills`
- Baseline commit: `fda0ebf26a9f01db80b5342d7e0a3ebe69f97aca`
- Baseline version: `2.0.0`
- Design pack purpose: 作为 V3 重构的设计权威，不直接改变现有 V2 行为。

## 放置方式

把本压缩包中的目录按原相对路径复制到 MakeWiki.skills 仓库根目录：

```text
MakeWiki.skills/
├── references/
│   └── v3/
│       ├── README.md
│       ├── BASELINE.md
│       ├── ARCHITECTURE.md
│       ├── COGNITIVE_BOUNDARY.md
│       ├── MULTI_AGENT_PROTOCOL.md
│       ├── SUBTASK_PROTOCOL.md
│       ├── ARTIFACT_CONTRACTS.md
│       ├── DOCUMENTATION_MODEL.md
│       ├── API_REFERENCE.md
│       ├── PAGE_SPEC.md
│       ├── QUALITY_POLICY.md
│       ├── MIGRATION_PLAN.md
│       ├── LOCAL_AGENT_RULES.md
│       └── PHASE_PROMPTS.md
└── evals/
    └── newapi-v3-rubric.md
```

建议先只提交这些设计文件：

```bash
git add references/v3 evals/newapi-v3-rubric.md
git commit -m "docs: add MakeWiki v3 architecture and migration authority"
```

在本地低性能 Agent 开始任何代码修改前，要求它至少阅读：

```text
references/v3/README.md
references/v3/ARCHITECTURE.md
references/v3/COGNITIVE_BOUNDARY.md
references/v3/LOCAL_AGENT_RULES.md
references/v3/MIGRATION_PLAN.md
```

然后一次只执行 `PHASE_PROMPTS.md` 中的一个 Micro Task。

## 权威优先级

V3 重构期间发生冲突时，按以下顺序处理：

1. 用户对 V3 的明确目标。
2. `references/v3/ARCHITECTURE.md`
3. `references/v3/COGNITIVE_BOUNDARY.md`
4. `references/v3/*_PROTOCOL.md` / artifact contracts
5. `references/v3/MIGRATION_PLAN.md`
6. 当前 V2 contract tests，用于保护已有正确能力
7. 当前 V2 文档中与 V3 设计相冲突的旧流程描述

V3 实现尚未切换 authoritative pipeline 之前，不应让新增规范破坏 V2 的正常使用。
