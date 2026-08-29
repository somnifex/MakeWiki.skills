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

## Execution Mode & Multi-Agent Topology

MakeWiki orchestrates specialized subagents with **dynamic budgeting** (capped at 10 subagents maximum) and **ReBattle competitive cross-examination** to eliminate single-agent bias and hallucinations.

```
                  ┌──────────────────────────────────────────────┐
                  │ Main Agent (Orchestrator & Chief Adjudicator)│
                  └──────────────────────┬───────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
  [Phase 1: Scout]            [Phase 2: ReBattle]             [Phase 3: Writers]
 ├─ Scout-Structure          ├─ Agent Red (User & Dev)        ├─ English Writer
 └─ Scout-Content            ├─ Agent Blue (Code & AST)       ├─ Chinese Writer
                             ├─ Agent Green (Deploy & Ops)    └─ (Other Lang Writers)
                             └─ [Judge + Code Verifier]
```

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

### Subagent Budgeting & Sizing Tiers

The Main Agent **automatically assesses project complexity** in Phase 0 without prompting the user:

| Project Tier | Sizing Criteria | Subagent Budget | ReBattle Protocol | Token Profile |
| :--- | :--- | :--- | :--- | :--- |
| **Tier S (Simple)** | Source files < 15, single entrypoint | **1 ~ 2 Subagents** | Prompt-based self-review (0 debate rounds) | ~15k-40k tokens |
| **Tier M (Medium)** | Source files 15~80, 5~15 commands | **3 ~ 5 Subagents** | Red vs Blue (1 debate round) | ~40k-80k tokens |
| **Tier L (Large)** | Source files > 80, Monorepo / Multi-module | **5 ~ 10 Subagents (Hard Cap)** | Red + Blue + Green (2 debate rounds) | ~80k-150k tokens |

---

## Part A: Documentation Standards (Enterprise Delivery + Diátaxis)

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

## Part B: Six-Phase Multi-Agent Workflow

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

If the script prints a path, refer to it as `<makewiki_root>`. If any launcher command fails later, continue in manual mode.

---

### Phase 0: Project Sizing & Subagent Budgeting (Autonomous)

1. Run the sizing probe or inspect directory file counts automatically:
   ```bash
   python <makewiki_root>/scripts/run_toolkit.py sizing .
   ```
2. Automatically select project tier (`Tier S`, `Tier M`, or `Tier L`) and allocate subagents accordingly. Do not ask user.

---

### Phase 1: Recon & Evidence Gathering (Scout Subagent)

For Tier M / L, launch **Scout Subagent(s)** autonomously:
- **Scout-Structure**: Scan directory tree, manifests (`pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`), Makefile, CI/CD workflows, Dockerfiles.
- **Scout-Content**: Read README, existing docs, `.env.example`, main entrypoints, and CLI help flags.

*Fallback / Tier S*: Run static scan via toolkit `python <makewiki_root>/scripts/run_toolkit.py scan . --format json` or direct `Glob`/`Read`.

---

### Phase 2: ReBattle Competitive Analysis & Cross-Examination

To eliminate hallucinations and single-agent omissions, deploy multi-perspective analysis:

#### 1. Independent Blind Extraction (Round 1)
- **Agent Red (User & Developer Experience)**: Extracts CLI commands, interactive workflows, quickstart tutorial paths, and expected outputs.
- **Agent Blue (Codebase & Implementation)**: Extracts actual AST functions, exports, handler signatures, default fallback values, and unreleased/stub code warnings.
- **Agent Green (Enterprise Deployment & Ops)**: Extracts OS/runtime compatibility, configuration matrix, environment variables, health checks, and error logs.

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
- Feed the Writer the **same adjudicated SemanticModel** and the language style guide.
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
