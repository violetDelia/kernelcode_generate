# lowering.md

用于定义 DSL 从 AST 到 IR 的 lowering 规则与校验规范。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：[`spec/dsl/lowering.md`](../../spec/dsl/lowering.md)
- `test`：[`test/dsl/test_memory_to_ir.py`](../../test/dsl/test_memory_to_ir.py)
- `功能实现`：[`python/dsl/lowering.py`](../../python/dsl/lowering.py)

## 设计目标

- 定义从 AST 到 IR 的确定性转换规则。
- 明确 lowering 前的校验职责与失败条件。
- 保证 `Memory` 中的 shape/stride/dtype/memory_level 信息被完整传递到 IR。
- 保证 lowering 结果可落地到 `xdsl`，并保持与 MLIR 生态兼容。

## 非目标

- 不定义后端优化 pass。
- 不处理复杂表达式化简与自动调度。
- 不负责 DSL builder 的用户接口设计。

## Lowering 原则

- 同一 AST 输入必须生成语义一致的 IR。
- lowering 分为“校验”和“转换”两个明确阶段。
- 任何会影响后端正确性的结构问题都必须在 lowering 前暴露。
- lowering 不得引入对 `faketensor` 或工作目录外项目实现的依赖。
- lowering 生成的 IR 可以参考常见中间表示的层级风格，但不得假设运行时直接依赖外部项目中的节点类。
- lowering 的目标实现为 `xdsl` IR，对外应能转换或打印为 MLIR 兼容格式。

## 输入与输出

输入：

- `ModuleAST` 或 `FunctionAST`

输出：

- `IRModule` 或 `IRFunction`

## 校验规则

Lowering 前必须至少校验以下内容：

- 每个 `TensorAST` 都绑定 `SymbolMemory`。
- `TensorAST.memory` 不得依赖 `faketensor`。
- 每个 `LoadAST` / `StoreAST` 的 `offset/stride` 必须可规范化为合法访存描述。
- 每个 `BinaryExprAST` / `CompareExprAST` 若作用于 `Memory`，其两侧 shape 必须严格一致。
- 每个 `BinaryExprAST` / `CompareExprAST` 在执行前都必须通过类型合法性检查。
- `BinaryExprAST` / `CompareExprAST` 的类型与 shape 校验规则必须与 [`spec/operation/memory.md`](../../spec/operation/memory.md) 保持一致。
- `ForAST` 的 `start` 与 `end` 不得为空。
- AST 中使用到的张量和变量必须已定义。
- `memory_level` 必须属于 `global/shared/local`。

## 核心 lowering 规则

### TensorAST -> IRBuffer

- `TensorAST(name, memory)` lowering 为 `IRBuffer`。
- `IRBuffer.name = name`
- `IRBuffer.shape = memory.shape`
- `IRBuffer.stride = memory.stride`
- `IRBuffer.dtype = memory.dtype`
- `IRBuffer.memory_level = memory.memory_level`
- 在 `xdsl` 中优先对应为 `func.func` 参数上的 `memref` 类型值，必要时附带 memory-level 属性。

### ScalarArgAST -> IRScalarArg

- `ScalarArgAST(name, value_type)` lowering 为函数标量参数。
- 在 `xdsl` 中优先对应为 `func.func` 的标量参数类型。

### FunctionAST -> IRFunction

- `FunctionAST.name` 直接映射到 `IRFunction.name`
- `inputs` 中的张量 lowering 为 `IRFunction.buffers`
- `inputs` 中的标量参数 lowering 为 `IRScalarArg`
- `body` lowering 为 `IRFunction.body`
- 在 `xdsl` 中优先对应为 `func.func`

### BlockAST -> IRBlock

- 顺序 lowering `statements`
- 保持语句顺序不变

### ForAST -> IRFor

- `var` lowering 为 `IRVar`
- `start/end` lowering 为常量或 IR 表达式
- `body` lowering 为 `IRBlock`
- 在 `xdsl` 中优先对应为 `scf.for`

### LoadAST -> IRLoad

- `tensor` 解析为 buffer 名称
- `offset/stride` 先规范化为索引表达式或线性访存描述
- 再 lowering 为 `IRLoad`
- 在 `xdsl` 中优先对应为 `memref.load`

### StoreAST -> IRStore

- `tensor` 解析为 buffer 名称
- `offset/stride` 先规范化
- `value` lowering 为 IR 表达式
- 在 `xdsl` 中优先对应为 `memref.store`

### BinaryExprAST -> IRBinary

- `op` 原样传递
- `lhs/rhs` 递归 lowering
- 在 `xdsl` 中优先对应为 `arith` 方言中的算术操作
- lowering 前必须确认 `lhs/rhs` 的操作类型合法，且 `dtype` 可兼容。

### CompareExprAST -> IRCompare

- `op` 原样传递
- `lhs/rhs` 递归 lowering
- 在 `xdsl` 中优先对应为 `arith` 或兼容的比较操作
- 比较结果应为 predicate/bool 类型
- lowering 前必须确认 `lhs/rhs` 的类型合法，且比较语义可定义。

