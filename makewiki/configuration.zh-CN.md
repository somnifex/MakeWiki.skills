# 配置

MakeWiki.skills 从目标项目根目录下的 `makewiki.config.yaml` 文件读取配置。如果没有该文件，使用默认值。

> 本页只整理运行时配置，不展开构建和打包元数据。

## 创建默认配置文件

在 Claude Code 对话中运行 `/makewiki-init` 生成带有默认值的 `makewiki.config.yaml`：

```text
/makewiki-init
```

也可以指定语言：

```text
/makewiki-init --lang en --lang zh-CN --lang ja
```

## 配置项参考

### 顶层选项

| 配置项                        | 默认值           | 说明                                           |
| -------------------------- | ------------- | -------------------------------------------- |
| `output_dir`               | `makewiki`    | 生成的 wiki 文件输出目录名（相对于项目根目录）                   |
| `languages`                | `[en, zh-CN]` | 要生成的语言代码。内置：`en`、`zh-CN`、`ja`、`de`、`fr`      |
| `default_language`         | `en`          | 默认语言不带文件后缀（如 `README.md` 而不是 `README.en.md`） |
| `overwrite`                | `true`        | 为 `true` 时，每次运行覆盖输出目录中已有的文件                  |
| `delete_stale_files`       | `false`       | 为 `true` 时，删除输出目录中未在本次运行生成的 `.md` 文件         |
| `generate_faq`             | `true`        | 为 `false` 时，跳过生成 FAQ 页面                      |
| `generate_troubleshooting` | `true`        | 为 `false` 时，跳过生成故障排除页面                       |
| `strict_grounding`         | `true`        | 为 `true` 时，缺乏项目证据支撑的内容视为违规；为 `false` 时降级为警告  |
| `emit_uncertainty_notes`   | `true`        | 为 `true` 时，在证据不足的页面添加提示说明                    |

### 扫描选项（`scan:`）

控制项目扫描方式。

| 配置项                                  | 默认值                                                                      | 说明                                             |
| ------------------------------------ | ------------------------------------------------------------------------ | ---------------------------------------------- |
| `scan.ignore_dirs`                   | `[node_modules, dist, build, .git, .makewiki, __pycache__, .venv, venv]` | 扫描时排除的目录                                       |
| `scan.max_depth`                     | `6`                                                                      | 文件扫描的最大目录深度                                    |
| `scan.max_file_size_kb`              | `512`                                                                    | 超过此大小（KB）的文件被跳过                                |
| `scan.enable_source_intelligence`    | `true`                                                                   | 为 `true` 时，扫描 Python 源码文件提取 CLI 帮助文本、错误消息和配置注释 |
| `scan.source_intelligence_max_files` | `50`                                                                     | 用于智能提取的最大源文件数量                                 |

### 复核选项（`review:`）

控制生成后的复核和验证阶段。

| 配置项                                         | 默认值    | 说明                          |
| ------------------------------------------- | ------ | --------------------------- |
| `review.enable_cross_language_review`       | `true` | 比较所有语言版本的结构化事实（命令、配置项、文件路径） |
| `review.enable_code_grounding_verification` | `true` | 检查生成文档中的声明是否存在于收集到的证据缓存中    |
| `review.enable_codebase_verification`       | `true` | 检查生成文档中的声明是否存在于实际项目文件系统中    |
| `review.enable_semantic_review`             | `true` | 准备对齐的段落用于语义层面的跨语言审核         |
| `review.min_page_alignment_ratio`           | `0.9`  | 所有语言都应具备的页面最低比例             |

### 内容深度选项（`content_depth:`）

控制生成内容的详细程度。

| 配置项                                       | 默认值    | 说明                                                                       |
| ----------------------------------------- | ------ | ------------------------------------------------------------------------ |
| `content_depth.mode`                      | `auto` | `auto` 根据项目复杂度自动判断。`detailed` 总是使用模块化文档和更高的内容上限。`compact` 使用单页用法说明和更低的上限 |
| `content_depth.max_faq_items`             | `20`   | FAQ 条目的最大数量                                                              |
| `content_depth.max_usage_examples`        | `8`    | 使用示例的最大数量                                                                |
| `content_depth.max_troubleshooting_items` | `8`    | 故障排除条目的最大数量                                                              |
| `content_depth.split_usage_threshold`     | `6`    | 当命令数超过此阈值时，将使用说明拆分为子页面                                                   |

## 配置示例

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

## 相关文档

- [文档生成](usage/doc-generation.zh-CN.md)——配置选项如何影响 `/makewiki` 命令
- [项目检查](usage/project-inspection.zh-CN.md)——扫描配置如何影响 `/makewiki-scan`