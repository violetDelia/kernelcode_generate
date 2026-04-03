# symbol_dim.md

## 功能简介

[immutable]用于定义 `SymbolDim` 的开发者设计规范。`SymbolDim` 是维度表达的统一入口，既支持静态整数维度，也支持基于符号的动态维度。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`大闸蟹`
- `spec`：[`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)
- `功能实现`：[`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py)
- `test`：[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)

## 依赖

- `sympy`：负责整数符号、静态整数与混合表达式的底层表示。
- [`expectation/symbol_variable/symbol_dim.py`](../../expectation/symbol_variable/symbol_dim.py)：本链路的只读 acceptance 定义来源。
- [`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)：当前单元测试承载文件；后续实现阶段需按本 spec 补齐 expectation 闭环。
- [`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md)：包级导入/导出与 legacy 路径边界来源。

## 目标

- 提供统一的 `SymbolDim` 公开入口，覆盖静态整数、动态符号与整数混合表达式。
- 明确 `+`、`-`、`*`、`/`、`//` 的公开语义、动态性传播与错误路径。
- 明确 `get_symbol()`、`get_value()`、`is_dynamic()` 的公开行为，支撑 [`expectation/symbol_variable/symbol_dim.py`](../../expectation/symbol_variable/symbol_dim.py) 最终运行成功。
- 以 [`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py) 承载单元测试，以 `python expectation/symbol_variable/symbol_dim.py` 作为只读 acceptance gate。

## 相邻边界

- `package_api.md` 负责包级导入边界；本文件只负责 `SymbolDim` 对象本身的构造、算术、比较与动态性语义。
- `symbol_shape.md` 负责多个 `SymbolDim` 的容器行为；本文件不定义切片、索引赋值或列表序列化。
- `memory.md` 负责 `Memory` 如何消费 `SymbolDim` 组成的 `shape/stride`；本文件不定义 `Memory` 的 dtype、space、format 或默认 stride 生成。
- `dialect/symbol.md` 负责 IR 层的整数 symbol type/attr 与查询接口；本文件不定义 IR 文本与 lowering。

## 限制与边界

- `SymbolDim` 只表示整数维度及其整型符号表达，不负责广播、约束求解、形状推导或高阶张量语义。
- 公开接口限定为 `SymbolDim(value)`、`get_symbol()`、`get_value()`、`is_dynamic()`、`__repr__()`、`__eq__()`，以及 `+`、`-`、`*`、`/`、`//` 对应的正向/反向运算；除为满足本文件要求所需的这些接口外，不再引入其他额外公开入口。
- 构造输入仅允许：
  - `int`：表示静态整数维度。
  - `str`：表示符号名；字符串执行 `strip()` 后不能为空，且不能是纯数字字符串。
  - `sympy.Basic`：表示已构造好的整数符号或整数表达式。
- 浮点输入与浮点算术操作数均不受支持：
  - `SymbolDim(1.5)` 必须抛出 `NotImplementedError`。
  - `SymbolDim(...)+1.5`、`-1.5`、`*1.5`、`/1.5`、`//1.5` 及对应反向运算必须抛出 `NotImplementedError`。
- 纯数字字符串与空白字符串属于非法输入，必须抛出 `ValueError`；除浮点外的其他非法类型必须抛出 `TypeError`。
- 动态性判断以表达式是否含自由符号为准：
  - 静态整数输入、静态整数之间的 `+`、`-`、`*`、`/`、`//` 结果必须保持 `is_dynamic() == False`。
  - 只要任一操作数含自由符号，结果必须保持 `is_dynamic() == True`。
- `get_value()` 的公开返回语义必须满足 expectation：
  - 静态整数、静态加减乘与静态整除结果返回可直接与 Python 对应结果比较的具体值。
  - 静态真除法结果返回可直接与 Python `/` 结果比较的具体值。
  - 动态符号或混合表达式返回可稳定比较的符号表达值。
- 不额外承诺异常消息文本；兼容性只要求异常类型与公开行为稳定。

## 公开接口

### `SymbolDim(value)`

功能说明：

- 统一的公开构造入口，用于创建静态整数维度、动态符号维度或混合整数表达式维度。

参数说明：

- `value`（`int | str | sympy.Basic`）：维度输入。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
import sympy as sp

SymbolDim(32)
SymbolDim("N")
SymbolDim(sp.Symbol("M", integer=True, real=True) + 1)
```

注意事项：

- `"12"`、`" 12 "`、`""`、`"   "` 必须抛出 `ValueError`。
- `1.5`、`-2.25` 等浮点输入必须抛出 `NotImplementedError`。
- `sympy.Symbol` 若未显式指定整数假设，实现需统一为整数语义。

返回与限制：

- 返回 `SymbolDim` 实例。
- 非法输入按“限制与边界”中的异常类型处理。

### `get_symbol()`

功能说明：

- 返回内部规整后的 `sympy` 表达式，作为实现侧统一表达。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

expr = SymbolDim("N").get_symbol()
```

注意事项：

- 返回值始终是 `sympy.Basic`。
- 该接口用于实现与测试读取标准化表达，不替代 `get_value()` 的对外比较语义。

返回与限制：

- 返回 `sympy.Basic`。

### `get_value()`

功能说明：

- 返回用于公开比较的当前值。
- 用于支撑 expectation 与测试中的静态值断言、动态表达式断言与混合表达式断言。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

assert SymbolDim(8).get_value() == 8
assert (SymbolDim(9) // SymbolDim(4)).get_value() == 2
assert (SymbolDim(9) / SymbolDim(4)).get_value() == 9 / 4
```

注意事项：

- 静态整数、静态加减乘与静态整除结果必须返回可与 Python 对应结果直接比较的具体值。
- 静态真除法结果必须返回可与 Python `/` 结果直接比较的具体值。
- 动态表达式可返回规整后的符号表达值，但必须保证 expectation 中的相等/不等比较稳定。

返回与限制：

- 返回具体值或规整后的符号表达值。

### `__repr__()`

功能说明：

- 返回当前内部表达式的公开字符串表示。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

assert repr(SymbolDim("N")) == "N"
```

注意事项：

- 输出以内部规整后的表达式为准。

返回与限制：

- 返回 `str`。

### `__add__() / __radd__()`

功能说明：

- 执行整数符号加法并返回新的 `SymbolDim`。

参数说明：

- `other`（`int | str | sympy.Basic | SymbolDim`）：右操作数或左操作数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

static_sum = SymbolDim(3) + SymbolDim(4)
dynamic_sum = 3 + SymbolDim("N")
```

注意事项：

- 静态整数加静态整数的结果必须保持非动态。
- 只要任一操作数含自由符号，结果必须保持动态。
- 浮点操作数必须抛出 `NotImplementedError`。

返回与限制：

- 返回 `SymbolDim`。

### `__sub__() / __rsub__()`

功能说明：

- 执行整数符号减法并返回新的 `SymbolDim`。

参数说明：

- `other`（`int | str | sympy.Basic | SymbolDim`）：右操作数或左操作数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

static_diff = SymbolDim(9) - SymbolDim(4)
dynamic_diff = SymbolDim(9) - SymbolDim("N")
```

注意事项：

- 结果动态性遵循“限制与边界”中的传播规则。
- 浮点操作数必须抛出 `NotImplementedError`。

返回与限制：

- 返回 `SymbolDim`。

### `__mul__() / __rmul__()`

功能说明：

- 执行整数符号乘法并返回新的 `SymbolDim`。

参数说明：

- `other`（`int | str | sympy.Basic | SymbolDim`）：右操作数或左操作数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

static_prod = SymbolDim(3) * SymbolDim(5)
dynamic_prod = SymbolDim(3) * SymbolDim("N")
```

注意事项：

- 结果动态性遵循“限制与边界”中的传播规则。
- 浮点操作数必须抛出 `NotImplementedError`。

返回与限制：

- 返回 `SymbolDim`。

### `__truediv__() / __rtruediv__()`

功能说明：

- 执行整数符号真除法并返回新的 `SymbolDim`。

参数说明：

- `other`（`int | str | sympy.Basic | SymbolDim`）：右操作数或左操作数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

static_div = SymbolDim(9) / SymbolDim(4)
dynamic_div = SymbolDim("N") / SymbolDim(4)
```

注意事项：

- 静态整数之间的真除法结果必须可通过 `get_value()` 与 Python `/` 结果直接比较。
- 含符号的真除法结果必须保持动态，并保留链式运算的结合顺序。
- 浮点操作数必须抛出 `NotImplementedError`。

返回与限制：

- 返回 `SymbolDim`。

### `__floordiv__() / __rfloordiv__()`

功能说明：

- 执行整数符号整除并返回新的 `SymbolDim`。

参数说明：

- `other`（`int | str | sympy.Basic | SymbolDim`）：右操作数或左操作数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

static_div = SymbolDim(9) // SymbolDim(4)
dynamic_div = SymbolDim("N") // SymbolDim(4)
```

注意事项：

- 静态整数之间的整除结果必须可通过 `get_value()` 与 Python `//` 结果直接比较。
- 含符号的整除结果必须保持动态，并保留链式运算的结合顺序。
- 浮点操作数必须抛出 `NotImplementedError`。

返回与限制：

- 返回 `SymbolDim`。

### `__eq__(other)`

功能说明：

- 比较当前值与 `other` 的公开等价性。

参数说明：

- `other`（`int | str | sympy.Basic | SymbolDim`）：比较对象。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

assert SymbolDim(4) == 4
assert SymbolDim("N") == SymbolDim("N")
```

注意事项：

- 比较规则必须基于规整后的整数符号表达。
- 非法类型比较继续抛出 `TypeError`；本接口不负责浮点算术语义。

返回与限制：

- 返回 `bool`。

### `is_dynamic()`

功能说明：

- 判断当前值是否包含自由符号。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

assert SymbolDim(8).is_dynamic() is False
assert (SymbolDim(8) + SymbolDim("N")).is_dynamic() is True
```

注意事项：

- 静态整数与静态整数算术结果必须返回 `False`。
- 只要表达式中仍有自由符号，必须返回 `True`。

返回与限制：

- 返回 `bool`。

## 测试

- 主测试文件：[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)
- acceptance：[`expectation/symbol_variable/symbol_dim.py`](../../expectation/symbol_variable/symbol_dim.py)
- 执行命令：
  - `pytest -q test/symbol_variable/test_symbol_dim.py`
  - `python expectation/symbol_variable/symbol_dim.py`

### 测试目标

- 保持现有构造、比较、动态性判断与错误分支的回归覆盖。
- 补齐静态整数、动态符号与混合表达式在 `+`、`-`、`*`、`/`、`//` 下的目标行为。
- 补齐浮点构造与浮点算术操作数必须抛出 `NotImplementedError` 的错误路径。
- 验证 `get_value()` 的公开返回语义满足 expectation：静态值可与 Python 结果直接比较，动态表达式可稳定比较。
- 明确 [`expectation/symbol_variable/symbol_dim.py`](../../expectation/symbol_variable/symbol_dim.py) 保持只读；后续实现阶段以该脚本运行成功作为 acceptance gate。

### 功能与用例清单

- SD-001：`int` 输入可构造 `SymbolDim`。（`test_init_accepts_int`）
- SD-002：非纯数字字符串符号输入可构造 `SymbolDim`。（`test_init_accepts_symbol_string`）
- SD-003：`sympy.Basic` 输入可构造 `SymbolDim`。（`test_init_accepts_sympy_basic`）
- SD-004：基础算术 `+`、`-`、`*`、`/` 与反向运算返回 `SymbolDim`。（`test_arithmetic_ops`）
- SD-005：等价比较返回 `bool`。（`test_equality`）
- SD-006：`is_dynamic()` 能区分静态整数与动态符号。（`test_is_dynamic`）
- SD-007：纯数字字符串输入与操作数抛出 `ValueError`。（`test_numeric_string_rejected`）
- SD-008：空白字符串输入与操作数抛出 `ValueError`。（`test_blank_string_rejected`）
- SD-009：非浮点非法类型输入与比较抛出 `TypeError`。（`test_invalid_type_rejected`）
- SD-010：静态整数之间的 `+/-/*` 结果保持非动态，`get_value()` 与 Python 运算结果一致。（`test_static_arithmetic_get_value_semantics`）
- SD-011：静态整数与动态符号混合参与 `+/-/*` 时，结果保持动态，链式运算顺序可稳定比较。（`test_dynamic_mixed_add_sub_mul_semantics`）
- SD-012：静态整数真除法 `a / b` 的结果可由 `get_value()` 直接与 Python `/` 结果比较；含符号真除法保持动态并保留结合顺序。（`test_truediv_get_value_and_order_semantics`）
- SD-013：静态整数整除 `a // b` 的结果可由 `get_value()` 直接与 Python `//` 结果比较；含符号整除保持动态并保留结合顺序。（`test_floordiv_get_value_and_order_semantics`）
- SD-014：混合表达式 `static + symbol - static * symbol / static` 的动态性传播与 `get_value()` 表达式比较稳定。（`test_mixed_expression_get_value_semantics`）
- SD-015：浮点构造输入必须抛出 `NotImplementedError`。（`test_float_constructor_rejected`）
- SD-016：浮点算术操作数在 `+`、`-`、`*`、`/`、`//` 中必须抛出 `NotImplementedError`。（`test_float_operands_rejected`）
