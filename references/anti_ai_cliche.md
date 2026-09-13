# Writing Style & Anti-AI Cliché Guide (文风与去 AI 腔准则)

MakeWiki is **evidence-backed**, not "zero-hallucination": every claim is
audited through the L0–L5 verification pipeline and the Quality Gate, and
documentation reads as if a senior engineer wrote it. The rules below keep
that voice consistent across all Language Writers, the Revision Agent, and
the Final Semantic Auditor. They are LLM-enforced; Python never scans prose.

## 0. Language Scope (语言作用域)

- **zh-CN**: every rule in this guide applies in full — register, sentence
  discipline, content-type tuning, rewrite boundary, banned words.
- **All languages**: the language-independent core applies — one idea per
  sentence; every sentence adds new information; one consistent name per
  concept; no unfounded sources; facts stated at their true strength with no
  uplifting closings; the rewrite boundary (§4). Language-specific renderings
  live in each `LanguageProfile.generation_hints`
  (`src/makewiki_skills/languages/profiles/`).

## 1. 语体 (Register)

- 默认使用规范的书面语，用词准确、专业，主谓宾完整，行文自然流畅。
- 目标是干净、有质感的书面语，接近成熟的文学表达；与聊天口吻和公文腔调都保持距离。
- 聊天腔以语气词（呀、啦、呗）和口语短语（"咱们、搞定、接得住、想清楚"）为标志；公文腔以套话和空泛的庄重（"综上所述、至关重要、有序推进"）为标志。出现即改写为相应的书面表达。
- 不写翻译腔，避免欧化长句与生硬的被动句。
- 专业术语按领域惯例使用，不刻意通俗化，也不堆砌。

## 2. 正向要求 (Sentence Discipline)

- 每句话只讲一件事，长句拆成短句。
- 长短句交替；句句长短相仿、结尾整齐，是被机器统一抛光过的节奏。
- 用常用词表达，不堆生硬的大词。
- 每句话提供新信息；重复的套话与铺垫只保留一处。
- 指称同一事物的名词就近沿用同一个叫法；为避重复升格换词，把"修表"先后写成"这门手艺""这项技能"，是另一种机器味。
- 写具体的人、事、动作、原因、结果；观点之后紧跟例子。
- 具体内容取自真实材料；凭空添上的时间、天气、物件与神态（凌晨三点、凉掉的咖啡）是伪造的现场感，删。
- 细节与数据有出处；给不出出处的"研究表明、数据显示、专家指出"，删掉铺垫，只留不依赖它也成立的判断，不编造来源。
- 形容词与副词只用于必要之处；程度与情绪用动作、细节、数字呈现，不用"非常、极其、突然"这类词。
- 按事实本来的程度陈述，不拔高、不升华；结尾在内容完结处收束，不加感想与展望。
- 标点以逗号、句号为主；冒号、破折号、引号、箭头非必要不用。
- 行文顺序由内容决定，不用"首先、其次、最后""一方面、另一方面"这类结构词。
- 上下句存在逻辑关系时把关系写明，该用"但是、因此、那么"承接就用，不靠读者自己猜；承接词承担真实逻辑，不为凑衔接硬加。
- 转折与强调直接写进句意，不借助"显然""值得注意的是""不可否认"这类提示词。

## 3. 按内容类型区分 (By Content Type)

- 叙事、描写、文学性文案（散文、故事、脚本旁白）少用副词与修饰性状语，用强动词和具体名词替代，"跑得飞快"写成"他冲出门时带翻了椅子"；只写动作与细节，不替读者总结情绪。
- 社交短文（朋友圈、微博）的语体可以略轻松，但同样避开语气词、网络流行语与聊天腔。
- 进展汇报、状态同步先写动作、结果、阻塞与风险；没有数据不写成绩，风险不写轻。
- 技术文档、公文、合同、操作手册保留"必须、严格、立即"等限定词，只删减"非常、极其"这类无信息量的修饰；术语与数字保持精确。

