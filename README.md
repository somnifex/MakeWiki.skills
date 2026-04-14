# MakeWiki.skills

MakeWiki.skills 用来给软件项目整理多语言的用户文档。它会先读项目里的配置、脚本和现有说明，再分别写出不同语言的版本，不走“先写一版、再整篇翻译”的路子。

[English](README.en.md) | **简体中文**

## 适合什么场景

这个项目主要有两种用法：

- 当作 CLI 用时，它适合放进本地脚本或 CI，按固定流程生成文档。
- 当作技能或插件用时，它可以和 AI 助手配合，把文档写得更自然一些，但写出来的内容还是要有项目里的依据。

归根结底，还是希望文档真的能拿来用：用户照着能操作，维护者也能看清这些说法的依据。

## 基本原则

- 每种语言单独生成，不是先写一版再整篇翻译。
- 文档里的事实要能在项目里找到依据。
- 证据不够时，就直接写清楚，不硬猜。
- 各语言里的代码块保持一致，主要变化的是说明文字。
- 默认输出目录是 `<目标项目>/makewiki/`。

## 内置语言

仓库内置了 English、简体中文、日本語、Deutsch 和 Français 五种语言配置。  
如果需要更多语言，可以在 `src/makewiki_skills/languages/profiles/` 下新增语言配置并注册。

## 安装

需要 Python 3.11+，并使用 `uv` 或 `pip` 安装。

```bash
git clone https://github.com/HowieWood/MakeWiki.skills.git
cd MakeWiki.skills
uv sync
```

如果你更习惯 `pip`：

```bash
pip install -e .
```

## 快速开始

为目标项目生成文档：

```bash
makewiki generate /path/to/project --lang en --lang zh-CN
```

常用命令还有：

```bash
makewiki scan /path/to/project
makewiki review /path/to/project --lang en --lang zh-CN
makewiki validate /path/to/project/makewiki
makewiki init-config /path/to/project
```

## 与 AI 助手配合使用

### Claude Code

把仓库作为插件加载后，可以直接使用这些斜杠命令：

```bash
claude --plugin-dir /path/to/MakeWiki.skills

/makewiki --lang en --lang zh-CN
/makewiki-scan
/makewiki-review --lang en --lang zh-CN
/makewiki-validate ./makewiki
/makewiki-init
```

### Codex 与其他助手

能读取 `AGENTS.md` 的助手可以直接在仓库根目录工作，并调用 CLI：

```bash
cd /path/to/MakeWiki.skills
uv sync
uv run makewiki generate /path/to/target --lang en --lang zh-CN
uv run makewiki scan /path/to/target
uv run makewiki review /path/to/target --lang en --lang zh-CN
uv run makewiki validate /path/to/target/makewiki
```

### CLI 模式和技能模式的区别

- CLI 模式更稳定、可预测，适合自动化、批处理和基础校验。
- 技能模式复用同一套证据与校验能力，但允许助手为每种语言写出更自然的说明文字。

## 输出结构

默认会在 `<目标项目>/makewiki/` 下生成这些文件：

```text
makewiki/
  index.md
  README.md
  README.zh-CN.md
  getting-started.md
  getting-started.zh-CN.md
  installation.md
  installation.zh-CN.md
  configuration.md
  configuration.zh-CN.md
  faq.md
  faq.zh-CN.md
  troubleshooting.md
  troubleshooting.zh-CN.md
  usage/
    basic-usage.md
    basic-usage.zh-CN.md
```

默认语言保留原始文件名，其他语言在文件名中追加类似 `.zh-CN` 的后缀。

## 配置示例

在目标项目根目录创建 `makewiki.config.yaml`：

```yaml
output_dir: makewiki
languages:
  - en
  - zh-CN
default_language: en
overwrite: true
generate_faq: true
generate_troubleshooting: true
strict_grounding: true
emit_uncertainty_notes: true
scan:
  ignore_dirs:
    - node_modules
    - dist
    - build
    - .git
  max_depth: 6
review:
  enable_cross_language_review: true
  enable_code_grounding_verification: true
  min_page_alignment_ratio: 0.9
```

也可以直接生成这份配置：

```bash
makewiki init-config /path/to/project
```

## 工作流程

1. 识别项目类型。
2. 从配置、脚本、README 和现有文档中收集证据。
3. 构建语言无关的语义模型。
4. 按语言分别渲染文档。
5. 对比各语言中的结构化事实。
6. 检查文档结论是否能被项目证据支撑。
7. 写入文件并校验 Markdown 输出。

## 仓库结构

```text
skills/                  AI 技能定义
src/makewiki_skills/     Python 工具层
  toolkit/               文件、配置、命令和 Markdown 工具
  scanner/               项目识别与证据采集
  model/                 语言无关的文档模型
  languages/             语言配置与注册表
  generator/             文档渲染
  review/                跨语言一致性检查
  verification/          证据溯源校验
  pipeline/              七阶段流水线
tests/                   自动化测试
examples/                示例项目
```

## 测试

```bash
uv sync && uv run pytest
```

## 边界

MakeWiki.skills 默认不会：

- 把单一语言版本直接翻译成其他语言
- 生成 API 参考文档
- 生成 UML 或架构图
- 修改目标项目源码
- 执行危险或任意项目命令
- 把猜测写成已经确认的事实

## 许可证

MIT License © 2026 HowieWood
