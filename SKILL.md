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

## 1. Multi-Agent Topology & Subagent Specifications

MakeWiki orchestrates specialized subagents with **dynamic budgeting** (capped at 10 subagents maximum) and **ReBattle competitive cross-examination** to eliminate single-agent bias and hallucinations.

```
                  ┌──────────────────────────────────────────────┐
                  │ Main Agent (Orchestrator & Chief Adjudicator)│
                  │ - Assesses Project Tier (S / M / L)          │
                  │ - Dispatches Subagents & Manages Budget      │
                  │ - Arbitrates ReBattle Conflicts              │
                  │ - Compiles Unified SemanticModel             │
                  └──────────────────────┬───────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
  [Phase 1: Scout]             [Phase 2: ReBattle]             [Phase 3: Writers]
 ├─ Scout-Structure           ├─ Agent Red (User & Dev)        ├─ English Writer
 └─ Scout-Surface             ├─ Agent Blue (Code & AST)       ├─ Chinese Writer
                              ├─ Agent Green (Deploy & Ops)    └─ (Other Lang Writers)
                              └─ [Mechanical Verifier]
                                         │
                                         ▼
                                [Phase 4: Reviewer]
                              ├─ Code Block Parity Auditor
                              ├─ Ground-Truth Verifier
                              └─ Anti-AI-Cliché & Link Auditor
```

---

### Subagent Role Definitions & Responsibility Matrix

| Subagent Role | Primary Focus | Allowed Tools | Input Contract | Output Contract |
| :--- | :--- | :--- | :--- | :--- |
| **`Scout-Structure`** | Repository layout, package manifests, build scripts, CI/CD, Dockerfiles | `Glob`, `Read`, `Grep` | Target root path | Project skeleton, dependencies, build targets, directory tree |
| **`Scout-Surface`** | Entrypoints, CLI flags, REST routes, `.env.example`, existing README | `Glob`, `Read`, `Grep`, CLI help probe | Target root path | CLI arguments, route paths, config keys, existing descriptions |
| **`Agent Red`** | User & Developer Experience (DX): tutorials, commands, expected outputs | `Read`, `Grep` | Scout facts + target root | `claims_red.json` (User-facing runnable commands & workflows) |
| **`Agent Blue`** | Code Implementation & AST: exported symbols, defaults, stubs, deprecations | `Read`, `Grep` | Scout facts + source code | `claims_blue.json` (Implementation ground truth & objection claims) |
| **`Agent Green`** | Deployment, Infrastructure & Ops: OS compatibility, env vars, error runbooks | `Read`, `Grep` | Scout facts + config files | `claims_green.json` (Ops runbook facts & configuration matrix) |
| **`Main Agent (Judge)`** | Chief Adjudicator & Orchestrator: arbitrates disputes, builds SemanticModel | All tools + Toolkit | Claims from Red, Blue, Green | Adjudicated **`SemanticModel`** (`semantic_model.json`) |
| **`Language Writer`** | Independent Diátaxis documentation author for a specific target language | `Write`, `Edit`, `Read` | Unified `SemanticModel` + Style Profile | Complete Markdown documentation set under `<output_dir>/` |
| **`Reviewer / Auditor`** | Cross-language parity, ground-truth verification, anti-AI-cliché audit | `Read`, `Edit`, Toolkit | Generated Markdown docs + Codebase | Verification report + in-place autonomous corrections |

---

### Subagent Prompt Templates (Dispatch Prompts)

When spawning subagents via `invoke_subagent` or delegation, use the following standardized prompt templates:

#### 1. Scout-Structure Prompt Template
```markdown
You are Scout-Structure for project '{project_name}'.
Your task is to scan the project repository and establish structural evidence:
1. Identify all package manifests (pyproject.toml, package.json, go.mod, Cargo.toml, pom.xml).
2. Scan build configurations (Makefile, CMakeLists.txt, Taskfile, Dockerfile, docker-compose.yml, CI workflows).
3. Map the top-level directory structure and module boundaries.
Output a structured summary of: project_type, dependencies, build commands, and verified file paths with line citations.
Do not guess or hallucinate any unobserved files.
```

#### 2. Scout-Surface Prompt Template
```markdown
You are Scout-Surface for project '{project_name}'.
Your task is to extract public interface evidence:
1. Scan main CLI entrypoints and extract help texts, flags, and parameter options.
2. Scan Web/API route definitions and extract HTTP methods and endpoint paths.
3. Read .env.example, config templates, and existing READMEs for declared configuration keys.
Output a list of verified commands, parameters, and environment variables with their source file and line numbers.
```

#### 3. Agent Red (User & DX Perspective) Prompt Template
```markdown
You are Agent Red (Developer & User Experience).
Analyze the project from the perspective of an external developer or end-user:
1. What is the 5-minute quickstart onboarding workflow from git clone to first run?
2. What are the primary CLI commands, required flags, and expected terminal outputs?
3. What are the common daily usage scenarios?
Extract factual claims strictly grounded in repository evidence. Label each claim with confidence: high, medium, or inferred.
```

