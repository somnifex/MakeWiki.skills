# MakeWiki.skills

MakeWiki.skills 是一个 Claude Code / Codex 插件，用于为软件项目生成多语言用户文档。它扫描仓库中的命令、配置和脚本，然后按请求的语言分别生成 Markdown wiki 页面，并进行跨语言一致性检查和代码库验证。

## 适合谁使用？

- 希望从项目实际代码和配置文件自动生成用户文档的开发者
- 需要维护多语言文档并确保各版本内容一致的团队

## 工作方式

在 Claude Code 中加载 MakeWiki.skills 插件后，在项目对话中运行 `/makewiki`。插件会：

1. 扫描项目中的命令、配置项、文件路径和版本信息
2. 构建面向用户的功能语义模型
3. 为每种请求的语言独立生成文档页面（不是翻译）
4. 比较所有语言版本的事实一致性
5. 将生成的内容与实际项目代码库进行对照验证
6. 检验输出质量（标题、链接、页面完整性）

## 快速开始

```bash
git clone https://github.com/somnifex/MakeWiki.skills.git
cd MakeWiki.skills
uv sync
```

在 Claude Code 中加载插件：

```bash
claude --plugin-dir /path/to/MakeWiki.skills
```

然后在项目对话中运行：

```text
/makewiki --lang en --lang zh-CN
```

## 内置语言

English、简体中文、日本語、Deutsch、Français。

## 目录

- [快速开始](getting-started.zh-CN.md)
- [安装](installation.zh-CN.md)
- [配置](configuration.zh-CN.md)
- **使用说明**
  - [概览](usage/overview.zh-CN.md)
  - [文档生成](usage/doc-generation.zh-CN.md)
  - [项目检查与验证](usage/project-inspection.zh-CN.md)
- [常见问题](faq.zh-CN.md)
- [故障排除](troubleshooting.zh-CN.md)

## 文档导航

| 语言      | 链接                                 |
| ------- | ---------------------------------- |
| English | [README.md](README.md)             |
| 简体中文    | [README.zh-CN.md](README.zh-CN.md) |