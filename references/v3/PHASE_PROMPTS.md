# MakeWiki V3 Local-Agent Phase Prompts

这些提示词设计给低性能本地 Agent。

每次只复制一个 Micro Task。

每个提示前附加 `LOCAL_AGENT_RULES.md` 中的永久总提示。

---

# Phase B — Cognitive Task Files

## B1 — Add orientation task

```text
TASK ID: V3-B1

GOAL
新增 Repository Orientation task。

READ
references/v3/ARCHITECTURE.md
references/v3/ARTIFACT_CONTRACTS.md
tasks/scan.md
SKILL.md

MODIFY ONLY
tasks/orient.md

REQUIREMENTS
1. Orientation 由 Main Agent 执行。
2. 输出 RepositoryBrief + InvestigationPlan。
3. Census/evidence 只能作为可选辅助。
4. 不生成 SemanticModel。
5. 不设计最终 IA。
6. 必须要求创建 independent investigation subtasks when subagents supported。
7. 不出现具体 host API 名称。

ACCEPTANCE
- 文件自洽。
- 明确 stop conditions。
- 不修改其它文件。

完成后停止。
```

## B2 — Add investigation task

```text
TASK ID: V3-B2

GOAL
新增 investigation subtask contract。

READ
references/v3/SUBTASK_PROTOCOL.md
references/v3/ARTIFACT_CONTRACTS.md
tasks/scan.md

MODIFY ONLY
tasks/investigate.md

REQUIREMENTS
1. 一个 coherent semantic domain 一个 task。
2. scope_hint 不是硬白名单。
3. 输出 ClaimBundle。
4. claim 必须带 evidence + rationale + confidence。
5. visibility/abstraction 由 LLM 判断。
6. 新 domain 只提出 follow-up。
7. 不写文档，不做全局 IA。

完成后停止。
```

## B3 — Add semantic task

```text
TASK ID: V3-B3

GOAL
新增 semantic synthesis task。

READ
references/v3/ARCHITECTURE.md
references/v3/COGNITIVE_BOUNDARY.md
src/makewiki_skills/model/semantic_model.py
tasks/rebattle.md

MODIFY ONLY
tasks/semantic.md

REQUIREMENTS
定义 ClaimBundles -> SemanticModel。
普通 ambiguity 先重新检查 evidence。
hard conflict 才升级 conflict_resolution/ReBattle。
Main Agent 不再默认 Judge。
不写最终 docs。

完成后停止。
```

## B4 — Add documentation-model task

```text
TASK ID: V3-B4

GOAL
新增 Documentation Modeling task。

READ
references/v3/DOCUMENTATION_MODEL.md
references/v3/API_REFERENCE.md

MODIFY ONLY
tasks/document-model.md

REQUIREMENTS
输出 DocumentationModel：
personas
capabilities
journeys
concepts
references
interface_references
documentation_gaps

必须显式考虑 operator/admin persona 和 management/API reference。
不固定页面目录。
不写 Markdown 页面。

完成后停止。
```

## B5 — Add page-planning task

```text
TASK ID: V3-B5

GOAL
新增 page planning task。

READ
references/v3/PAGE_SPEC.md
references/v3/DOCUMENTATION_MODEL.md
tasks/write.md

MODIFY ONLY
tasks/plan-pages.md

REQUIREMENTS
输出 DocumentationPlan + PageSpecs。
按 user intent/persona/capability 拆页。
Diátaxis 只做 rubric。
API reference 可以按 resource/endpoint 拆页。
不写最终 prose。

完成后停止。
```

## B6 — Add single-page writer

```text
TASK ID: V3-B6

GOAL
新增 PageSpec-driven writer task。

READ
references/v3/PAGE_SPEC.md
references/v3/API_REFERENCE.md
tasks/write.md

MODIFY ONLY
tasks/write-page.md

REQUIREMENTS
1. 一个 PageSpec × language。
2. 只读 relevant model/evidence slice。
3. 保留 block ID / section ID。
4. 不改 global IA。
5. 不猜 API contract。
6. 信息不足返回 gap。
7. native language writing。

完成后停止。
```

## B7 — Add revision task

```text
TASK ID: V3-B7

GOAL
新增独立 revision task。

READ
references/v3/QUALITY_POLICY.md
tasks/review.md

MODIFY ONLY
tasks/revise.md

REQUIREMENTS
ReviewFindings -> revised draft。
只修指定页面。
不自我宣布 passed。
必须重新 review。

完成后停止。
```

## B8 — Add integration task

```text
TASK ID: V3-B8

GOAL
新增 integration task。

READ
references/v3/ARCHITECTURE.md
src/makewiki_skills/model/site_presentation.py

MODIFY ONLY
tasks/integrate.md

REQUIREMENTS
只整合 passed drafts。
生成 navigation + related links + SitePresentationPlan。
不重新研究源码。
不新增 major product fact。

完成后停止。
```