#### 4. Agent Blue (Code AST & Ground-Truth) Prompt Template
```markdown
You are Agent Blue (Code Implementation & AST Verifier).
Analyze the source code to verify factual accuracy and catch non-existent features:
1. Verify whether commands and flags proposed by Agent Red actually exist in argument parsers or route tables.
2. Check default values, type constraints, and fallback logic directly in source code.
3. Identify unreleased features, stub functions, or deprecated parameters.
Output verified implementation facts and explicit objection challenges against any ungrounded user-facing claims.
```

#### 5. Agent Green (Enterprise Deployment & Ops) Prompt Template
```markdown
You are Agent Green (Enterprise Delivery & Operations).
Analyze the project for deployment and production reliability:
1. Compatibility matrix: Supported OS, runtime versions (e.g. Node 18+, Python 3.11+, Go 1.22+), database dependencies.
2. Configuration matrix: Environment variables, config files, required vs optional settings, default values, production recommendations.
3. Incident runbook: Error messages found in source code, root causes, log locations, and troubleshooting resolution steps.
Output deployment runbook facts and operational failure recovery steps.
```

#### 6. Language Writer Subagent Prompt Template
```markdown
You are the {language_name} Documentation Writer for project '{project_name}'.
Write the complete documentation suite in {language_name} using the unified SemanticModel provided.
Requirements:
1. Independent generation: Write native, high-quality technical {language_name} directly from the SemanticModel — NEVER translate from another language output.
2. Code block parity: All command code blocks, configuration keys, and parameter flags must remain 100% identical across all language versions.
3. Diátaxis structure: Write README.md, getting-started.md, installation.md, configuration.md, usage/*.md, faq.md, troubleshooting.md, and index.md.
4. Strict Anti-AI-Cliché rules:
   - BAN binary antitheses ("不是……而是……", "不仅……而且……").
   - BAN buzzwords ("收敛", "赋能", "对齐").
   - BAN redundant colons in headings and list items.
   - Write clear, concise, engineer-to-engineer prose.
Save all generated files under '{output_dir}/'.
```

#### 7. Reviewer & Quality Auditor Subagent Prompt Template
```markdown
You are the Quality Auditor and Reviewer for the generated documentation in '{output_dir}/'.
Perform an autonomous audit and self-healing pass:
1. Run codebase grounding verification to confirm all mentioned commands, config keys, and file paths exist.
2. Run cross-language consistency review: ensure every code block and parameter in English matches Chinese and all other languages 1:1.
3. Scan for broken Markdown links and AI clichés.
4. Autonomous Self-Healing: If minor discrepancies, typos, or missing commands are found, edit and correct the Markdown files in-place immediately without asking the user.
```

---

### Autonomous Zero-Intervention Principle (全自主无人值守原则)

This skill is designed for **end-to-end autonomous execution without interrupting the user**:
1. **No Intermediate Blocking Prompts**:
   - Do **NOT** ask the user intermediate questions (e.g. do NOT ask *"Which scan mode do you want?"*, *"Do you approve this outline?"*, *"Should I continue?"*).
   - Automatically determine project sizing (Tier S/M/L), scan depth, and documentation layout from codebase evidence.
2. **Deterministic Auto-Defaults**:
   - If languages are not specified, default to `en` and `zh-CN` (or read from `makewiki.config.yaml`).
   - If output directory is not specified, default to `makewiki`.
   - If theme is not specified, default to `auto`.
3. **Autonomous Self-Healing & In-Place Correction**:
   - If a command/path verification fails $\rightarrow$ automatically correct or remove it in-place without human intervention.
   - If a toolkit command fails $\rightarrow$ automatically fallback to agent tools (`Glob`, `Read`, `Grep`) and proceed smoothly.
   - If cross-language drift is detected $\rightarrow$ automatically synchronize code blocks and facts across all versions.

---

### Subagent Budgeting & Sizing Tiers

The Main Agent **automatically assesses project complexity** in Phase 0 without prompting the user:

| Project Tier | Sizing Criteria | Subagent Budget | ReBattle Protocol | Subagent Allocation |
| :--- | :--- | :--- | :--- | :--- |
| **Tier S (Simple)** | Source files < 15, single entrypoint | **1 ~ 2 Subagents** | Prompt-based self-review (0 debate rounds) | Main Agent (Scout + Judge) + 1~2 Parallel Writers |
| **Tier M (Medium)** | Source files 15~80, 5~15 commands | **3 ~ 5 Subagents** | Red vs Blue (1 debate round) | 1 Scout + 2 ReBattle (Red, Blue) + 2 Writers |
| **Tier L (Large)** | Source files > 80, Monorepo / Multi-module | **5 ~ 10 Subagents (Hard Cap)** | Red + Blue + Green (2 debate rounds) | 2 Scouts + 3 ReBattle + Parallel Writers + 1 Reviewer |

