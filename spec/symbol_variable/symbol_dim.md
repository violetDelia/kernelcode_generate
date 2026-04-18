# symbol_dim.md

## 功能简介

[immutable]用于定义 `SymbolDim` 的开发者设计规范。`SymbolDim` 是维度表达的统一入口，既支持静态整数维度，也支持基于符号的动态维度。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)
- `功能实现`：[`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py)
- `test`：[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)

## 依赖

- `sympy`：负责静态整数、符号与混合表达式的底层表示。
- [`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md)：包级导入边界来源。

## 目标

- 提供统一的 `SymbolDim(value)` 公开入口，覆盖静态整数、动态符号与整数表达式。
- 冻结字符串输入域合同：`int` 合法，按符号名语义规整后的 `str` 合法，数值字面量字符串非法。
- 明确构造、算术操作数、比较操作数三条路径共用同一套字符串词法校验。
- 保持现有公开 API 名称与参数顺序不变，为实现与测试同步收口提供直接依据。

## 限制与边界

- `SymbolDim` 只表示整数维度及其整型符号表达，不负责广播、约束求解、形状推导或高阶张量语义。
- 公开接口限定为 `SymbolDim(value)`、`get_symbol()`、`get_value()`、`is_dynamic()`、`__repr__()`、`__eq__()`，以及 `+`、`-`、`*`、`/`、`//` 对应的正向/反向运算；不新增其他对外入口。
- 构造输入仅允许：
  - `int`：表示静态整数维度。
  - `str`：表示符号名；字符串执行 `strip()` 后不能为空，且不能是数值字面量字符串。
  - `sympy.Basic`：表示已构造好的整数符号或整数表达式。
- 数值字面量字符串包括但不限于 `"12"`、`"3.14"`、`".5"`、`"1e3"`、`"+1"`、`"-2"`；这些输入在构造、算术操作数、比较操作数路径上都必须抛出 `ValueError`。
- 空字符串或仅空白字符串在构造、算术操作数、比较操作数路径上都必须抛出 `ValueError`。
- 浮点构造输入与浮点算术操作数均不受支持：
  - `SymbolDim(1.5)` 必须抛出 `NotImplementedError`。
  - `SymbolDim(...)+1.5`、`-1.5`、`*1.5`、`/1.5`、`//1.5` 及对应反向运算必须抛出 `NotImplementedError`。
- 除浮点外的其他非法类型必须抛出 `TypeError`。
- 动态性判断以表达式是否含自由符号为准：
  - 静态整数输入、静态整数之间的 `+`、`-`、`*`、`/`、`//` 结果必须保持 `is_dynamic() == False`。
  - 只要任一操作数含自由符号，结果必须保持 `is_dynamic() == True`。
- `get_symbol()` 返回内部规整后的 `sympy.Basic` 表达式。
- `get_value()` 的公开返回值为 `int | float | str`：
  - 静态表达式返回可直接与 Python 运算结果比较的具体值。
  - 动态表达式返回稳定、可机械比较的字符串表示，不暴露 `sympy` 内部对象类型。
- `sympy.Symbol` 若未显式声明整数假设，实现需统一为整数语义。
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

SymbolDim(12)
SymbolDim(" N ")
SymbolDim(sp.Symbol("M", integer=True, real=True) + 1)
```

注意事项：

- `SymbolDim(12)` 合法，但 `SymbolDim("12")` 非法。
- `"3.14"`、`".5"`、`"1e3"`、`"+1"`、`"-2"`、`""`、`"   "` 必须抛出 `ValueError`。
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

expr = SymbolDim(" N ").get_symbol()
```

注意事项：

- 返回值始终是 `sympy.Basic`。
- 该接口用于实现与测试读取标准化表达，不替代 `get_value()` 的对外比较语义。

返回与限制：

- 返回 `sympy.Basic`。

### `get_value()`

功能说明：

- 返回用于公开比较的当前值。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

