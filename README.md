# MakeWiki.skills

在 Claude Code 或 Codex 的对话里输入 `/makewiki`，为你的项目生成多语言用户文档。

[English](README.en.md) | **简体中文**

## 做什么用

给任何软件项目写用户文档——安装、配置、日常操作、常见问题，每种语言独立生成而非翻译。文档里的每条结论都能追溯到项目本身的代码、配置或脚本。

## 怎么用

### Claude Code

加载插件后直接调用：

```bash
claude --plugin-dir /path/to/MakeWiki.skills
```

```
/makewiki --lang en --lang zh-CN    # 完整流程：扫描→生成→校验→验证
/makewiki-scan                       # 只扫描，看看项目里能检测到什么
/makewiki-review --lang en --lang zh-CN  # 跨语言一致性检查
/makewiki-validate ./makewiki        # 验证已有文档的质量
/makewiki-init                       # 生成默认配置文件
```

### 安装

Python 3.11+，用 `uv` 或 `pip`：

```bash
git clone https://github.com/somnifex/MakeWiki.skills.git
cd MakeWiki.skills
uv sync          # 或 pip install -e .
```

## 原则

- 每种语言从项目理解独立生成，不做翻译。
- 事实要有项目证据；证据不足就明确标注，不猜。
- 代码块跨语言一致，只有说明文字不同。

## 输出

默认写入 `<项目>/makewiki/`，按语言后缀区分文件：

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

在目标项目根目录放一份 `makewiki.config.yaml`，或用 `/makewiki-init` 生成默认版：

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

English、简体中文、日本語、Deutsch、Français。需要更多可在 `src/makewiki_skills/languages/profiles/` 下添加。

## 流水线

扫描项目 → 收集证据 → 构建语义模型 → 按语言生成 → 跨语言校验 → 证据溯源 → 写入并验证。

## 不做的事

不翻译、不生成 API 参考、不画架构图、不改源码、不执行危险命令、不把猜测写成事实。

## 致谢

MakeWiki.skills 也默默受益于 [GitHub](https://github.com/)、[Reddit](https://www.reddit.com/) 和 [Linux.do](https://linux.do/) 社区里持续分享的问题讨论、论坛帖子与排障记录。

## 测试

```bash
uv sync && uv run pytest
```

## 许可证

MIT License © 2026 HowieWood
