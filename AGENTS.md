# AGENTS.md

## 约定
- 未经特别授权，不得访问或修改 `.skills`、`.agents` 目录中的任何文件。
- 所有函数和文件都需补充完整的功能说明、使用示例，并提供对应的 `创建者` `最后修改人` `spec`、`test`、`功能实现` 文件链接。
- 示例链接：
- `spec`：[`spec/codex-multi-agents/scripts/codex-multi-agents-list.md`](spec/codex-multi-agents/scripts/codex-multi-agents-list.md)
- `test`：[`test/codex-multi-agents/test_codex-multi-agents-list.py`](test/codex-multi-agents/test_codex-multi-agents-list.py)
- `功能实现`：[`skills/codex-multi-agents/scripts/codex-multi-agents-list.sh`](skills/codex-multi-agents/scripts/codex-multi-agents-list.sh)

## 目录结构
  
## 项目说明
- 项目目标：`<待填写>`
- 生效范围：`<待填写>`

## 测试约定
- `test` 为测试目录。
- 测试统一使用 `pytest` 框架。
- 每个测试函数都需添加注释，至少包含以下信息：
  - 创建者
  - 最后一次更改
  - 最近一次运行测试时间。
  - 最近一次运行成功时间。
  - 对应功能实现文件路径。
  - 对应 `spec` 文件路径。
  - example：[`test/codex-multi-agents/test_codex-multi-agents-list.py`](test/codex-multi-agents/test_codex-multi-agents-list.py)

## [immutable]
- 不可更改带有[immutable]的代码段/文本段/注释等。也不能生成带有[immutable]的注释/代码。
- md 文件中带有 [immutable] 标题的段不可更改。



## 编码约定
- 目录约定：`<待填写>`
- 风格约定：`<待填写>`
- 测试约定：`<待填写>`

### spec文件规范
- 推荐结构：
  - `spec.md`
    - `功能简介`
      - 简要描述该 spec 对应的类、模块或方法的作用与职责。
    - `文档信息`
      - 创建者
      - 最后一次更改
      - `spec`：`<spec_file>`
      - `功能实现`：`<impl_file>`
      - `test`：`<test_file>`
    - `依赖`
      - 说明该 spec 直接依赖的文件、类型或模块，并附对应路径。
    - `目标`（可选）
      - 说明该模块对外提供的能力、使用方式和预期场景。
    - `限制与边界`（可选）
      - 说明实现必须满足的限制、与依赖的一致性要求，以及明确的不负责范围。
    - `公开接口`
      - 每个 API 建议至少包含：
        - 功能说明
        - 参数说明
        - 使用示例
        - 注意事项
        - 返回与限制
    - `测试`
      - 测试文件：`<test_file>`
      - 执行命令
      - 测试目标
      - 功能与用例清单

- 编写要求
  - 每个 spec 原则上只对应一个源文件；若存在例外，需要在文档中明确说明原因。
  - spec 文件应面向开发实现，不写历史迁移过程、重构过程或任务过程记录。
  - spec 中的接口说明、测试目标和示例，应与实际实现和测试保持一致。
  - 若 spec 中定义了测试清单，应与实际测试用例一一对应。
