# MakeWiki.skills

在 Claude Code 或 Codex 里输入 `/makewiki`，即可为项目生成多语言用户文档。

**简体中文** | [English](README.en.md)

## 它现在怎么工作

MakeWiki.skills 现在采用 artifact-first 架构：

- Python 先把仓库扫描成客观证据和可续跑的 run state
- LLM 再负责语义理解：模块划分、workflow 归纳、页面规划、页面写作
- 每种语言都基于同一批证据独立生成，不走“先写英文再翻译”的流程

`/makewiki` 是主编排器。主对话只读取 `state.json`、`semantic-model.index.json` 和短回执，不回读模块简报、trace 或页面正文。

## 使用方式

### Claude Code

先加载插件：

```bash
claude --plugin-dir /path/to/MakeWiki.skills
```

然后在项目对话中使用：

```text
/makewiki --lang en --lang zh-CN
/makewiki-scan
/makewiki-review --lang en --lang zh-CN
/makewiki-validate ./makewiki
/makewiki-init
```

`/makewiki` 的内部流程现在是：

1. `prepare`：生成 objective evidence 和 run state
2. `status` 循环：逐个执行 `surface-card`、`semantic-root`、`module-brief`、`workflow-brief`、`page-plan`、`page-write`、`page-repair`
3. `assemble`：把页面 artifact 组装到 `<project>/makewiki/`
4. `verify` / `review` / `validate`

## 安装

需要 Python 3.11+。推荐使用 `uv`：

```bash
git clone https://github.com/somnifex/MakeWiki.skills.git
cd MakeWiki.skills
uv sync
```

## 原则

- 每种语言独立生成，不做翻译
- Python 只负责客观证据、artifact/state、组装和机械校验
- 语义理解和页面写作交给 LLM child skills
- 如果 Python 扫描失败，可回退到 LLM 直接扫描仓库并写入 evidence artifacts
- 证据不足时要明确保留不确定性
- 不同语言里的代码块必须保持一致
- 主对话只看索引和短回执，不看模块简报正文

## 默认输出

默认输出到 `<project>/makewiki/`：

```text
makewiki/
  index.md
  README.md / README.zh-CN.md
  getting-started.md / getting-started.zh-CN.md
  installation.md / installation.zh-CN.md
  configuration.md / configuration.zh-CN.md
  commands.md / commands.zh-CN.md
  modules/overview.md / modules/overview.zh-CN.md
  modules/<module>.md / modules/<module>.zh-CN.md
  workflows/overview.md / workflows/overview.zh-CN.md
  workflows/<workflow>.md / workflows/<workflow>.zh-CN.md
  integrations/overview.md / integrations/overview.zh-CN.md
  faq.md / faq.zh-CN.md
  troubleshooting.md / troubleshooting.zh-CN.md
```

## 配置

在目标项目根目录放置 `makewiki.config.yaml`，或用 `/makewiki-init` 生成默认配置：

```yaml
output_dir: makewiki
languages: [en, zh-CN]
default_language: en
overwrite: true
strict_grounding: true
scan:
  ignore_dirs: [node_modules, dist, build, .git, .makewiki]
  max_depth: 6
  python_ast_config_tracking: true
  grep_fallback_for_config: true
  allow_llm_fallback_on_failure: true
semantic_reasoning:
  mode: llm-first
  module_index_threshold: 30
  index_only_in_main_conversation: true
orchestration:
  state_dir: .makewiki
  resume: true
  max_attempts: 2
render:
  annotate_low_confidence_footnotes: true
review:
  enable_cross_language_review: true
  enable_code_grounding_verification: true
```

## 内部工具链

`scripts/run_toolkit.py` 只给 skills 使用。当前核心内部命令包括：

```bash
python scripts/run_toolkit.py prepare . --format json --no-write-run
python scripts/run_toolkit.py status . --format json --no-write-state
python scripts/run_toolkit.py assemble . --lang en --lang zh-CN --format json --no-write-output
python scripts/run_toolkit.py verify .
python scripts/run_toolkit.py review . --lang en --lang zh-CN
python scripts/run_toolkit.py validate ./makewiki
```

在 Claude Code 里，推荐让 toolkit 负责计算内容与状态，但用内置 `Write` / `Edit` 工具真正写入 `state.json`、`evidence.index.json`、`evidence/shards/*.json`、`makewiki.config.yaml` 和最终 `makewiki/` 页面，这样能显著减少由 `python` / `uv` 落盘带来的授权弹窗。

## 内置语言

English、简体中文、日本語、Deutsch、Français。需要更多语言时，可在 `src/makewiki_skills/languages/profiles/` 下继续添加。

## 不负责的内容

不翻译已有文档，不在证据很薄的时候硬写 API 参考，不默认输出架构分析，不修改用户项目源码，也不把猜测包装成事实。

## 测试

```bash
uv sync
uv run pytest
```

## 许可证

MIT License © 2026 HowieWood
