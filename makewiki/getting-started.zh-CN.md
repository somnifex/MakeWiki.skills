# 快速开始

本指南帮助你从零开始配置 MakeWiki.skills 并生成第一份 wiki 文档。

> 本指南只聚焦用户实际能看到和操作的内容，不展开内部架构。

## MakeWiki.skills 是什么？

MakeWiki.skills 是一组 Claude Code 和 Codex 的技能（斜杠命令）。在项目对话中运行 `/makewiki`，它会扫描项目并按你请求的语言生成用户文档。每种语言版本基于同一份项目证据独立编写，不走翻译流程。

## 前置条件

- **Python** >= 3.11
- **Claude Code** 或 **Codex**（技能以斜杠命令形式调用）
- **uv**（推荐）或 **pip** 用于依赖管理

## 安装

```bash
git clone https://github.com/somnifex/MakeWiki.skills.git
cd MakeWiki.skills
uv sync
```

也可以用 pip：

```bash
pip install -e .
```

## 加载插件

```bash
claude --plugin-dir /path/to/MakeWiki.skills
```

将 `/path/to/MakeWiki.skills` 替换为你克隆的仓库路径。

## 生成第一份 wiki

在任意项目目录打开 Claude Code 对话，然后运行：

```text
/makewiki
```

默认会生成英文和简体中文文档。命令完成后，项目根目录下会出现 `makewiki/` 目录，包含：

```
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
  usage/basic-usage.md
  usage/basic-usage.zh-CN.md
  faq.md
  faq.zh-CN.md
  troubleshooting.md
  troubleshooting.zh-CN.md
```

## 检查输出

确认生成的文件是否正确：

1. 打开 `makewiki/index.md`——列出所有生成的页面及链接
2. 打开 `makewiki/README.md`——应当基于代码库证据描述你的项目
3. 对比 `makewiki/README.md` 和 `makewiki/README.zh-CN.md`——代码块应完全一致，只有说明文字不同

## 下一步

- [配置 MakeWiki](configuration.zh-CN.md)，自定义语言、输出目录和扫描行为
- [生成文档](usage/doc-generation.zh-CN.md)，了解具体的语言和输出选项
- [检查与验证](usage/project-inspection.zh-CN.md)，查看项目证据和输出质量