## 4. 改写边界 (Rewrite Boundary)

只改说法，不改事实。This binds every style-driven revision (Revision Agent,
Auditor in-place revision):

- 只改说法，不改事实；不补原文没有的数字、例子、来源与心理活动，不删核心事实，不改责任主体、因果、条件与否定关系。
- 数字、时间、单位与它修饰的对象一起保留；数量关系有歧义（"缩小了3倍"）时保留原表述并标注待确认，不替作者选定一种。
- 术语、命令、代码、引用原样保留；词本身正被讨论或引用时不动。
- 逐句通读后改写，不做按词表扫描、搜索替换式的机械改法。
- 删掉修饰后，句子落在原文已有的事实上；宁可变短，不用"有提升、见成效"这类更空的话填回去。

## 5. 常见 AI 腔换成正常说法 (AI-tic Phrasings → Plain Replacements)

- "X是Y""本质是X""核心是X""关键是X"，直接写X做了什么、导致了什么。
- "一句话总结""简单来说""换句话说""说到底"，删掉，直接给结论。
- "不是X而是Y""与其X不如Y""既X又Y"拆成普通句式；两边都真实存在、被否定的那半句有明确出处时保留对比。
- "X而且Y"拆成两句。
- "你有没有想过""你是否发现""你可能不知道"，删除，第一句直接进入正题。
- "对流程进行了优化""实现了效率的提升""起到了支撑作用"还原成动词，"把流程改顺了"。"进行、实现、完成、开展、起到、具有"后面跟动名词是典型信号。
- "东西""那一套""一个形状""这种感觉""那么回事"这类含糊代指，换成实际指的词，如产物、改动、材料、问题、来源。
- "接、跑、打、落、补、收"等肢体动作词不做比喻（"接住需求""打掉问题""补一刀"），换成实际动作；万能动词"走、打"同样换成具体动作。字面实义与领域固定术语（打日志、落盘）放行。
- "颗粒度"按语境换成单位、层级、精度或拆分口径。

## 6. 禁用词 (Banned Words)

- 不用"深度赋能、重塑格局、全新升级、多维度、底层逻辑、价值闭环、抓手、沉淀、打法、势能、生态位、顶层设计、全链路、拉齐、打通、对标、勾兑、倒逼、引爆点"等抬价词与AI黑话；沿用既有禁令：`收敛`、`赋能`、`对齐`、`闭环`。
- 不用"让我们一起""共同期待"等口号式收尾。
- 词表管的是动作不是字面：换一套字继续拔高、做空承诺、替读者总结，同样改写；词在句中承担实义或属引用时保留。
- **Formulaic Openings**: `这是……`, `这是一个……`, `以下是……`, `在本文档中我们将……`.
- **Trailing Colons in Headings**: `## 步骤 1：安装` → `## 步骤 1 安装`.
- **Unfounded Praise**: `powerful`, `robust`, `blazing-fast`, `seamless`, `enterprise-grade` (unless backed by cited benchmark data; `documentation_policy.banned_descriptors` is the source of truth).
- **Marketing for the Toolkit Itself**: never describe `/makewiki` or its subskills with promotional adjectives — they are tools, not products.

## 7. Recommended Engineering Prose

- Active verbs first: `安装依赖`, `启动开发服务`, `配置环境变量`.
- Direct statements of factual capability without promotional hedging.
- Clean tables for parameters, configs, and status codes.
- When evidence is missing, the section renders `UNKNOWN` — do not paper over the gap with confident-sounding filler.

## 8. Quality Gate Linkage

The `semantic-review` command prepares aligned passages across languages for
the LLM-driven Auditor. The Auditor checks this style guide alongside the
L0–L5 layer statuses; failures surface as `hedged` L5 claims that block
PASS unless the writer revises them or the claim is dropped.
