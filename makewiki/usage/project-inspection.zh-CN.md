# 项目检查与验证

MakeWiki.skills 提供四个命令，用于检查项目、复核已有文档、验证输出质量和创建配置文件——无需运行完整的生成流水线。

## 扫描项目证据

```text
/makewiki-scan
```

扫描当前项目并显示收集到的所有证据摘要：检测到的项目类型、按类型统计的事实数量（命令、配置项、路径、版本）和置信度。

### 显示内容

扫描完成后，你会看到：

- **项目名称**和**检测到的类型**（如 `python-cli`、`node-react`）
- **检测置信度**百分比
- **发现的指标**（如 `pyproject.toml`、`src/`）
- **证据摘要表**：命令、配置项、路径、版本、描述等事实类型的数量
- **总事实数**

### 使用场景

- 在运行 `/makewiki` 之前，预览 MakeWiki 能从项目中提取哪些信息
- 识别证据缺口——例如，如果检测到的命令很少，说明 README 可能需要更多代码块
- 确认排除目录（`scan.ignore_dirs`）设置是否正确

### 影响扫描的配置项

| 配置项                                  | 作用                           |
| ------------------------------------ | ---------------------------- |
| `scan.ignore_dirs`                   | 扫描时排除的目录                     |
| `scan.max_depth`                     | 最大目录深度                       |
| `scan.max_file_size_kb`              | 读取的最大文件大小                    |
| `scan.enable_source_intelligence`    | 是否扫描 Python 源码提取 CLI 帮助和错误信息 |
| `scan.source_intelligence_max_files` | 用于智能提取的最大 Python 文件数         |

## 复核跨语言一致性

```text
/makewiki-review --lang en --lang zh-CN
```

比较各语言版本的生成文档，报告事实不一致。

### 检查内容

复核器从每种语言版本中提取结构化事实并比较：

- **命令**——代码块中的每条命令都必须出现在所有语言中（严重程度：严重）
- **配置项**——每个配置项引用都必须出现在所有语言中（严重程度：严重）
- **文件路径**——文件路径引用应跨语言匹配（严重程度：重要）
- **版本号**——版本号应当一致（严重程度：重要）
- **页面覆盖**——所有语言应有相同的页面集合（严重程度：重要）

### 显示内容

- **一致性评分**——各语言版本匹配程度的百分比
- **不一致表**——每个差异的类型、值、哪些语言有、哪些语言缺少、严重程度

### 使用场景

- 运行 `/makewiki` 后，在发布前验证输出
- 怀疑某种语言版本已更新但另一种没有时
- 作为文档质量检查清单的一部分

## 验证生成输出

```text
/makewiki-validate ./makewiki
```

检查生成的输出目录的 Markdown 质量问题。

### 检查内容

- **缺少 H1**——每个页面应以 H1 标题开头
- **标题层级**——不允许跳级（如从 H2 直接到 H4）
- **内部链接断裂**——生成页面间的链接必须指向实际存在的文件
- **空页面**——没有实质内容的页面会被标记
- **禁用描述词**——未经证据支持的营销用语（如"强大"、"无缝"）会被标记
- **禁用标题**——用户文档中出现的开发者导向标题（如"架构"、"项目结构"）会被标记

### 显示内容

- **文件数量**和有问题的文件数
- **错误**（必须修复）和**警告**（建议修复）
- **通过/失败**状态——存在错误时判定为失败

### 使用场景

- 运行 `/makewiki` 后作为最终质量检查
- 手动编辑生成文件后检查格式回归
- 作为文档质量 CI 流水线的一部分

## 创建默认配置

```text
/makewiki-init
```

在当前项目根目录生成带有默认设置的 `makewiki.config.yaml` 文件。

### 指定语言

```text
/makewiki-init --lang en --lang zh-CN --lang ja
```

### 创建内容

一个包含所有默认配置值的 YAML 文件，你可以按需修改：

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

### 使用场景

- 第一次运行 `/makewiki` 之前，如果想自定义行为
- 添加更多语言支持时
- 调整扫描或复核设置时

## 相关文档

- [使用概览](overview.zh-CN.md)——所有可用命令
- [文档生成](doc-generation.zh-CN.md)——完整的 `/makewiki` 流水线
- [配置](../configuration.zh-CN.md)——所有配置选项详解