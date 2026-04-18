# 安装

## 前置条件

| 需求                  | 版本       | 说明                 |
| ------------------- | -------- | ------------------ |
| Python              | >= 3.11  | `uv` 和 `pip` 安装均需要 |
| Claude Code 或 Codex | 任意版本     | 技能以斜杠命令形式调用        |
| uv                  | 任意版本（推荐） | 没有 uv 时退回到 pip     |

## 用 uv 安装（推荐）

```bash
git clone https://github.com/somnifex/MakeWiki.skills.git
cd MakeWiki.skills
uv sync
```

## 用 pip 安装

```bash
git clone https://github.com/somnifex/MakeWiki.skills.git
cd MakeWiki.skills
pip install -e .
```

## 加载 Claude Code 插件

安装完成后，每次启动 Claude Code 时加载插件：

```bash
claude --plugin-dir /path/to/MakeWiki.skills
```

将 `/path/to/MakeWiki.skills` 替换为仓库的实际路径。

## 验证安装

运行测试套件确认一切正常：

```bash
uv run pytest
```

所有测试应当通过。如果有测试失败，检查是否使用了 Python 3.11 或更高版本，以及依赖是否安装完整。

## 平台说明

### Windows

本仓库的一些开发命令使用了 Unix shell 语法。如果遇到问题，请使用 WSL 或 Git Bash 代替默认的 Windows 命令提示符。

### macOS / Linux

无需额外步骤，按上述方法安装即可。
