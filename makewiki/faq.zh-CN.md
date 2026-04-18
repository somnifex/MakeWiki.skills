# 常见问题

## 需要哪个 Python 版本？

MakeWiki.skills 需要 Python 3.11 或更高版本。这个限制来自 `pyproject.toml` 中的 `requires-python = ">=3.11"`。

## 如何确认安装成功？

运行测试套件：

```bash
uv run pytest
```

所有测试应当通过。如果有失败，检查是否使用了 Python 3.11+ 以及 `uv sync`（或 `pip install -e .`）是否正常完成。

## 在哪里修改用户配置？

在目标项目的根目录放置 `makewiki.config.yaml` 文件。你可以在 Claude Code 对话中运行 `/makewiki-init` 来生成带有默认值的配置文件。详见[配置](configuration.zh-CN.md)。

## 支持哪些语言？

内置五种语言：English（`en`）、简体中文（`zh-CN`）、日本語（`ja`）、Deutsch（`de`）、Français（`fr`）。你可以在 `src/makewiki_skills/languages/profiles/` 下参照已有配置文件添加新语言。

## MakeWiki 会从一种语言翻译到另一种吗？

不会。每种语言版本基于同一份项目证据独立编写。代码块在所有语言中保持一致，但说明文字是为每种语言单独生成的，避免翻译痕迹，确保每个版本读起来自然。

## 如果 MakeWiki 没有检测到我的项目类型怎么办？

MakeWiki 使用文件指标检测项目类型（如 Python 的 `pyproject.toml`、Node.js 的 `package.json`、Rust 的 `Cargo.toml`、Go 的 `go.mod`）。如果都不匹配，退回到 `generic` 类型，置信度较低。你可以运行 `/makewiki-scan` 查看检测结果，再据此调整项目文件。

## 可以只生成一种语言吗？

可以：

```text
/makewiki --lang en
```

这只生成英文文档。只请求一种语言时，跨语言复核阶段会被跳过。

## "严格证据验证"是什么意思？

当 `strict_grounding: true`（默认）时，生成文档中提到的每条命令、配置项和文件路径都必须能追溯到项目证据。无法验证的声明被标记为违规。设为 `false` 后，这类声明降级为警告。

## 重新运行 `/makewiki` 时已有文件会怎样？

默认（`overwrite: true`）会覆盖输出目录中的已有文件。未在本次运行中生成的文件会保留，除非设置了 `delete_stale_files: true`。

## 有平台特定的步骤吗？

本仓库的一些开发命令使用了 Unix shell 语法。在 Windows 上，如果遇到 shell 命令问题，请使用 WSL 或 Git Bash。
