---
name: makewiki
description: "Generate enterprise-grade multilingual wiki documentation and an offline static website for a software project using autonomous collaborative subagents and ReBattle competitive verification. Use when: user asks to generate wiki, docs, documentation, enterprise delivery manuals, or multilingual docs for a project."
version: "2.0.0"
argument-hint: "[--lang <code>...] [--output <dir>] [--theme <auto|light|dark>]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Read Write Edit Glob Grep WebFetch
---
# MakeWiki v2 - Autonomous Multi-Agent Multilingual Wiki Generator

Generate high-quality, zero-hallucination, multilingual wiki documentation and an interactive offline static website with **full autonomy (zero human intervention required)**.

---

## 1. Subagent-First Cognitive Architecture (以 Subagent 为核心的智能协同体系)

MakeWiki adopts an **Autonomous, Self-Reflecting, Self-Configuring Subagent Architecture**: all deep comprehension, multi-perspective analysis, adversarial debate, documentation writing, and adversarial auditing are performed by **LLM Subagents with internal self-reflection loops**. Python scripts are strictly relegated to **deterministic mechanical plumbing** (such as assembling HTML SPA files or packaging EPUB zip archives).

```yaml
orchestration_topology:
  orchestrator:
    role: "Main Agent (Chief Adjudicator & Dispatcher)"
    capabilities:
      - Dynamic project sizing & on-demand subagent role synthesis
      - Elastic subagent budgeting (capped at 10) & task fission
      - ReBattle adversarial dispute arbitration
      - Compilation of canonical SemanticModel (source of truth)

  execution_pipeline:
    phase_1_recon:
      subagents:
        - name: "Scout-Structure"
          scope: "Scan package manifests, build scripts, CI/CD, and top-level directory layout"
        - name: "Scout-Surface"
          scope: "Scan CLI entrypoints, flags, API routes, and .env.example"
        - dynamic: "On-demand specialized Scouts synthesized for unique tech stacks"
      output: "Structured evidence facts with source file line citations"

    phase_2_rebattle:
      subagents:
        - name: "Agent Red (User & DX)"
          focus: "User onboarding workflows, runnable commands, tutorials, expected output"
        - name: "Agent Blue (Code AST & Ground-Truth)"
          focus: "AST functions, exported symbols, flags verification, stub warnings"
        - name: "Agent Green (Enterprise Ops)"
          focus: "Runtime compatibility, env vars matrix, error runbooks"
      interaction: "3-way adversarial cross-examination debate with self-reflection & claim retraction"
      adjudication: "Main Agent resolves objections into canonical SemanticModel"

    phase_3_writers:
      subagents:
        - name: "Language Writers (en, zh-CN, ja, etc.)"
          focus: "Parallel independent native authoring directly from SemanticModel"
      constraints: "100% code block and config key parity across languages"

    phase_4_review:
      subagents:
        - name: "Auditor Subagent"
          focus: "Cross-language parity audit, grounding check, anti-AI-cliché audit"
          action: "Autonomous in-place self-healing"

    phase_5_site:
      mechanism: "Deterministic Python Site Compiler (run_toolkit.py build-site)"
      output: "Standalone single-file offline HTML SPA wiki"
```

---

## 2. Dynamic Self-Configuration & Subagent Synthesis (动态角色合成与弹性配置)

Rather than forcing a rigid, static agent roster, the Main Agent **dynamically synthesizes and configures Subagents** based on the target project's tech stack and complexity:

```yaml
dynamic_synthesis_rules:
  monorepo_or_microservices:
    trigger: "Multiple services, workspaces, or sub-packages detected"
    action: "Spawn dedicated Scout/Writer subagents per major service module (within global budget)"

  native_or_ffi_bindings:
    trigger: "C/C++, Rust FFI, WebAssembly, or Python C-extensions detected"
    action: "Synthesize 'Scout-ABI-Bindings' to inspect header files and exported ABI bindings"

  plugin_or_sdk_ecosystem:
    trigger: "Extensible plugin architecture or public client SDK detected"
    action: "Synthesize 'Agent-Ecosystem' focusing on hook registration and SDK interfaces"

  elastic_budget_cap:
    hard_limit: 10
    policy: "Dynamically allocate agent budget: Tier S (1-2), Tier M (3-5), Tier L (5-10 max)"
```

