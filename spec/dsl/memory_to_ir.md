# memory_to_ir.md

用于定义一个以 `Memory` 为输入、经 AST 表达后再 lowering 到 IR 的 DSL 总体设计规范。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：[`spec/dsl/memory_to_ir.md`](../../spec/dsl/memory_to_ir.md)
- `AST`：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- `IR`：[`spec/dsl/ir.md`](../../spec/dsl/ir.md)
- `Lowering`：[`spec/dsl/lowering.md`](../../spec/dsl/lowering.md)
- `Operation`：[`spec/operation/memory.md`](../../spec/operation/memory.md)
- `test`：[`test/dsl/test_memory_to_ir.py`](../../test/dsl/test_memory_to_ir.py)
- `功能实现`：[`python/dsl/memory_to_ir.py`](../../python/dsl/memory_to_ir.py)

## 设计目标

- 提供一个最小但可扩展的 DSL，用于描述基于 `Memory` 的张量计算。
- 将“用户书写接口”“语义结构表达”“后端 IR 表达”分成三个稳定层次：DSL 输入层、AST 层、IR 层。
- 允许 `shape`、`stride`、下标和循环边界使用 `SymbolDim`/`SymbolShape` 表达动态信息。
- 保持 DSL 与具体后端解耦，不绑定 `faketensor` 或某个既有 IR 实现。
- IR 落地使用 `xdsl`，并与 MLIR 生态兼容。

## 非目标

- 不在本阶段定义完整的算子库、自动调度器或类型推导系统。
- 不处理自动求导、内存复用、并行映射和复杂优化。
- 不要求 IR 直接等同于 MLIR、TVM IR 或 LLVM IR；这里只定义项目内部的中间表示约束。

## 设计原则

- `Memory` 是 DSL 的输入值对象，不直接承担 AST 节点职责。
- `Memory` 相关运算可在 DSL 外独立使用；DSL 只复用这套运算语义并将其捕获为 AST。
- AST 负责表达“程序语义”，IR 负责表达“后端可消费的显式结构”。
- Lowering 必须是确定性的，同一 AST 输入应生成语义一致的 IR。
- 动态维度信息必须从 `Memory.shape` / `Memory.stride` 显式传递到 AST 与 IR，不得丢失。
- IR 的层次组织可以参考已有编译中间表示的分层风格，但接口与字段定义必须保持本项目独立。
- 所有计算在 shape 校验之前或同时，必须先满足类型合法性约束。

## 依赖约定

- `symbol_variable.symbol_dim.SymbolDim`：表示动态或静态整数维度。
- `symbol_variable.symbol_shape.SymbolShape`：表示 shape/stride 向量。
- `symbol_variable.memory.SymbolMemory`：表示张量输入对象。

## 核心术语

- DSL：用户编写计算描述时直接接触的接口层。
- AST：抽象语法树，描述语义结构，不关心最终后端编码细节。
- IR：中间表示，显式表达缓冲区、循环、访存和算术操作。
- Memory：张量描述对象，含 shape、stride、dtype、memory_level。
- Buffer：AST/IR 中可被 load/store 的命名内存对象，通常由 `Memory` lowering 而来。

## 总体流程

1. 用户准备 `SymbolMemory` 作为输入张量描述。
2. DSL 构造函数、表达式与语句节点，形成 AST。
3. Lowering 阶段校验 AST，并将 `Memory`、索引、循环、表达式转换为 IR。
4. 后续后端再基于 IR 做代码生成或进一步优化。

## 分层设计

### DSL 输入层

功能说明：

- DSL 的主入口是“带类型标注的 Python 函数”。
- 函数参数中的 `SymbolMemory` 表示张量输入，`int` 等标量类型表示普通标量参数。
- 函数体中的 `load`、`store`、算术表达式和循环描述语义，再由前端构造成 AST。

建议入口：

- `def kernel(A: SymbolMemory, B: int, ...): ...`

建议内建 DSL 操作：

- `load(tensor, offset, stride=None)`
- `store(tensor, offset, value, stride=None)`
- `add/sub/mul/truediv`
- `eq/ne/lt/le/gt/ge`
- `range_for(start, end, step=1)` 或等价循环构造
- 基础算术表达式：`+`、`-`、`*`、`/`

示例：

`load` 示例：

```python
from dsl import load

def kernel_load(A: SymbolMemory, i: int):
    x = load(A, i, A.get_stride())
    return x
```

`store` 示例：

```python
from dsl import load, store

def kernel_store(A: SymbolMemory, B: SymbolMemory, i: int):
    x = load(A, i, A.get_stride())
    store(B, i, x, B.get_stride())
```

链式运算示例：

```python
from operation.memory import add

def kernel_chain(X: SymbolMemory, Y: SymbolMemory):
    z = add(add(X, 3), Y)
    return z
```

循环示例：

