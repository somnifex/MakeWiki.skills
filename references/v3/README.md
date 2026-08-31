# MakeWiki V3 Refactor Authority

本目录是 MakeWiki V3 重构的设计权威。

V3 不以“重写工具”为目标。V3 的目标是在保持 V2 已有证据链、验证层、静态站点和跨语言能力的基础上，解决两个结构性问题：

1. 当前多智能体更多体现为动态角色描述，subtask 尚未成为稳定的一等工作单位。
2. 当前生成物仍容易成为“高可信技术 Wiki”，而不是按 persona、capability、journey、reference 组织的成熟产品文档。

V3 的核心定义：

> MakeWiki 是 LLM-first、evidence-backed、subtask-first 的 Documentation Compiler。

## 非目标

V3 不应演变为：

- 编程语言/框架识别器集合；
- 大量 AST/regex 启发式驱动的文档生成器；
- 某个特定 Agent Harness 的专用插件；
- 自动伪造 OpenAPI/Swagger contract 的工具；
- 依赖项目实际启动后才能完成的浏览器测试框架；
- 强制固定 Diátaxis 文件名或固定目录模板的生成器。

## 核心原则

### 1. 语义由 LLM 决定

LLM 决定：

- 项目是什么；
- 哪些部分重要；
- 哪些用户/persona 存在；
- 哪些 capability 是用户可见能力；
- 哪些步骤构成 journey；
- 哪些事实属于 internal implementation；
- 哪些 API/CLI/config/interface 对用户或运维人员构成稳定 reference；
- 文档应该如何拆页与导航；
- 一个 claim 的含义、风险和适用受众；
- 文档是否完整、误导或抽象层错误。

### 2. Python 只做确定性工作

Python 可以：

- 枚举文件；
- 提取可机械证明的事实候选；
- 验证路径/键/语法；
- 验证稳定 block ID 和 section ID；
- 校验 schema/digest；
- 编译 site/export；
- 聚合 Quality Gate 状态。

Python 不得通过规则决定：

- persona；
- capability；
- journey；
- IA；
- 页面分类；
- public/internal semantic standing；
- API operation 的业务含义；
- troubleshooting 因果；
- 文档 completeness。

### 3. Subtask 是基本工作单位

Agent role 表达能力类型。

Subtask 表达一次具体工作。

V3 优先动态生成 subtasks，而不是动态发明大量角色。

### 4. Artifact 是 Agent 之间的主要 handoff

不得主要依赖 Main Agent 把一个 subagent 的长输出重新总结给另一个 subagent。

关键阶段必须形成结构化 artifact。

### 5. Host-neutral

Skill 描述：

- subagent；
- delegated subtask；
- isolated context；
- parallel execution；
- sequential fallback。

Skill 不写具体宿主 API 名称。

### 6. API / Operator Reference 是一等能力

对于存在 HTTP API、management API、RPC、webhook、CLI、health/metrics 等操作接口的项目，DocumentationModel 必须判断是否需要面向 operator/admin/developer 的 reference。

其中 HTTP API 应尽量形成 Swagger/OpenAPI 风格的静态参考页，但任何字段都必须来自证据或 LLM 对源码的可解释分析，不得为了页面完整而猜测。

## 本目录文件

- `BASELINE.md`：固定 commit 的 V2 现状。
- `ARCHITECTURE.md`：V3 authoritative architecture。
- `COGNITIVE_BOUNDARY.md`：认知/机械权威边界。
- `MULTI_AGENT_PROTOCOL.md`：subagent 协作规则。
- `SUBTASK_PROTOCOL.md`：SubtaskSpec 和工作颗粒度。
- `ARTIFACT_CONTRACTS.md`：阶段 handoff。
- `DOCUMENTATION_MODEL.md`：persona/capability/journey/reference。
- `API_REFERENCE.md`：面向 operator/admin/developer 的接口文档规范。
- `PAGE_SPEC.md`：PageSpec 与 writer contract。
- `QUALITY_POLICY.md`：质量与 review 规则。
- `MIGRATION_PLAN.md`：增量迁移顺序。
- `LOCAL_AGENT_RULES.md`：低性能本地 Agent 施工规范。
- `PHASE_PROMPTS.md`：可逐个复制给本地 Agent 的分阶段提示词。