---

## 3. Subagent Self-Reflection & Self-Critique Loop (子代理自反思四维校验)

Every Subagent must execute a mandatory **internal 4-dimensional self-reflection pass** before submitting claims or writing documents:

```yaml
self_reflection_checklist:
  1_grounding_critique:
    question: "Is every command, argument flag, config key, and file path directly cited with actual code lines?"
    remedy: "Strip or explicitly hedge any speculative assertions as [INFERRED/UNCONFIRMED]."

  2_parity_critique:
    question: "Does my code sample, config snippet, or CLI invocation match 100% with the canonical SemanticModel?"
    remedy: "Synchronize parameter names and command syntax character-for-character."

  3_anti_ai_cliche_critique:
    question: "Did I inadvertently generate binary tropes ('不是……而是……', '不仅……而且……'), empty buzzwords ('收敛', '赋能', '对齐'), or colon-stuffed headings?"
    remedy: "Rewrite in direct, natural, active engineer prose."

  4_adversarial_defense_critique:
    question: "If an opposing agent challenges this assertion with AST evidence, will this claim withstand inspection?"
    remedy: "Refine claim confidence: CONFIRMED_AST, DERIVED_CONFIG, or HYPOTHESIS_HEDGED."
```

---

## 4. Subagent Dispatch Prompts with Embedded Reflection

When spawning subagents via `invoke_subagent` or delegation, provide each with its task prompt including the self-reflection requirement:

#### 1. Scout-Structure Prompt
```markdown
You are Scout-Structure for project '{project_name}'.
Your goal is to autonomously explore and comprehend the repository architecture using Glob, Grep, and Read tools:
1. Identify all package manifests (pyproject.toml, package.json, go.mod, Cargo.toml, pom.xml).
2. Inspect build and deployment configurations (Makefile, Dockerfile, docker-compose.yml, CI workflows).
3. Map top-level directory structure and module boundaries.
Self-Reflection Step: Verify that all reported file paths actually exist on disk before reporting.
Output a structured summary with: project_type, dependencies, build commands, and verified file paths with line citations.
```

#### 2. Scout-Surface Prompt
```markdown
You are Scout-Surface for project '{project_name}'.
Your goal is to extract public interfaces and developer surfaces using Glob, Grep, and Read tools:
1. Scan main CLI entrypoints and extract help texts, flags, and parameter options.
2. Scan Web/API route definitions and extract HTTP methods and endpoint paths.
3. Read .env.example, config templates, and existing READMEs for declared configuration keys.
Self-Reflection Step: Confirm each parameter and route against actual source declarations.
Output a verified list of commands, parameters, and environment variables with source file citations.
```

#### 3. Agent Red (User & DX Perspective) Prompt
```markdown
You are Agent Red (Developer & User Experience).
Analyze the project from the perspective of an external developer or end-user:
1. Formulate the 5-minute quickstart onboarding workflow from git clone to first run.
2. Extract primary CLI commands, required flags, and expected terminal outputs.
3. Map common daily usage scenarios.
Self-Reflection Step: Challenge your own tutorial — did you assume any implicit prerequisites or omit setup steps?
Label each claim: CONFIRMED_AST, DERIVED_CONFIG, or HYPOTHESIS_HEDGED.
```

#### 4. Agent Blue (Code AST & Ground-Truth) Prompt
```markdown
You are Agent Blue (Code Implementation & AST Verifier).
Inspect the source code to verify factual accuracy and challenge ungrounded assertions:
1. Audit commands and flags proposed by Agent Red against actual argument parsers or route tables in source code.
2. Check default values, type constraints, and fallback logic directly in the codebase.
3. Identify unreleased features, stub functions, or deprecated parameters.
Self-Reflection Step: Ensure every objection you raise is backed by exact file line references.
Output verified implementation facts and explicit objection challenges against ungrounded user claims.
```

