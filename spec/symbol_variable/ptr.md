# ptr.md

## 功能简介

用于冻结 Python 上层 `class Ptr` 的公开语义。`Ptr` 是一个仅承载 pointee dtype 的类型对象，面向 DSL 函数输入注解与 runtime args 传入场景。

## 文档信息

- 创建者：`咯咯咯`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/symbol_variable/ptr.md`](../../spec/symbol_variable/ptr.md)
- `test`：[`test/symbol_variable/test_ptr.py`](../../test/symbol_variable/test_ptr.py)（计划新增）
- `功能实现`：[`kernel_gen/symbol_variable/ptr.py`](../../kernel_gen/symbol_variable/ptr.py)（计划新增）

## 依赖

- [`ARCHITECTURE/plan/ptr_symbol_func_input_plan.md`](../../ARCHITECTURE/plan/ptr_symbol_func_input_plan.md)：P1 任务来源与边界定义。
- [`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md)：后续包导出层将基于本文件导出 `Ptr`。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：用于明确 `Ptr` 与 `Memory` 的职责边界。
- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：用于明确 `Ptr` 与 `SymbolDim` 的职责边界。

## 目标

- 定义上层 `class Ptr` 的最小稳定语义：`Ptr(dtype)`。
- 明确 `Ptr` 只表示 pointee dtype，不带名字。
- 明确 `Ptr` 的构造参数约束与失败边界（缺参、多参）。
- 明确 `Ptr` 不是 `Memory`，也不是 `SymbolDim`，三者无别名关系。

## 限制与边界

- 本文件只定义 Python 上层 `Ptr` 对象，不定义 IR 文本（例如 `!symbol.ptr<...>`）。
- 本文件不定义 DSL AST、lowering、codegen、runtime/include、审查或复审规则。
- `Ptr` 不带名字；禁止具名形式，例如 `Ptr("data", f32)`。
- `Ptr` 不表示地址值，不表示 shape，不表示 stride。
- `Ptr` 不是 `Memory`，也不是 `SymbolDim`。
- `Ptr` 不得写成 `SymbolDim` 的别名、兼容名或 `Memory` 的特例。

## 公开接口

### `class Ptr`

功能说明：

- 表示“指向某个 element dtype 的指针类型对象”。
- 公开最小构造入口为 `Ptr(dtype)`。

参数说明：

- `dtype`：pointee element dtype（如 `f32`）。

使用示例：

```python
from kernel_gen.symbol_variable import Ptr
from xdsl.dialects.builtin import f32

ptr = Ptr(f32)
```

注意事项：

- `Ptr` 只承载 pointee dtype，不承载地址名或地址值。
- `Ptr` 不带名字；`Ptr(f32)` 与 `Ptr(f32)` 的等价性仅由 dtype 决定。
- `Ptr` 与 `Memory`、`SymbolDim` 为不同对象职责，不能互相替代。

返回与限制：

- 返回 `Ptr` 对象。
- 仅允许 1 个 dtype 参数；参数数量非法时必须抛 `TypeError`，消息包含 `Ptr requires exactly one dtype`。

### 构造失败边界

功能说明：

- 冻结构造参数数量的失败口径。

参数说明：

- 无额外参数。

使用示例：

```python
from kernel_gen.symbol_variable import Ptr
from xdsl.dialects.builtin import f32

# 缺少 dtype
Ptr()

# 多传参数
Ptr(f32, f32)
```

注意事项：

- `Ptr()` 必须抛 `TypeError`，消息包含 `Ptr requires exactly one dtype`。
- `Ptr(f32, f32)` 必须抛 `TypeError`，消息包含 `Ptr requires exactly one dtype`。

返回与限制：

- 该场景无返回值；只定义错误行为口径。

### 与 `Memory` / `SymbolDim` 的关系

功能说明：

- 明确 `Ptr` 的对象边界，防止与现有 `symbol_variable` 类型混淆。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable import Memory, Ptr, SymbolDim
from xdsl.dialects.builtin import f32

ptr = Ptr(f32)
dim = SymbolDim("N")
```

注意事项：

- `Ptr` 不是 `Memory`，不表示张量容器元信息。
- `Ptr` 不是 `SymbolDim`，不表示整数符号维度表达。
- 不存在公开别名关系：`Ptr != Memory`、`Ptr != SymbolDim`。

返回与限制：

- 该条目只定义类型职责边界，不定义运行时转换规则。

## 测试

- 计划测试文件：[`test/symbol_variable/test_ptr.py`](../../test/symbol_variable/test_ptr.py)
- 验证命令（文档验收）：

```bash
rg -n 'class Ptr|Ptr\(f32\)|Ptr requires exactly one dtype|不带名字|不表示地址值|不是 Memory|不是 SymbolDim' spec/symbol_variable/ptr.md -S
```

### 测试目标

- `test_ptr_preserves_pointee_dtype`：
  - 输入：`ptr = Ptr(f32)`。
  - 预期输出：公开文本可表达 `Ptr(f32)`，且 pointee dtype 为 `f32`。
- `test_ptr_rejects_missing_dtype`：
  - 输入：`Ptr()`。
  - 预期输出：抛 `TypeError`，消息包含 `Ptr requires exactly one dtype`。
- `test_ptr_rejects_extra_args`：
  - 输入：`Ptr(f32, f32)`。
  - 预期输出：抛 `TypeError`，消息包含 `Ptr requires exactly one dtype`。
- `test_ptr_is_not_memory_or_symbol_dim`：
  - 输入：`Ptr(f32)` 与 `Memory(...)` / `SymbolDim("N")`。
  - 预期输出：文档明确三者不是同类，不存在公开别名关系。