```python
from dsl import load, store, range_for

def kernel_copy(A: SymbolMemory, B: SymbolMemory, N: int):
    for i in range_for(0, N, 1):
        x = load(A, i, A.get_stride())
        store(B, i, x, B.get_stride())
```

### AST / IR / Lowering

- AST 规范见 [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- IR 规范见 [`spec/dsl/ir.md`](../../spec/dsl/ir.md)
- Lowering 规范见 [`spec/dsl/lowering.md`](../../spec/dsl/lowering.md)
- Operation 规范见 [`spec/operation/memory.md`](../../spec/operation/memory.md)

## Memory 输入约束

`Memory` 在 DSL 中承担“张量元信息输入”的角色，至少包含：

- `shape: SymbolShape`
- `stride: SymbolShape`
- `dtype: str | None`
- `memory_level: global/shared/local`

约束：

- `memory` 必须与 `faketensor` 解耦，不得依赖其他项目中的张量实现。
- `shape` 与 `stride` 维度数必须一致。
- 当 stride 缺省时，可在 `Memory` 构造时或 lowering 前补齐默认连续布局。
- `Memory` 的算术与比较操作在独立的 `operation` 层定义，不直接放入基础类型规范中。
- 这套运算语义可脱离 DSL 独立使用；DSL 前端只负责把它们映射到 AST。
- 运算时必须同时检查 shape 合法性与类型合法性。

## 转换关系

- `Memory` 是 DSL 输入的张量元信息。
- Python 函数签名与函数体先构造 AST。
- lowering 阶段再将 AST 转为基于 `xdsl` 的 IR。
- 校验规则与转换规则见 [`spec/dsl/lowering.md`](../../spec/dsl/lowering.md)。

## 最小可用示例

输入：

```python
from symbol_variable.memory import SymbolMemory
from dsl import load
from operation.memory import add

def kernel(A: SymbolMemory, B: int):
    SA = load(A, B, A.get_stride())
    return SA
```

运算示例：

```python
from operation.memory import add

def kernel_add(X: SymbolMemory, Y: SymbolMemory):
    Z = add(X, Y)
    return Z
```

链式运算示例：

```python
from operation.memory import add

def kernel_chain(X: SymbolMemory, Y: SymbolMemory):
    Z = add(add(X, 3), Y)
    return Z
```

若 `X.shape == Y.shape == [A, B]`，则 `Z.shape` 仍为 `[A, B]`。

期望 AST 与 IR 的具体结构约束分别见：

- [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- [`spec/dsl/ir.md`](../../spec/dsl/ir.md)

## 实现建议

- 优先实现“Python 函数 + 类型标注”的 DSL 入口，不引入文本解析。
- 先实现 AST 数据结构与 lowering，再决定是否补更复杂的 tracing 机制。
- 将“校验”和“lowering”拆成独立阶段，便于测试错误分支。
- IR 节点建议使用 dataclass 或等价的结构化对象，便于比较与测试。

## 返回与错误

### 成功返回

- DSL 构造阶段返回 AST 节点对象。
- lowering 成功返回 `IRModule` 或 `IRFunction`。

### 失败返回

- DSL 构造时输入类型不合法抛 `TypeError`。
- AST 校验失败抛 `ValueError` 或 `NameError`。
- lowering 过程中遇到未支持节点类型抛 `NotImplementedError`。

## 测试

- 测试文件：[`test/dsl/test_memory_to_ir.py`](../../test/dsl/test_memory_to_ir.py)
- 执行命令：`pytest -q test/dsl/test_memory_to_ir.py`

### 测试目标

- 验证 `SymbolMemory` 可作为 DSL 输入正确构造 AST。
- 验证简单 copy/kernel AST 可正确 lowering 到 IR。
- 验证动态 shape 和符号循环边界在 IR 中被保留。
- 验证 rank 不一致、未定义张量、非法 memory_level 等错误路径。

### 测试标准

- 全部测试用例通过，`pytest` 返回码为 0。
- AST 与 IR 节点字段可稳定比较。
- lowering 不丢失 `shape`、`stride`、`dtype`、`memory_level` 信息。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| DSL-001 | AST 构造 | Python 函数入口 | N/A | `def kernel(A: SymbolMemory, B: int)` | 返回合法 AST |
| DSL-002 | IR lowering | `load(offset, stride)` | AST 合法 | lowering | 生成合法 IR |
| DSL-003 | 运算 | `Memory + Memory` | shape 一致 | `add(X, Y)` | 返回合法 AST/IR |
| DSL-004 | 校验 | shape 不一致 | `X.shape=[A,B]`, `Y.shape=[A,C]` | `add(X, Y)` | 抛 `ValueError` |
| DSL-005 | 校验 | 未定义变量 | 缺少变量绑定 | lowering | 抛 `NameError` |
| DSL-006 | 解耦 | 非法依赖 | memory 依赖 `faketensor` | 校验 | 视为不符合设计约束 |