### ConstAST / VarAST

- `ConstAST` -> `IRConst`
- `VarAST` -> `IRVar`

## Memory 相关要求

- `Memory` 是 lowering 的输入元信息来源，不直接成为 IR 节点。
- `shape`、`stride`、`dtype`、`memory_level` 必须体现在 `IRBuffer` 中。
- 若 `Memory.stride` 缺省，必须在进入 lowering 前已补齐，或在 lowering 的规范化阶段补齐为默认连续布局。

## 名称解析

- AST 中的张量引用在 lowering 时必须完成到 `IRBuffer.name` 的解析。
- AST 中的变量引用在 lowering 时必须完成作用域绑定。
- 解析失败时抛 `NameError`。
- 标量参数应解析为函数参数对应的 SSA 值。

## 错误处理

建议错误类型：

- `TypeError`
  - AST 节点类型不匹配
  - `TensorAST.memory` 不是 `SymbolMemory`
  - 运算输入类型不合法
  - `dtype` 不兼容
- `ValueError`
  - rank 不一致
  - `Memory` 运算时 shape 不一致
  - `ForAST` 边界为空
  - `memory_level` 非法
- `NameError`
  - 未定义张量
  - 未定义变量
- `NotImplementedError`
  - AST 中出现当前 lowering 尚未支持的节点类型

## 最小示例

输入 AST：

- `FunctionAST("kernel", ...)`
- 一个 `TensorAST(A)`
- 一个 `ScalarArgAST(B, int)`
- 一个 `LoadAST(A, offset=B, stride=A.stride)`

lowering 后 IR：

- `IRFunction("kernel")`
- `IRBuffer("A", ...)`
- `IRScalarArg("B", ...)`
- 一个 `IRLoad("A", ...)`
- 若实现层使用 `xdsl`，则对应 `func.func` + `memref.load` 等结构

## 实现建议

- `validate_ast(ast)` 与 `lower_ast(ast)` 拆开实现。
- 名称解析建议使用显式 symbol table，不依赖全局状态。
- lowering 输出优先使用 dataclass 或不可变对象，便于测试比较。
- 若后续要兼容其他中间表示，建议先输出本项目 IR，再增加单独适配阶段，而不是直接在 lowering 中绑定外部实现。
- 若直接输出 `xdsl` IR，建议保留一层本项目 AST 校验逻辑，再在 lowering 末端构造 `xdsl` 操作。

## 返回与错误

### 成功返回

- `lower_ast(FunctionAST)` 返回 `IRFunction`
- `lower_ast(ModuleAST)` 返回 `IRModule`

### 失败返回

- AST 非法时抛 `TypeError`、`ValueError` 或 `NameError`
- 未支持节点时抛 `NotImplementedError`

## 测试

- 测试文件：[`test/dsl/test_memory_to_ir.py`](../../test/dsl/test_memory_to_ir.py)
- 执行命令：`pytest -q test/dsl/test_memory_to_ir.py`

### 测试目标

- 验证 `TensorAST -> IRBuffer` 保留完整 memory 元信息。
- 验证 copy kernel 的 AST 可正确 lowering 到 IR。
- 验证 `Memory` 的算术与比较操作可正确 lowering。
- 验证 lowering 前会先执行类型合法性检查。
- 验证动态循环边界和符号 shape 在 IR 中不丢失。
- 验证 rank 不一致、未定义名称和非法 memory_level 错误路径。

### 测试标准

- lowering 结果结构稳定、字段可比较。
- 校验错误在 lowering 前或 lowering 入口稳定暴露。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| LOW-001 | Buffer lowering | `TensorAST(memory)` | 已有 `SymbolMemory` | lowering | 生成 `IRBuffer` |
| LOW-002 | Function lowering | copy kernel | AST 合法 | lowering | 生成 `IRFunction` |
| LOW-003 | 动态边界 | `end="N"` | AST 合法 | lowering | IR 保留符号边界 |
| LOW-004 | 校验 | 非法访存描述 | `offset/stride` 无法规范化 | lowering | 抛 `ValueError` |
| LOW-005 | 校验 | 未定义张量 | tensor 未绑定 | lowering | 抛 `NameError` |
| LOW-006 | 运算 lowering | Memory 相加 | shape 一致 | lowering | 生成 `IRBinary` |
| LOW-007 | 比较 lowering | Memory 比较 | shape 一致 | lowering | 生成 `IRCompare` |
| LOW-008 | 类型校验 | 标量类型不合法 | `add(X, "3")` | lowering | 抛 `TypeError` |
| LOW-009 | 类型校验 | dtype 不兼容 | `lhs.dtype!=rhs.dtype` | lowering | 抛 `TypeError` |
| LOW-010 | 校验 | 非法依赖 | memory 依赖 `faketensor` | lowering | 视为不合法输入 |
