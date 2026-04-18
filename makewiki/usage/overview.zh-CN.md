# 使用概览

MakeWiki.skills 提供五个斜杠命令，在 Claude Code 或 Codex 对话中运行。这些命令覆盖文档生成的完整生命周期：从扫描项目到验证最终输出。

## 可用命令

| 命令                   | 用途                           |
| -------------------- | ---------------------------- |
| `/makewiki`          | 运行完整流程：扫描、生成、复核、验证           |
| `/makewiki-scan`     | 扫描项目并显示收集到的证据                |
| `/makewiki-review`   | 比较各语言版本的事实一致性                |
| `/makewiki-validate` | 检查生成输出的质量问题                  |
| `/makewiki-init`     | 创建默认的 `makewiki.config.yaml` |

## 功能区域

### 文档生成

运行 `/makewiki` 为你的项目生成完整的多语言 wiki。这是主要命令，自动执行所有流水线阶段。

- 扫描项目中的命令、配置项、文件路径和版本信息
- 构建面向用户的功能语义模型
- 为每种请求的语言生成文档页面
- 执行跨语言复核和代码库验证
- 输出写入 `<项目>/makewiki/`

详见[文档生成](doc-generation.zh-CN.md)。

### 项目检查与验证

使用 `/makewiki-scan`、`/makewiki-review`、`/makewiki-validate` 和 `/makewiki-init` 来检查、验证和配置文档，无需运行完整的生成流水线。

- 预览 MakeWiki 能从你的项目中提取哪些证据
- 检查已有文档的跨语言不一致
- 验证输出质量（标题、链接、空页面）
- 生成配置文件以自定义行为

详见[项目检查与验证](project-inspection.zh-CN.md)。

## 常见工作流程

典型的使用流程如下：

1. 运行 `/makewiki-scan` 预览 MakeWiki 在你的项目中看到了什么
2. 运行 `/makewiki-init` 创建配置文件（如果需要自定义设置）
3. 运行 `/makewiki` 生成完整文档
4. 运行 `/makewiki-review` 检查跨语言一致性
5. 运行 `/makewiki-validate ./makewiki` 检查质量问题

## 相关文档

- [配置](../configuration.zh-CN.md)——所有配置选项详解
- [常见问题](../faq.zh-CN.md)——常见疑问
- [故障排除](../troubleshooting.zh-CN.md)——错误消息与修复方法