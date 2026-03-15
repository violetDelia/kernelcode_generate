# ir.md

用于定义 DSL lowering 后的 IR 设计规范，描述后端可消费的中间表示结构。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：[`spec/dsl/ir.md`](../../spec/dsl/ir.md)
- `test`：[`test/dsl/test_memory_to_ir.py`](../../test/dsl/test_memory_to_ir.py)
- `功能实现`：[`python/dsl/ir.py`](../../python/dsl/ir.py)

## 设计目标

- 提供独立于 DSL builder 的显式中间表示。
- 保留足够的张量与访存信息，支持后续代码生成与优化。
- 明确 `shape`、`stride`、`dtype`、`memory_level` 在 IR 中的表示方式。
- 基于 `xdsl` 实现 IR，并与 MLIR 生态兼容。

## 非目标

- 不要求 IR 直接等同于某个现有编译框架的 IR。
- 不在本阶段引入 SSA、类型系统细化或复杂控制流。
- 不负责前端 AST 构造与错误恢复。

## 设计原则

- IR 必须比 AST 更显式，便于后端消费。
- IR 中不保留 DSL builder 包装对象。
- IR 必须能稳定承载动态维度和符号表达式。
- Buffer、Loop、Load、Store、Binary 等核心节点应支持结构化比较。
- IR 层次结构可参考常见中间表示的分层习惯，例如 `module/function/buffer/block/op`，但不能直接耦合外部实现细节。
- IR 的内存表示、函数、循环和算术应优先映射到 `xdsl` 提供的 MLIR 兼容 dialect。

## IR 节点

### 顶层节点

- `IRModule`
  - 字段：`functions`
- `IRFunction`
  - 字段：`name`、`buffers`、`body`
- `IRScalarArg`
  - 字段：`name`、`type`
  - 说明：函数的标量参数。

### 数据节点

- `IRBuffer`
  - 字段：`name`、`shape`、`stride`、`dtype`、`memory_level`
  - 说明：由 `SymbolMemory` lowering 而来。

### 控制流节点

- `IRBlock`
  - 字段：`ops`
- `IRFor`
  - 字段：`var`、`start`、`end`、`body`

### 访存与表达式节点

- `IRLoad`
  - 字段：`buffer`、`indices`
- `IRStore`
  - 字段：`buffer`、`indices`、`value`
- `IRBinary`
  - 字段：`op`、`lhs`、`rhs`
- `IRCompare`
  - 字段：`op`、`lhs`、`rhs`
- `IRConst`
  - 字段：`value`
- `IRVar`
  - 字段：`name`

## IR 约束

### IRBuffer

- `shape` 与 `stride` 必须来源于同一个 `SymbolMemory`。
- `shape.rank()` 与 `stride.rank()` 必须一致。
- `memory_level` 只能取 `global`、`shared`、`local`。
- `dtype` 可为空，但字段必须存在。

### IRLoad / IRStore

- `buffer` 必须引用已声明的 `IRBuffer`。
- `indices` 数量必须与 `buffer.shape.rank()` 一致。
- `IRStore.value` 必须为 IR 表达式节点。

### IRFor

- `var` 应为 `IRVar`。
- `start/end` 支持常量或符号表达式节点。
- `body` 必须为 `IRBlock`。

### IRBinary

- 第一阶段支持 `add`、`sub`、`mul`、`div`。
- `lhs/rhs` 必须为 IR 表达式节点。
- 若 `lhs/rhs` 对应张量语义值，必须先满足 `spec/operation/memory.md` 中的类型合法性与 shape 规则。
- 若双侧都带有 `dtype` 信息，则二者必须可兼容。

### IRCompare

- 第一阶段支持 `eq`、`ne`、`lt`、`le`、`gt`、`ge`。
- `lhs/rhs` 必须为 IR 表达式节点。
- 若 `lhs/rhs` 对应张量语义值，必须先满足 `spec/operation/memory.md` 中的类型合法性与 shape 规则。
- 结果类型应为 `bool` 或 predicate。

## 与 AST 的关系

- AST 表达语义结构，IR 表达显式后端结构。
- AST 中的 `TensorAST(memory=...)` 在 IR 中必须变成显式 `IRBuffer`。
- AST 中的 `ScalarArgAST` 在 IR 中必须变成显式函数参数或 SSA 值。
- AST 中的访存和表达式节点在 IR 中保留结构，但字段更直接、名称解析已完成。