---

## 2. Documentation Standards (Enterprise Delivery + Diátaxis)

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

## 3. Six-Phase Multi-Agent Execution Workflow

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

If the script prints a path, refer to it as `<makewiki_root>`. If any launcher command fails later, continue in manual agent mode.

---

### Phase 0: Project Sizing & Subagent Budgeting (Autonomous)

1. Run the sizing probe automatically:
   ```bash
   python <makewiki_root>/scripts/run_toolkit.py sizing .
   ```
2. Automatically select project tier (`Tier S`, `Tier M`, or `Tier L`) and allocate subagents according to the sizing table.

---

### Phase 1: Recon & Evidence Gathering (Scout Subagents)

For Tier M / L, launch **Scout Subagents** with their prompt templates:
- **`Scout-Structure`**: Scans package manifests (`pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`), Makefile, CI/CD workflows, Dockerfiles.
- **`Scout-Surface`**: Scans README, entrypoints, CLI help flags, REST route decorators, and `.env.example`.

*Fallback / Tier S*: Run static scan via toolkit `python <makewiki_root>/scripts/run_toolkit.py scan . --format json` or direct `Glob`/`Read`.

---

### Phase 2: ReBattle Competitive Analysis & Adjudication

To eliminate hallucinations and single-agent omissions, deploy multi-perspective analysis:

#### 1. Independent Blind Extraction (Round 1)
- **Agent Red (User & DX)**: Extracts CLI commands, interactive workflows, quickstart tutorial paths, and expected outputs.
- **Agent Blue (Code AST & Ground Truth)**: Extracts actual AST functions, exports, handler signatures, default fallback values, and unreleased/stub code warnings.
- **Agent Green (Enterprise Ops)**: Extracts OS/runtime compatibility, configuration matrix, environment variables, health checks, and error logs.

#### 2. Cross-Examination & Challenge (Round 2)
The Main Agent exchanges Claims among the agents:
- Agent Blue challenges Agent Red: *"Command `--fast` does not exist in cli.py parser; flag is invalid."*
- Agent Green challenges Agent Red: *"Quickstart tutorial omits mandatory `DB_PORT` environment variable."*
- Agent Red challenges Agent Blue: *"Function `export_csv` is exposed via CLI even though marked internal."*

#### 3. Adjudication & Unified Semantic Model (Round 3)
The Main Agent acts as **Judge**:
- Runs `python <makewiki_root>/scripts/run_toolkit.py verify . --format json` to mechanically verify disputed paths, commands, and keys.
- Resolves conflicts, rejects ungrounded claims, hedges uncertain capabilities, and compiles the authoritative **`SemanticModel`**.

---

### Phase 3: Parallel Multilingual Writers

For each requested language (`en`, `zh-CN`, `ja`, etc.):
- Spawn an independent **Language Writer Subagent** (or sequential in Tier S).
- Feed the Writer the **same adjudicated SemanticModel** and language prompt template.
- Each Writer writes the full Markdown document set into `<output_dir>/`:
  - `README.md` / `README.<lang>.md`
  - `getting-started.md` / `getting-started.<lang>.md`
  - `installation.md` / `installation.<lang>.md`
  - `configuration.md` / `configuration.<lang>.md`
  - `usage/overview.md`, `usage/<slug>.md`
  - `faq.md` / `faq.<lang>.md`
  - `troubleshooting.md` / `troubleshooting.<lang>.md`
  - `index.md` (root navigation)

---

### Phase 4: Adversarial Review & Codebase Verification (Auto-Correction)

1. **Mechanical Ground-Truth Check**:
   ```bash
   python <makewiki_root>/scripts/run_toolkit.py verify . --format json
   ```
2. **Cross-Language Consistency Check**:
   ```bash
   python <makewiki_root>/scripts/run_toolkit.py review . --lang en --lang zh-CN
   ```
3. **Review Subagent Pass**:
   - Verify code blocks and command syntax match 100% across all languages.
   - Automatically correct or remove any invalid keys, commands, or paths in-place.
   - Ensure text is strictly free of AI clichés ("不是而是", "这是", "收敛", redundant colons).

---

### Phase 5: Offline Static Site Compilation

Compile the Markdown docs into a standalone, zero-dependency, responsive offline website:
```bash
python <makewiki_root>/scripts/run_toolkit.py build-site <output_dir> --theme auto
```
This generates `<output_dir>/site/index.html`, which users can directly double-click to open in any web browser with:
- Multilingual dropdown switcher
- Light / Dark theme toggle
- Search bar with instant client-side keyword indexing
- Code syntax display with 1-click copy button

---

### Phase 6: Ephemeral Cleanup & Final Report

1. Automatically clean up any temporary debug logs, AST caches, or scratch files.
2. Present a single concise completion report to the user:
   - Project Tier & Subagent count utilized
   - Total documents generated per language
   - Verification status
   - Direct link to the compiled static site (`makewiki/site/index.html`)