assert SymbolDim(8).get_value() == 8
assert SymbolDim(" N ").get_value() == "N"
```

注意事项：

- 静态表达式必须返回可与 Python 对应结果直接比较的具体值。
- 动态表达式必须返回 `str`，作为公开机械比较口径；调用方不得依赖 `sympy` 内部对象类型。

返回与限制：

- 返回 `int | float | str`；动态表达式不返回 `sympy.Basic`。

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
- `str` 操作数复用构造路径的字符串词法校验；数值字面量字符串必须抛出 `ValueError`。
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
- `str` 操作数复用构造路径的字符串词法校验；数值字面量字符串必须抛出 `ValueError`。
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
- `str` 操作数复用构造路径的字符串词法校验；数值字面量字符串必须抛出 `ValueError`。
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
- 含符号的真除法结果必须保持动态。
- `str` 操作数复用构造路径的字符串词法校验；数值字面量字符串必须抛出 `ValueError`。
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
- 含符号的整除结果必须保持动态。
- `str` 操作数复用构造路径的字符串词法校验；数值字面量字符串必须抛出 `ValueError`。
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
- `str` 比较对象复用构造路径的字符串词法校验；数值字面量字符串必须抛出 `ValueError`。
- `__eq__()` 的对外语义是表达式等价比较，不替代 `get_value()` 的机械字符串比较合同。
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

## 额外补充

- [`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md) 负责包级导入边界；本文件只定义 `SymbolDim` 对象本身的构造、算术、比较与动态性语义。
- [`spec/symbol_variable/symbol_shape.md`](../../spec/symbol_variable/symbol_shape.md) 负责多个 `SymbolDim` 的容器行为；本文件不定义切片、索引赋值或列表序列化。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md) 负责 `Memory` 如何消费 `SymbolDim` 组成的 `shape/stride`；本文件不定义 `Memory` 的 dtype、space、format 或默认 stride 生成。

## 测试

- 测试文件：[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)
- 执行命令：`pytest -q test/symbol_variable/test_symbol_dim.py`
- 测试目标：锁定构造输入域、算术操作数与比较路径的字符串词法边界，并保持基础动态性、算术与错误分支回归覆盖。
- 功能与用例清单：
  - `test_init_accepts_int`：验证 `int` 输入可构造 `SymbolDim`，且保持静态值语义。
  - `test_init_accepts_symbol_string`：验证符号名字符串在 `strip()` 后可构造 `SymbolDim`，并返回规整后的公开值。
  - `test_init_accepts_sympy_basic`：验证 `sympy.Basic` 输入可构造 `SymbolDim`，且自由符号统一为整数语义。
  - `test_arithmetic_ops`：验证 `+`、`-`、`*`、`/`、`//` 及反向运算返回 `SymbolDim`。
  - `test_equality`：验证 `__eq__()` 对 `int`、`str`、`sympy.Basic`、`SymbolDim` 的公开比较行为。
  - `test_is_dynamic`：验证 `is_dynamic()` 能区分静态整数与动态符号。
  - `test_numeric_string_rejected`：验证 `"12"`、`"3.14"`、`".5"`、`"1e3"`、`"+1"`、`"-2"` 在构造、操作数、比较路径上均抛出 `ValueError`；若现有测试未覆盖，执行者需补齐。
  - `test_blank_string_rejected`：验证空字符串与空白字符串在构造、操作数、比较路径上均抛出 `ValueError`。
  - `test_invalid_type_rejected`：验证除浮点外的其他非法类型在构造、操作数、比较路径上抛出 `TypeError`。
  - `test_float_constructor_rejected`：验证浮点构造输入抛出 `NotImplementedError`；若现有测试未覆盖，执行者需补齐。
  - `test_float_operands_rejected`：验证浮点算术操作数在正向/反向路径上抛出 `NotImplementedError`；若现有测试未覆盖，执行者需补齐。