---

# Phase C — Minimal Artifact Models

## C1 — Add RepositoryBrief model

```text
TASK ID: V3-C1

GOAL
增加 RepositoryBrief 的 Pydantic validation model。

READ
references/v3/ARTIFACT_CONTRACTS.md
src/makewiki_skills/model/orchestration_state.py

MODIFY ONLY
src/makewiki_skills/model/v3_artifacts.py
tests/unit/test_v3_artifacts.py

REQUIREMENTS
只实现 RepositoryBrief 相关 model。
docstring 明确 LLM-authored, Python validates only。
extra=forbid。
不实现推断函数。

ACCEPTANCE
serialization round-trip test passes。

完成后停止。
```

## C2 — Add SubtaskSpec model

```text
TASK ID: V3-C2

GOAL
增加 SubtaskSpec validation。

READ
references/v3/SUBTASK_PROTOCOL.md
src/makewiki_skills/model/v3_artifacts.py

MODIFY ONLY
src/makewiki_skills/model/v3_artifacts.py
tests/unit/test_v3_artifacts.py

REQUIREMENTS
字段：
id,type,goal,context,scope_hint,questions,inputs,expected_output,depends_on,stop_conditions。
不要增加 scheduler。
不要增加 host API。

完成后停止。
```

## C3 — Add InvestigationPlan model

同 C1/C2，只实现 InvestigationPlan。

## C4 — Add ClaimBundle model

只实现 ClaimBundle、Claim、ClaimEvidence、visibility/abstraction 字符串字段。
不要让 Python 推断 classification。

## C5 — Add ReviewFindings model

只做 validation。

---

# Phase D — OrchestrationState

## D1 — Add V3 artifact slots

```text
TASK ID: V3-D1

GOAL
让 OrchestrationState 可以保存 V3 artifacts 的引用/数据。

READ
src/makewiki_skills/model/orchestration_state.py
src/makewiki_skills/model/v3_artifacts.py
references/v3/ARCHITECTURE.md

MODIFY ONLY
src/makewiki_skills/model/orchestration_state.py
tests/contracts/test_phase3_agent_native_contracts.py

REQUIREMENTS
最小增量加入：
repository_brief
investigation_plan
subtasks
documentation_model
page_specs

保持现有字段兼容。
不实现 scheduler。
不让 Python选择 ready task。
```

---

# Phase E — ClaimBundle Compatibility

## E1 — SearchLedger conversion

```text
TASK ID: V3-E1

GOAL
提供 SearchLedger -> ClaimBundle 的兼容转换。

READ
src/makewiki_skills/model/search_ledger.py
src/makewiki_skills/model/v3_artifacts.py

MODIFY ONLY
src/makewiki_skills/model/search_ledger.py
tests/contracts/test_phase3_agent_native_contracts.py

REQUIREMENTS
只迁移可以字面迁移的字段。
visibility=unknown。
abstraction=unknown。
不要 Python 推断 persona/meaning。
保留现有 Markdown parser 行为。
```

---

# Phase F — ReBattle

## F1 — Rewrite task semantics only

```text
TASK ID: V3-F1

GOAL
把 ReBattle 从固定 Phase 改成 hard-conflict escalation。

READ
tasks/rebattle.md
tasks/semantic.md
references/v3/ARCHITECTURE.md

MODIFY ONLY
tasks/rebattle.md

REQUIREMENTS
保留 rebattle-diff helper。
删除“Main Agent default Judge”权威。
normal conflict 先 targeted resolution。
只有仍不收敛才 adversarial debate。
```

---

# Phase G — DocumentationModel

## G1 — Add documentation model validation

```text
TASK ID: V3-G1

GOAL
新增 LLM-authored DocumentationModel validation models。

READ
references/v3/DOCUMENTATION_MODEL.md
references/v3/API_REFERENCE.md

MODIFY ONLY
src/makewiki_skills/model/documentation_model.py
tests/unit/test_documentation_model.py

REQUIREMENTS
本 task 只实现：
Persona
Capability
Journey
Concept
ReferenceItem
DocumentationGap
DocumentationModel

暂不实现 HTTP operation。
所有 docstring 强调 LLM-authored。
无 inference。
```

## G2 — Add InterfaceReference models

```text
TASK ID: V3-G2

GOAL
新增 interface reference validation。

READ
references/v3/API_REFERENCE.md
src/makewiki_skills/model/documentation_model.py

MODIFY ONLY
src/makewiki_skills/model/documentation_model.py
tests/unit/test_documentation_model.py

REQUIREMENTS
实现：
InterfaceReference
HttpOperationReference
parameter/request/response 支撑结构

必须允许 unknown/null。
不得要求“完整 Swagger”。
不得生成内容。
```

