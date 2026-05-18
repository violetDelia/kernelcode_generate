# memory.md

## 功能简介

定义 `memory dialect` 的最小公开 IR：`memory.get_data` 从 `!nn.memory<...>` 读取 backing data pointer，结果以 `!symbol.ptr<element_type, template = T?>` 表达。该 dialect 只承载 memory data pointer 查询，不新增 has-data / ptr-ne-zero presence API、optional memory type 或 DSL `memory.data` 表面 API。

## API 列表

- `Memory = Dialect("memory", [MemoryGetDataOp], [])`
- `class MemoryGetDataOp(source: SSAValue | Operation, result_type: Attribute | None = None)`

## 文档信息

- `spec`：[`spec/dialect/memory.md`](../../spec/dialect/memory.md)
- `功能实现`：[`kernel_gen/dialect/memory.py`](../../kernel_gen/dialect/memory.py)
- `test`：[`test/dialect/test_memory.py`](../../test/dialect/test_memory.py)

## 依赖

- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：提供 `!nn.memory<...>` source 类型。
- [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)：提供 `SymbolPtrType` result 类型。
- [`spec/core/context.md`](../../spec/core/context.md)：默认 context 必须加载 `memory` dialect。

## API详细说明

### `Memory = Dialect("memory", [MemoryGetDataOp], [])`

- api：`Memory = Dialect("memory", [MemoryGetDataOp], [])`
- 功能说明：注册 `memory` dialect 与 `memory.get_data` operation。
- 使用示例：

  ```python
  from kernel_gen.core.context import build_default_context

  ctx = build_default_context()
  assert ctx.get_optional_op("memory.get_data") is not None
  ```
- 注意事项：本计划不要求在 `kernel_gen.dialect` 包根 re-export；公开导入路径固定为 `from kernel_gen.dialect.memory import Memory, MemoryGetDataOp`。

### `class MemoryGetDataOp(source: SSAValue | Operation, result_type: Attribute | None = None)`

- api：`class MemoryGetDataOp(source: SSAValue | Operation, result_type: Attribute | None = None)`
- 参数：
  - `source`：`!nn.memory<...>` SSA value 或 operation。
  - `result_type`：可选 `SymbolPtrType`；省略时由 source memory element dtype 与 template name 推导。
- 返回值：`MemoryGetDataOp`。
- 使用示例：

  ```python
  from kernel_gen.dialect.memory import MemoryGetDataOp

  ptr_op = MemoryGetDataOp(memory_value)
  ```
- 功能说明：生成 `memory.get_data` pointer query；它是 presence guard 构造链路的一部分，不算 memory data-use。
- 注意事项：source 必须是 `NnMemoryType`；result 必须是 `SymbolPtrType`；ptr dtype 必须等于 memory element type；ptr template 必须等于 memory template。错误关键短语分别包含 `memory.get_data source must be !nn.memory`、`memory.get_data result type must be !symbol.ptr`、`memory.get_data ptr dtype must match memory element_type`、`memory.get_data ptr template_name must match memory template_name`。

## 文本语法

```mlir
%ptr = memory.get_data %mem : !nn.memory<[#symbol.expr<N>], [#symbol.expr<1>], f32, #nn.space<global>, template = T> -> !symbol.ptr<f32, template = T>
```

`memory.get_data` 打印后再解析必须稳定保留 source memory type 与 result ptr type。

## 测试

- 测试文件：`test/dialect/test_memory.py`
- 执行命令：`pytest -q test/dialect/test_memory.py`

| 用例 ID | 功能 | 场景 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- |
| TC-DIALECT-MEMORY-001 | 公开入口 | `MemoryGetDataOp` 程序化构造 | result 为携带 dtype/template 的 `SymbolPtrType` | `test_memory_get_data_infers_symbol_ptr_type` |
| TC-DIALECT-MEMORY-002 | 解析/打印 | `memory.get_data` 文本 round-trip | parse/print 保持 memory 与 ptr 类型 | `test_memory_get_data_parse_print_round_trip` |
| TC-DIALECT-MEMORY-003 | 边界/异常 | 非 memory source | 按 source 错误关键短语失败 | `test_memory_get_data_rejects_non_memory_source` |
| TC-DIALECT-MEMORY-004 | 边界/异常 | result 不是 ptr 或 dtype/template 不匹配 | 按 result/dtype/template 错误关键短语失败 | `test_memory_get_data_rejects_invalid_result_type` |