## 设计参考

- 可参考已有中间表示的层级设计和节点组织方式。
- 本项目 IR 不要求与任何外部实现一一同名，也不要求字段完全一致。
- 参考的重点是“结构分层清晰、buffer 与 op 显式分离、函数级作用域明确”。

## xdsl 兼容要求

- IR 的实现基于 `xdsl`。
- IR 应能打印为 MLIR 兼容的文本格式。
- 优先使用或映射到 `builtin`、`func`、`memref`、`scf`、`arith` 等 dialect。
- 仅当现有 dialect 无法承载语义时，才新增自定义 dialect。
- 若需要自定义 dialect，优先采用 `xdsl` 的 IRDL 机制定义操作与属性。

## Buffer 表示建议

`IRBuffer` 至少包含：

- `name`
- `shape`
- `stride`
- `dtype`
- `memory_level`

其中：

- `shape` 建议保留 `SymbolShape` 或等价符号序列。
- `stride` 建议保留 `SymbolShape` 或等价符号序列。
- `memory_level` 使用字符串或枚举值，但语义上只允许 `global/shared/local`。

推荐的 `xdsl` 映射：

- `IRModule` -> `builtin.module`
- `IRFunction` -> `func.func`
- `IRScalarArg` -> `func.func` 的标量参数
- `IRBuffer` -> `memref` 类型的函数参数或符号对象
- `IRFor` -> `scf.for`
- `IRLoad` -> `memref.load`
- `IRStore` -> `memref.store`
- `IRBinary` -> `arith` 对应算术操作
- `IRCompare` -> `arith` 或兼容比较操作

## 最小示例

对于一个二维 copy kernel，IR 至少应包含：

- 一个 `IRFunction(name="copy")`
- 两个 `IRBuffer(name="A"/"B")`
- 若有标量参数，则对应 `IRScalarArg`
- 两个嵌套 `IRFor`
- 一个 `IRLoad(buffer="A", indices=[i, j])`
- 一个 `IRStore(buffer="B", indices=[i, j], value=...)`

## 返回与错误

### 成功返回

- IR 构造成功返回 `IRModule`、`IRFunction` 或具体 IR 节点。

### 失败返回

- 字段类型错误抛 `TypeError`。
- Buffer 元信息不一致、rank 不一致等结构错误抛 `ValueError`。
- 引用未声明 buffer 时抛 `NameError`。

## 测试

- 测试文件：[`test/dsl/test_memory_to_ir.py`](../../test/dsl/test_memory_to_ir.py)
- 执行命令：`pytest -q test/dsl/test_memory_to_ir.py`

### 测试目标

- 验证 `IRBuffer` 保留 `shape`、`stride`、`dtype`、`memory_level`。
- 验证 loop/load/store/binary 的 IR 节点结构稳定。
- 验证比较节点可稳定表达逐元素比较语义。
- 验证错误的 rank、非法 `memory_level`、类型不兼容和未声明 buffer 路径。

### 测试标准

- IR 节点可稳定比较。
- 动态 shape 与符号边界在 IR 中不丢失。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| IR-001 | Buffer 表达 | 由 `Memory` 派生 | 已有 `SymbolMemory` | 构造 `IRBuffer` | 保留 shape/stride/dtype/memory_level |
| IR-002 | Loop 表达 | 动态边界 | end=`"N"` | 构造 `IRFor` | 保留符号边界 |
| IR-003 | 访存表达 | 二维张量 | `load/store` | 构造 IR 访存节点 | 索引与 rank 一致 |
| IR-004 | 错误处理 | rank 不一致 | shape/stride 不匹配 | 构造 `IRBuffer` | 抛 `ValueError` |
| IR-005 | 比较表达 | Memory 比较 | shape 一致 | 构造 `IRCompare` | 返回 predicate/bool 结果 |
| IR-006 | 错误处理 | 非法层级 | `memory_level="foo"` | 构造 `IRBuffer` | 抛 `ValueError` |
| IR-007 | 类型校验 | 非法标量类型 | `lhs.dtype=float32` | 构造 `IRBinary(lhs, "3")` | 抛 `TypeError` |
| IR-008 | 类型校验 | dtype 不兼容 | `lhs.dtype=float32`, `rhs.dtype=int32` | 构造 `IRBinary(lhs, rhs)` | 抛 `TypeError` |