#### 5. Agent Green (Enterprise Deployment & Ops) Prompt
```markdown
You are Agent Green (Enterprise Delivery & Operations).
Analyze the project for deployment and production reliability:
1. Compatibility matrix: Supported OS, runtime versions, database dependencies.
2. Configuration matrix: Environment variables, config files, required vs optional settings, default values, production recommendations.
3. Incident runbook: Error messages found in source code, root causes, log locations, and troubleshooting resolution steps.
Self-Reflection Step: Check if every error message symptom maps to a verified resolution.
Output deployment runbook facts and operational failure recovery steps.
```

#### 6. Language Writer Subagent Prompt
```markdown
You are the {language_name} Documentation Writer for project '{project_name}'.
Write the complete documentation suite in {language_name} using the unified SemanticModel provided.
Requirements:
1. Independent generation: Write native, high-quality technical {language_name} directly from the SemanticModel — NEVER translate from another language output.
2. Code block parity: All command code blocks, configuration keys, and parameter flags must remain 100% identical across all language versions.
3. Diátaxis structure: Write README.md, getting-started.md, installation.md, configuration.md, usage/*.md, faq.md, troubleshooting.md, and index.md.
4. Self-Reflection Step: Run the 4-dimensional self-reflection check:
   - Check grounding of all commands.
   - Confirm 100% parity with SemanticModel.
   - Purge AI clichés: NO "不是……而是……", NO "不仅……而且……", NO "收敛/赋能", NO redundant colons.
Save all generated files under '{output_dir}/'.
```

#### 7. Reviewer & Quality Auditor Subagent Prompt
```markdown
You are the Quality Auditor and Reviewer for the generated documentation in '{output_dir}/'.
Perform an autonomous audit and self-healing pass:
1. Run codebase grounding verification to confirm all mentioned commands, config keys, and file paths exist.
2. Run cross-language consistency review: ensure every code block and parameter in English matches Chinese and all other languages 1:1.
3. Scan for broken Markdown links and AI clichés.
4. Autonomous Self-Healing: If minor discrepancies, typos, or missing commands are found, edit and correct the Markdown files in-place immediately without asking the user.
```

---

## 5. Subagent Budgeting & Sizing Tiers

The Main Agent **automatically assesses project complexity** in Phase 0 without prompting the user:

| Project Tier | Sizing Criteria | Subagent Budget | ReBattle Protocol | Subagent Allocation |
| :--- | :--- | :--- | :--- | :--- |
| **Tier S (Simple)** | Source files < 15, single entrypoint | **1 ~ 2 Subagents** | Prompt-based self-review (0 debate rounds) | Main Agent (Scout + Judge) + 1~2 Parallel Writers |
| **Tier M (Medium)** | Source files 15~80, 5~15 commands | **3 ~ 5 Subagents** | Red vs Blue (1 debate round) | 1 Scout + 2 ReBattle (Red, Blue) + 2 Writers |
| **Tier L (Large)** | Source files > 80, Monorepo / Multi-module | **5 ~ 10 Subagents (Hard Cap)** | Red + Blue + Green (2 debate rounds) | 2 Scouts + 3 ReBattle + Parallel Writers + 1 Reviewer |

---

## 6. Documentation Standards (Enterprise Delivery + Diátaxis)

Every generated documentation set must fulfill **two core requirements**:
1. **Developer Rapid Onboarding (Diátaxis Framework)**: Help developers understand the project in 5 minutes and perform daily tasks.
2. **Enterprise & Commercial Delivery Standard**: Provide rigorous deployment runbooks, compatibility matrices, configuration references, and incident recovery guides.

### Diátaxis & Enterprise Structure

