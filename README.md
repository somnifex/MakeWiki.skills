# MakeWiki.skills

在 Claude Code 或 Codex 中输入 `/makewiki`，就能为项目生成多语言用户文档。

[English](README.en.md) | **简体中文**

## 它能做什么

MakeWiki.skills 会先扫描仓库里的代码、配置和脚本，再整理出安装、配置、日常使用、FAQ 和排障文档。每种语言都基于同一份项目证据独立写作，不走“先写一种语言再翻译”的流程。

## 使用方式

### Claude Code

先加载插件：

```bash
claude --plugin-dir /path/to/MakeWiki.skills
```

然后在项目对话里调用：

```text
/makewiki --lang en --lang zh-CN    # 完整流程：扫描 → 生成 → 复核 → 验证
/makewiki-scan                      # 只看项目里能提取到哪些信息
/makewiki-review --lang en --lang zh-CN
/makewiki-validate ./makewiki
/makewiki-init
```

### 安装

需要 Python 3.11+，可使用 `uv` 或 `pip`：

```bash
git clone https://github.com/somnifex/MakeWiki.skills.git
cd MakeWiki.skills
uv sync          # 或 pip install -e .
```

## 原则

- 每种语言独立生成，不做翻译。
- 文档内容必须有项目证据支撑；证据不足时保持谨慎，不把推测写成事实。
- 不同语言里的代码块保持一致，只调整说明文字。

## 输出

默认输出到 `<项目>/makewiki/`：

```
makewiki/
  index.md
  README.md / README.zh-CN.md
  getting-started.md / getting-started.zh-CN.md
  installation.md / installation.zh-CN.md
  configuration.md / configuration.zh-CN.md
  usage/basic-usage.md / usage/basic-usage.zh-CN.md
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
review:
  enable_cross_language_review: true
  enable_code_grounding_verification: true
```

## 内置语言

English、简体中文、日本語、Deutsch、Français。需要更多语言时，可在 `src/makewiki_skills/languages/profiles/` 下添加。

## 工作流程

扫描项目 → 收集证据 → 构建语义模型 → 生成文档 → 跨语言复核 → 验证输出。

## 不负责的内容

不翻译现有文案，不生成 API 参考，不写架构分析，不修改源码，不执行危险命令，也不把猜测包装成事实。

## 致谢

感谢 [GitHub](https://github.com/)、[Reddit](https://www.reddit.com/) 和 [Linux.do](https://linux.do/) 社区长期公开分享的问题讨论、排障记录和经验总结。这些资料让 MakeWiki.skills 受益很多。

## 测试

```bash
uv sync && uv run pytest
```

## 许可证

MIT License © 2026 HowieWood
