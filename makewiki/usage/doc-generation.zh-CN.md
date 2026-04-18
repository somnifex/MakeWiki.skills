# 文档生成

`/makewiki` 命令运行完整的文档流水线：扫描项目、为每种请求的语言生成页面、执行跨语言复核、对照代码库验证声明、以及检验输出质量。

## 基本用法

```text
/makewiki
```

默认生成英文和简体中文文档，输出到 `<项目>/makewiki/`。

## 指定语言

```text
/makewiki --lang en --lang zh-CN --lang ja
```

内置语言代码：`en`、`zh-CN`、`ja`、`de`、`fr`。

每种语言版本基于同一份项目证据独立编写。MakeWiki 不会从一种语言翻译到另一种——它为每种语言从头生成。

## 指定输出目录

```text
/makewiki --output docs-wiki
```

将输出写入 `<项目>/docs-wiki/` 而不是默认的 `makewiki/`。

## 流水线做了什么

运行 `/makewiki` 时，按顺序执行以下阶段：

1. **检测项目类型**——根据 `pyproject.toml`、`package.json`、`Cargo.toml` 或 `go.mod` 等文件识别项目是 Python、Node.js、Rust、Go 还是通用类型
2. **收集证据**——读取配置文件、文档、脚本和 Python 源码，提取命令、配置项、文件路径、版本号、CLI 帮助文本和错误消息
3. **构建语义模型**——将收集到的事实组织成结构化模型：项目身份、安装步骤、配置、命令、用户任务、FAQ 和故障排除条目
4. **生成文档**——使用语义模型为每种请求的语言渲染 Markdown 页面
5. **跨语言复核**——比较所有语言版本，查找缺失的命令、配置项或文件路径
6. **证据验证**——检查生成文档中的每条命令、配置项和路径是否存在于收集到的证据中
7. **代码库验证**——将同样的声明与实际项目文件系统进行对照
8. **输出与检验**——将文件写入磁盘，检查标题层级、链接完整性和页面内容

## 输出结构

成功运行后，输出目录结构如下（英文 + 中文）：

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

对于复杂项目（命令或配置项较多），`usage/` 部分可能拆分为多个子页面，而不是单一的 `basic-usage.md`。当 `content_depth.mode` 设为 `auto`（默认值）时会自动判断。

## 核心原则

- **证据支撑**：生成文档中的每条命令、配置项和路径都必须来自实际项目。没有证据的内容会被标记或加上谨慎措辞。
- **独立生成**：每种语言版本从头编写，不做翻译。代码块在所有语言中保持一致，只有说明文字不同。
- **不用营销语言**：生成的文档描述项目实际做了什么，不使用"强大"、"极速"等主观描述词。

## 影响生成的配置项

| 配置项                  | 作用                 |
| -------------------- | ------------------ |
| `output_dir`         | 输出文件写入的位置          |
| `languages`          | 生成哪些语言版本           |
| `default_language`   | 哪种语言使用不带后缀的文件名     |
| `overwrite`          | 是否覆盖已有文件           |
| `strict_grounding`   | 缺乏证据的声明是违规还是警告     |
| `content_depth.mode` | 是自动检测、强制详细还是强制紧凑输出 |

详见[配置](../configuration.zh-CN.md)。

## 使用示例

### 为 Python 项目生成文档

```text
/makewiki --lang en --lang zh-CN
```

预期输出：`makewiki/` 目录，包含基于 `pyproject.toml` 的安装步骤、来自 YAML/TOML 文件的配置文档、以及来自 README 代码块的使用示例。

### 生成日语文档

```text
/makewiki --lang en --lang ja
```

日语版本使用礼貌体技术文档风格（です/ます调），英文技术术语保留片假名或原文。

### 输出到自定义目录

```text
/makewiki --output wiki --lang en
```

将仅英文的文档写入 `<项目>/wiki/`。

## 相关文档

- [使用概览](overview.zh-CN.md)——所有可用命令一览
- [项目检查](project-inspection.zh-CN.md)——无需完整生成即可扫描、复核和验证
- [配置](../configuration.zh-CN.md)——所有配置选项