# ast.md

用于定义 DSL 的 AST 设计规范，描述 `Memory` 输入在语义层如何组织为抽象语法树。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- `test`：[`test/dsl/test_memory_to_ir.py`](../../test/dsl/test_memory_to_ir.py)
- `功能实现`：[`python/dsl/ast.py`](../../python/dsl/ast.py)

## 设计目标

- 用独立 AST 表达 DSL 的程序语义，不把语义逻辑塞进 `Memory` 类型本身。
- 为后续 lowering 到 IR 提供稳定、清晰、可校验的中间层。
- 支持动态 shape、动态边界和基于 `Memory` 的张量访存表达。
- 支持从带类型标注的 Python 函数签名中提取张量参数与标量参数。

## 非目标

- 不定义具体后端代码生成格式。
- 不承担优化、调度、并行映射或自动求导能力。
- 不引入文本解析器；第一阶段约束 Python 函数式 DSL 对应的 AST。

## 依赖约定

- `symbol_variable.memory.SymbolMemory`：张量元信息输入。
- `symbol_variable.symbol_dim.SymbolDim`：动态或静态整数表达。
- `symbol_variable.symbol_shape.SymbolShape`：shape/stride 表达。

## AST 设计原则

- AST 只表达“程序语义”，不夹带后端实现细节。
- AST 节点之间通过显式字段建立关系，不使用隐式全局状态。
- `Memory` 是 `TensorAST` 的元信息字段，不是 AST 节点树的替代物。
- `Memory` 运算的原始语义定义在 AST 外；AST 只负责捕获这些运算。
- 所有动态信息必须在 AST 中被显式保留，不得在构造时提前丢失。

## 节点分类

### 模块与函数节点

- `ModuleAST`
  - 字段：`functions`
  - 说明：一个 DSL 模块，可包含多个函数。
- `FunctionAST`
  - 字段：`name`、`inputs`、`outputs`、`body`
  - 说明：一个可 lowering 的顶层计算单元。

### 张量与变量节点

- `TensorAST`
  - 字段：`name`、`memory`
  - 说明：具名张量声明，其中 `memory` 必须为 `SymbolMemory`。
- `ScalarArgAST`
  - 字段：`name`、`value_type`
  - 说明：函数签名中的标量参数，例如 `int`。
- `VarAST`
  - 字段：`name`
  - 说明：循环变量或索引变量。

### 语句节点

- `BlockAST`
  - 字段：`statements`
  - 说明：有序语句块。
- `ForAST`
  - 字段：`var`、`start`、`end`、`body`
  - 说明：循环结构。
- `StoreAST`
  - 字段：`tensor`、`offset`、`stride`、`value`
  - 说明：写入张量元素，前端保留 `offset/stride` 访问语义。

### 表达式节点

- `LoadAST`
  - 字段：`tensor`、`offset`、`stride`
  - 说明：读取张量元素，前端保留 `offset/stride` 访问语义。
- `BinaryExprAST`
  - 字段：`op`、`lhs`、`rhs`
  - 说明：二元表达式。
- `CompareExprAST`
  - 字段：`op`、`lhs`、`rhs`
  - 说明：逐元素比较表达式。
- `ConstAST`
  - 字段：`value`
  - 说明：常量。

## AST 约束

### FunctionAST

- `inputs` 必须由 `TensorAST` 与 `ScalarArgAST` 组成。
- `outputs` 可以为空，或由 `TensorAST` / 标量返回值描述组成。
- `body` 必须为 `BlockAST`。
- `name` 不得为空字符串。
- 应支持从 Python 函数签名提取参数信息，例如 `def kernel(A: SymbolMemory, B: int)`.

### TensorAST

- `name` 必须为合法标识名称。
- `memory` 必须为 `SymbolMemory`。
- `memory` 不得依赖 `faketensor` 或工作目录外其他项目实现。

### ForAST

- `var` 必须为 `VarAST`。
- `start` 与 `end` 支持 `int`、`SymbolDim` 或等价表达节点。
- `body` 必须为 `BlockAST`。

### LoadAST / StoreAST

- `tensor` 必须引用已定义的 `TensorAST`。
- `offset` 必须为标量表达式，或可被规范化为索引表达式的序列。
- `stride` 可以为空；非空时必须与 `tensor.memory.stride` 语义兼容。
- `StoreAST.value` 必须为可求值表达式节点。

### BinaryExprAST

