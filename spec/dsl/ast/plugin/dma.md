# dma.md

## 功能简介

- 注册 `kernel_gen.operation.dma` 公开 helper 到 AST builtin registry。
- DMA helper 的 target-first/source-first 参数口径由 `nodes/dma.md` 与 parser 共同约束。
- 注册项 builder 负责构造对应 DMA AST 节点，并承接 DMA helper 前端合同校验。

## API 列表

本文件不承载公开 API。

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/ast/plugin/dma.md`](../../../../spec/dsl/ast/plugin/dma.md)
- `功能实现`：[`kernel_gen/dsl/ast/plugin/dma.py`](../../../../kernel_gen/dsl/ast/plugin/dma.py)
- `test`：[`test/dsl/ast/plugin/test_dma.py`](../../../../test/dsl/ast/plugin/test_dma.py)

## 依赖

- [`spec/dsl/ast/plugin/registry.md`](../../../../spec/dsl/ast/plugin/registry.md)
- [`spec/dsl/ast/nodes/dma.md`](../../../../spec/dsl/ast/nodes/dma.md)

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本文件只承载内部注册副作用；未列入上层公开 API 的 builder、注册函数或 helper 不得跨文件直接调用。
- `store`、`deslice` 的字段顺序必须保持 target-first。
- `load`、`slice` 的 builder 保持公开 operation helper 的 source-first 参数面，并构造对应具体 AST 节点；emit 阶段内部生成 target alloc。
- `view` 必须保持 source-first。

## API详细说明

本文件没有公开 API 详细条目；内部注册、目录组织与非公开 helper 边界见“额外补充”。

## 测试

- 测试文件：`test/dsl/ast/plugin/test_dma.py`
- 执行命令：`pytest -q test/dsl/ast/plugin/test_dma.py`

### 测试目标

- DMA helper call 被注册表识别，并由 DMA plugin builder 构造对应节点。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-PLUGIN-DMA-001 | 解析/打印 | DMA fill parses to specific node | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_dma_fill_parses_to_specific_node`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_dma_fill_parses_to_specific_node` |
| TC-DSL-AST-PLUGIN-DMA-002 | 解析/打印 | DMA load slice parse to specific nodes | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_dma_load_slice_parse_to_specific_nodes`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_dma_load_slice_parse_to_specific_nodes` |
| TC-DSL-AST-PLUGIN-DMA-003 | 解析/打印 | DMA store deslice parse to specific nodes | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_dma_store_deslice_parse_to_specific_nodes`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_dma_store_deslice_parse_to_specific_nodes` |
| TC-DSL-AST-PLUGIN-DMA-004 | 公开入口 | DMA public helpers parse parameterized return nodes | 通过固定 seed 的参数化顺序覆盖 alloc/copy/cast/view/reshape/flatten/load/slice 返回型 helper。 | 运行 `test_dma_public_helpers_parse_parameterized_return_nodes`。 | 返回型 DMA helper 均解析为对应公开 AST 节点。 | `test_dma_public_helpers_parse_parameterized_return_nodes` |
| TC-DSL-AST-PLUGIN-DMA-005 | 公开入口 | DMA public statement helpers parse parameterized nodes | 准备 free/store/deslice 语句型公开调用。 | 运行 `test_dma_public_statement_helpers_parse_parameterized_nodes`。 | 语句型 DMA helper 均解析为对应公开 AST 节点。 | `test_dma_public_statement_helpers_parse_parameterized_nodes` |
| TC-DSL-AST-PLUGIN-DMA-006 | 边界/异常 | DMA public helpers reject invalid contracts | 准备固定 seed 的 alloc/copy/cast/fill/load/slice/store/deslice arity、dtype、space、target/source 非法参数矩阵。 | 运行 `test_dma_public_helpers_reject_invalid_contracts`。 | 参数错误按公开 KernelCodeError 文案被拒绝，且不同 helper 的错误边界互不串线。 | `test_dma_public_helpers_reject_invalid_contracts` |