---

# Phase H — PageSpec

## H1 — Add PageSpec model

```text
TASK ID: V3-H1

GOAL
新增 PageSpec validation model。

READ
references/v3/PAGE_SPEC.md

MODIFY ONLY
src/makewiki_skills/model/page_spec.py
tests/unit/test_page_spec.py

REQUIREMENTS
实现 contract 字段。
不要自动 page split。
不要自动 page type。
page_type 只验证允许值。
```

---

# Phase I — Review Separation

## I1 — Change review task to read-only

```text
TASK ID: V3-I1

GOAL
把 tasks/review.md 改成只读 Reviewer。

READ
tasks/review.md
references/v3/QUALITY_POLICY.md

MODIFY ONLY
tasks/review.md

REQUIREMENTS
移除 in-place repair。
输出 ReviewFindings。
增加 review modes：
grounding
documentation_fitness
audience_fit
api_contract
cross_language
epistemic

不要修改 Python。
```

## I2 — Replace old architecture contract expectation

```text
TASK ID: V3-I2

GOAL
更新“LLM Auditor edits Markdown in place”的 contract。

READ
tests/contracts/test_cognitive_authority_boundary.py
tasks/review.md
tasks/revise.md

MODIFY ONLY
tests/contracts/test_cognitive_authority_boundary.py

REQUIREMENTS
旧 assertion 必须替换为：
Reviewer read-only
revision separate
Python still does no semantic repair

其它 contract 不动。
```

---

# Phase J — Site hierarchy

## J1 — Recursive navigation lookup

```text
TASK ID: V3-J1

GOAL
移除 SitePresentationPlan 只能浅两层 lookup 的结构限制。

READ
src/makewiki_skills/model/site_presentation.py
tests/contracts/test_site_ia_authority_contract.py

MODIFY ONLY
src/makewiki_skills/model/site_presentation.py
相关 site presentation tests

REQUIREMENTS
nav_item_by_id 递归 children。
Python仍不能推断 IA。
不增加 filename categorizer。
```

---

# Phase K — Authoritative SKILL Switch

## K1 — Rewrite orchestration section only

```text
TASK ID: V3-K1

GOAL
只把 SKILL.md authoritative pipeline 切到 V3。

READ
全部 references/v3/
全部新 tasks/*.md
SKILL.md

MODIFY ONLY
SKILL.md
必要 contract tests

REQUIREMENTS
authoritative flow:
Orientation
Investigation
Semantic Synthesis
Documentation Modeling
Page Planning
Writing
Review
Revision
Integration
Verify
Deliver

Census/evidence = optional mechanical evidence.
ReBattle = escalation.
Subtask mandatory where host supports.
Host-neutral.
保留 L0-L5、SemanticAuditBundle、Quality Gate。

不要顺手重写 README。
```

## K2 — Replace embedded old Agent archetypes

只把巨大固定 prompt archetypes 替换为对 `tasks/*.md` 和 `references/v3/` 的 progressive disclosure 引用。

---

# Phase L — Config

## L1 — Design config migration first

```text
TASK ID: V3-L1

GOAL
只写 config migration note，不改 config.py。

MODIFY ONLY
references/v3/config-migration.md

分析：
delivery.audience
documentation_policy.audience
operator persona
API reference controls
agent parallelism

设计兼容迁移。
完成后停止。
```

后续再按 note 做独立 Micro Tasks。

---

# Phase M — Eval

## M1 — Add V3 documentation benchmark scaffolding

```text
TASK ID: V3-M1

GOAL
为 NewAPI benchmark 增加 run notes/template，不写语义 scorer。

READ
evals/newapi-v3-rubric.md
现有 eval framework

MODIFY ONLY
evals/newapi-v3/*

REQUIREMENTS
不要 Python regex 评分 prose。
允许人工/LLM rubric result。
保留现有 deterministic eval scorer 不动。
```

---

# Final Review Prompt

每完成一个 Micro Task 后：

```text
只审查当前 diff，不修改代码。

检查：
1. 是否超出 task scope。
2. 是否引入 host-specific API。
3. 是否引入 framework/language-specific semantic inference。
4. 是否把 semantic authority 交给 Python。
5. 是否破坏 V2 protected assets。
6. 是否让 Main Agent继续垄断可 delegation 的认知工作。
7. 是否出现 Writer 决定 global IA。
8. 是否出现 Reviewer 修改并批准自己的内容。
9. 是否让 API reference 猜测未知 contract。
10. 测试是否与新 architecture 一致。

输出：
PASS
或
CHANGES REQUIRED + 最小修正列表。
```