| Base Page | Diátaxis Quadrant | Enterprise Delivery Equivalent | Core Content |
| :--- | :--- | :--- | :--- |
| `README.md` | — | Delivery Overview | One-sentence purpose, key capability highlights, quick navigation |
| `getting-started.md` | **Tutorial** | — | 5-minute zero-to-hero workflow from clone to first successful run |
| `installation.md` | Reference | **Deployment Runbook** | Multi-platform setup, compatibility matrix (OS × runtime), verify commands, smoke test |
| `configuration.md` | **Reference** | **Configuration Matrix** | Every config key & env var: type, default, required, production recommendation |
| `usage/overview.md` | **Explanation** | Capability Map | Feature modules breakdown, workflow dependencies, architecture surface |
| `usage/<module>.md` | **How-To** | Operations Manual | Step-by-step business tasks, concrete commands, expected output |
| `faq.md` | — | Known Limits | Real issues, common pitfalls, boundary constraints |
| `troubleshooting.md` | — | **Incident Runbook** | Symptom (with real error messages) → Root Cause → Resolution Steps → Log paths |

### Anti-AI Cliché & Natural Human Voice Rules (去 AI 腔与自然人声准则)

文档是写给**真实人类工程师与用户**阅读的，必须条理清晰、表述自然、切中要害，严禁产生“机器模板腔”：

1. **严禁二元对比式套话**：
   - ❌ 绝对禁止使用 `不是……而是……`、`不仅……而且……`、`不仅仅是……更是一个……` 等对仗套话。
   - ✅ 直接阐述事实（例如写“MakeWiki 基于代码仓库中的配置和脚本生成文档”，不要写“MakeWiki 不是一个简单的翻译工具，而是一个……”）。
2. **严禁虚浮抽象大词**：
   - ❌ 禁用 `收敛`、`对齐`、`赋能`、`闭环`、`底层逻辑` 等泛化黑话。
   - ✅ 使用具体的工程动作：`校验`、`同步`、`生成`、`配置`、`处理`。
3. **严禁机械死板的开场白与代词堆砌**：
   - ❌ 禁用 `这是……`、`这是一个……`、`以下是……`、`在本文档中我们将……` 等废话。
   - ✅ 开门见山，动词先行（例如直接说明“安装依赖”、“运行启动命令”）。
4. **禁止滥用冒号与过度符号化**：
   - ❌ 标题和列表项严禁滥用冒号（禁止 `## 步骤 1：安装`、`## 核心特性：多语言`、`**注意：**` 后再加冒号）。
   - ❌ 禁止无休止的加粗冒号列表堆砌。
   - ✅ 采用流畅自然的段落说明与标准 Markdown 表格。
5. **拒绝生硬机翻腔**：
   - 中文文档遵循地道技术中文习惯，中英文之间保留空格，专有名词保持原有大小写，不生造怪异译词。

### Non-Negotiable Documentation Rules

1. **Independent generation, NEVER machine-translate**: Write each language version from the unified Semantic Model.
2. **Code Block Parity**: All command code blocks, configuration keys, and parameters must remain 100% identical across all languages.
3. **No Unfounded Praise**: Never use `powerful`, `robust`, `blazing-fast`, `enterprise-grade`, `seamless`, `production-ready` unless cited from verified benchmark evidence.
4. **Observable Behavior Only**: Write what users type and see. Never write internal source directory tours or developer-only architecture essays in user guides.
5. **Strict Hedging**: When evidence is indirect, explicitly hedge (*"The repository contains X, suggesting Y may be supported"*).

---

## 7. Six-Phase Subagent-Driven Execution Workflow

### Arguments

Parse `$ARGUMENTS` for:
- `--lang <code>` (repeatable): Target language codes. Default: `en zh-CN`. Supported: `en`, `zh-CN`, `ja`, `de`, `fr`, etc.
- `--output <dir>`: Output directory name. Default: `makewiki`.
- `--theme <auto|light|dark>`: Static site theme. Default: `auto`.

---

### Step 1: Bootstrap the home-scoped toolkit

Use the bundled bootstrap script. It prepares `<makewiki_root>` at `HOME/.makewiki` on Windows, macOS, and Linux. The launcher at `<makewiki_root>/scripts/run_toolkit.py` then bootstraps `<makewiki_root>/.venv`, preferring `uv` and falling back to `python -m venv`.

Run this bootstrap command:

```bash
python scripts/bootstrap_toolkit.py
```

---

### Phase 0: Autonomous Project Sizing & Dynamic Subagent Synthesis

