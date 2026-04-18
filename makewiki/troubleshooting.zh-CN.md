# 故障排除

## `Error: Target directory does not exist`

**现象：** 运行 `/makewiki` 或其他 MakeWiki 命令时显示：

```
Error: Target directory does not exist: <path>
```

**原因：** 传给命令的路径不是有效目录。

**解决方法：** 确保你在 Claude Code 对话中打开了有效的项目目录。如果手动指定了路径，检查路径是否存在且为目录。

## `Language '<code>' not registered, skipping`

**现象：** 运行 `/makewiki` 后，一种或多种请求的语言被跳过并显示此警告。

**原因：** 请求的语言代码没有内置配置文件。内置代码为：`en`、`zh-CN`、`ja`、`de`、`fr`。

**解决方法：** 使用内置语言代码。如果需要未内置的语言，可以在 `src/makewiki_skills/languages/profiles/` 下参照已有文件创建新的语言配置。

## `Wiki directory not found`

**现象：** 运行 `/makewiki-review` 或 `/makewiki-validate` 时显示：

```
Error: Wiki directory not found: <path>
```

**原因：** 命令需要 `makewiki/` 目录（或 `output_dir` 指定的目录）已存在且包含生成的文档。

**解决方法：** 先运行 `/makewiki` 生成文档。如果已将文档生成到自定义目录，指定正确的路径：

```text
/makewiki-validate ./custom-output-dir
```

## 工具包引导时输出 `NOT_FOUND`

**现象：** 技能启动时打印 `NOT_FOUND` 并退回手动模式。

**原因：** 引导脚本无法在 `~/.makewiki` 下准备工具包环境，通常是权限错误或上次运行留下的锁定文件。

**解决方法：** 删除 `~/.makewiki` 目录后重新运行：

```bash
rm -rf ~/.makewiki
```

技能会在下次运行时重新创建工具包环境。如果问题持续，技能会继续以手动模式工作——文档生成仍然正常进行。

## `uv run pytest` 失败

**现象：** 全新安装后测试失败。

**原因：** 依赖可能未完全安装，或者 Python 版本低于 3.11。

**解决方法：**

1. 检查 Python 版本：`python --version`（必须是 3.11+）
2. 重新同步依赖：`uv sync`
3. 重新运行测试：`uv run pytest`

## 跨语言复核显示严重问题

**现象：** `/makewiki-review` 报告严重问题，一致性评分较低。

**原因：** 一种或多种语言版本缺少其他版本中出现的命令、配置项或文件路径。这可能发生在语言版本间的代码块不一致时。

**解决方法：** 重新运行 `/makewiki` 从相同证据重新生成所有语言版本。如果问题仍然存在，检查不一致表找到具体差异并修复相关页面。

## 验证报告链接断裂

**现象：** `/makewiki-validate` 报告内部链接断裂。

**原因：** 某个生成页面引用了输出目录中不存在的另一个页面——例如，链接到 `configuration.zh-CN.md` 但中文版未被生成。

**解决方法：** 确保链接中引用的所有语言都包含在生成中。用正确的 `--lang` 参数重新运行 `/makewiki`，或者手动修复链接。