- 第一阶段只要求支持 `add`、`sub`、`mul`、`div`。
- `lhs` 与 `rhs` 必须为表达式节点。
- 若 `lhs/rhs` 带有 `Memory` 张量语义，必须先满足 `spec/operation/memory.md` 中的类型合法性规则。
- 若 `lhs/rhs` 为 `SymbolMemory` 张量语义，必须满足 shape 严格一致；不支持广播。
- 该节点语义与 `spec/operation/memory.md` 中的独立运算规则保持一致。

### CompareExprAST

- 第一阶段支持 `eq`、`ne`、`lt`、`le`、`gt`、`ge`。
- `lhs` 与 `rhs` 必须为表达式节点。
- 若 `lhs/rhs` 带有 `Memory` 张量语义，必须先满足 `spec/operation/memory.md` 中的类型合法性规则。
- 若 `lhs/rhs` 为 `SymbolMemory` 张量语义，必须满足 shape 严格一致；不支持广播。
- 比较结果仍表示逐元素张量语义结果，而不是单个 Python `bool`。
- 该节点语义与 `spec/operation/memory.md` 中的独立比较规则保持一致。

## 建议 DSL 映射

- `def kernel(A: SymbolMemory, B: int)` -> `FunctionAST`
- `A: SymbolMemory` -> `TensorAST`
- `B: int` -> `ScalarArgAST`
- `load(tensor, offset, stride)` -> `LoadAST`
- `store(tensor, offset, value, stride)` -> `StoreAST`
- `range_for(...)` 或等价循环 -> `ForAST`
- Python 算术表达式 -> `BinaryExprAST`
- Python 比较表达式或 DSL 比较函数 -> `CompareExprAST`

## 最小示例

```python
def kernel(A: SymbolMemory, B: int):
    SA = load(A, B, A.get_stride())
    return SA
```

该示例至少应构造出：

- 一个 `FunctionAST`
- 一个 `TensorAST`
- 一个 `ScalarArgAST`
- 一个 `LoadAST`
- 一个局部绑定或返回表达式节点

## 返回与错误

### 成功返回

- DSL builder 返回对应 AST 节点对象。
- AST 节点支持被 lowering 和校验阶段消费。

### 失败返回

- 节点字段类型不符时抛 `TypeError`。
- 结构不合法时抛 `ValueError`。
- 引用未定义张量或变量时抛 `NameError`。

## 测试

- 测试文件：[`test/dsl/test_memory_to_ir.py`](../../test/dsl/test_memory_to_ir.py)
- 执行命令：`pytest -q test/dsl/test_memory_to_ir.py`

### 测试目标

- 验证 Python 函数签名可正确映射为 `FunctionAST`、`TensorAST` 与 `ScalarArgAST`。
- 验证 `load(offset, stride)` 示例可构造出预期 AST 结构。
- 验证 `Memory` 的逐元素算术与比较操作可构造正确 AST。
- 验证非法参数类型、非法 offset/stride 和未定义名称的错误路径。

### 测试标准

- AST 节点结构可稳定比较。
- 动态维度、符号边界与 memory 元信息在 AST 中被完整保留。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| AST-001 | 函数签名 | `SymbolMemory` 与 `int` 参数 | N/A | `def kernel(A: SymbolMemory, B: int)` | 生成 `FunctionAST`、`TensorAST`、`ScalarArgAST` |
| AST-002 | 访存构造 | `load(offset, stride)` | 已定义 `A/B` | `SA = load(A, B, A.get_stride())` | 构造成功 |
| AST-003 | 循环构造 | 动态边界 | `end="N"` | 构造 `ForAST` | 保留符号边界 |
| AST-004 | 校验 | 非法参数类型 | 参数未标注 | 构造函数 AST | 抛 `TypeError` |
| AST-005 | 校验 | offset/stride 非法 | stride 维度不匹配 | 构造 `LoadAST` | 抛 `ValueError` |
| AST-006 | 运算构造 | Memory 相加 | `X.shape=[A,B]`, `Y.shape=[A,B]` | `X + Y` | 构造 `BinaryExprAST` |
| AST-007 | 比较构造 | Memory 比较 | `X.shape=[A,B]`, `Y.shape=[A,B]` | `eq(X, Y)` | 构造 `CompareExprAST` |
| AST-008 | 校验 | 未定义变量 | 缺少变量绑定 | 构造或校验 | 抛 `NameError` |