1. The Main Agent counts project source files or runs `python <makewiki_root>/scripts/run_toolkit.py sizing .`.
2. Assess project complexity (`Tier S`, `Tier M`, or `Tier L`) and dynamically synthesize subagent roles according to project characteristics.

---

### Phase 1: Autonomous Codebase Reconnaissance (Scout Subagents)

Launch **Scout Subagents** directly into the codebase:
- **`Scout-Structure Subagent`**: Uses `Glob` and `Read` to inspect package manifests (`pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`), Makefile, CI workflows, Dockerfiles.
- **`Scout-Surface Subagent`**: Uses `Grep` and `Read` to inspect README, CLI entrypoints, help flags, and `.env.example`.

Both subagents return structured factual evidence with file and line citations after self-critique.

---

### Phase 2: ReBattle Adversarial Cross-Examination & Adjudication

Deploy multi-perspective subagents for adversarial verification:

#### 1. Blind Extraction with Self-Reflection (Round 1)
- **Agent Red (User & DX)**: Extracts runnable CLI commands, onboarding tutorial paths, and expected outputs.
- **Agent Blue (Code AST & Ground Truth)**: Inspects source code functions, exports, handlers, and stub/deprecated warnings.
- **Agent Green (Enterprise Ops)**: Extracts compatibility matrices, environment variables, health checks, and error runbooks.

#### 2. Cross-Examination & Debate (Round 2)
The subagents challenge each other's claims:
- Agent Blue challenges Agent Red: *"Command `--fast` does not exist in cli.py parser; flag is invalid."*
- Agent Green challenges Agent Red: *"Quickstart tutorial omits mandatory `DB_PORT` environment variable."*
- Agent Red challenges Agent Blue: *"Function `export_csv` is exposed via CLI even though marked internal."*

#### 3. Adjudication & Unified Semantic Model (Round 3)
The Main Agent acts as **Judge**:
- Adjudicates disputed claims using codebase facts.
- Rejects ungrounded claims, hedges uncertain capabilities, and compiles the authoritative **`SemanticModel`** (`semantic_model.json`).

---

### Phase 3: Parallel Multilingual Writers (Subagent Authors)

For each target language (`en`, `zh-CN`, `ja`, etc.):
- Spawn an independent **Language Writer Subagent**.
- Each Writer receives the **same adjudicated SemanticModel**.
- Each Writer executes internal self-reflection (grounding, parity, anti-cliché) and writes the complete native Markdown documentation set into `<output_dir>/`:
  - `README.md` / `README.<lang>.md`
  - `getting-started.md` / `getting-started.<lang>.md`
  - `installation.md` / `installation.<lang>.md`
  - `configuration.md` / `configuration.<lang>.md`
  - `usage/overview.md`, `usage/<slug>.md`
  - `faq.md` / `faq.<lang>.md`
  - `troubleshooting.md` / `troubleshooting.<lang>.md`
  - `index.md` (root navigation)

---

### Phase 4: Adversarial Review & Autonomous Self-Healing (Auditor Subagent)

1. Launch the **Auditor Subagent**:
   - Compares English and Chinese docs side-by-side to guarantee 100% code block and parameter parity.
   - Verifies all referenced paths, commands, and keys against the actual codebase.
   - Scans for broken links and AI clichés ("不是……而是……", "收敛", redundant colons).
2. **Autonomous Self-Healing**:
   - The Auditor directly edits and fixes Markdown files in place if discrepancies are detected.

---

### Phase 5: Offline Static Site Compilation (Mechanical Tooling)

Compile the Markdown docs into a standalone, zero-dependency, responsive offline website:
```bash
python <makewiki_root>/scripts/run_toolkit.py build-site <output_dir> --theme auto
```
This generates `<output_dir>/site/index.html` with:
- Multilingual dropdown switcher
- Light / Dark theme toggle
- Search bar with instant client-side keyword indexing
- 1-click code copy buttons

---

### Phase 6: Ephemeral Cleanup & Final Report

1. Clean up temporary scratch logs or debug artifacts.
2. Present a concise completion report to the user:
   - Project Tier & Subagents deployed
   - Generated pages per language
   - Verification status
   - Direct link to `makewiki/site/index.html`
