# symbol_dim.md

## 功能简介

[immutable]用于定义 `SymbolDim` 的开发者设计规范。`SymbolDim` 是维度表达的统一入口，既支持静态整数维度，也支持基于符号的动态维度。

## API 列表

- `SymbolDim(value)`
- `get_symbol()`
- `get_value()`
- `__repr__()`
- `__add__() / __radd__()`
- `__sub__() / __rsub__()`
- `__mul__() / __rmul__()`
- `__truediv__() / __rtruediv__()`
- `__floordiv__() / __rfloordiv__()`
- `__eq__(other)`
- `is_dynamic()`

## 文档信息

- `spec`：[`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)
- `功能实现`：[`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py)
- `test`：[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)

## 依赖

- `sympy`：负责静态整数、符号与混合表达式的底层表示。
- [`spec/symbol_variable/__init__.md`](../../spec/symbol_variable/__init__.md)：包级导入边界来源。

## 目标

- 提供统一的 `SymbolDim(value)` 公开入口，覆盖静态整数、动态符号与整数表达式。
- 明确字符串输入域：`int` 合法，按符号名语义规整后的 `str` 合法，数值字面量字符串非法。
- 明确 `get_symbol()` 与 `get_value()` 的职责分层：前者暴露内部 `sympy.Basic` 表达式，后者暴露稳定的公开比较值。
- 明确 `+`、`-`、`*`、`/`、`//` 在静态值、动态值、可约表达式、链式除法与链式整除下的公开行为，为实现与测试同步收口提供直接依据。

## API详细说明

### `SymbolDim(value)`

- api：`SymbolDim(value)`
- 参数：
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `int | str | Expr | Symbol`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
- 返回值：`SymbolDim` 实例。
- 使用示例：

  ```python
  symbol_dim = SymbolDim(value=sample_value)
  ```
- 功能说明：构造 `SymbolDim` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `get_symbol()`

- api：`get_symbol()`
- 参数：无。
- 返回值：`get_symbol` 的公开结果值。
- 使用示例：

  ```python
  result = get_symbol()
  ```
- 功能说明：读取 `symbol`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。

### `get_value()`

- api：`get_value()`
- 参数：无。
- 返回值：`get_value` 的公开结果值。
- 使用示例：

  ```python
  result = get_value()
  ```
- 功能说明：读取 `value`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。

### `__repr__()`

- api：`__repr__()`
- 参数：无。
- 返回值：`__repr__` 的公开结果值。
- 使用示例：

  ```python
  result = __repr__()
  ```
- 功能说明：返回调试表示文本。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `__add__() / __radd__()`

- api：`__add__() / __radd__()`
- 参数：无。
- 返回值：`__add__` 的公开结果值。
- 使用示例：

  ```python
  result = __add__()
  ```
- 功能说明：执行 `__add__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `__sub__() / __rsub__()`

- api：`__sub__() / __rsub__()`
- 参数：无。
- 返回值：`__sub__` 的公开结果值。
- 使用示例：

  ```python
  result = __sub__()
  ```
- 功能说明：执行 `__sub__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `__mul__() / __rmul__()`

- api：`__mul__() / __rmul__()`
- 参数：无。
- 返回值：`__mul__` 的公开结果值。
- 使用示例：

  ```python
  result = __mul__()
  ```
- 功能说明：执行 `__mul__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `__truediv__() / __rtruediv__()`

- api：`__truediv__() / __rtruediv__()`
- 参数：无。
- 返回值：`__truediv__` 的公开结果值。
- 使用示例：

  ```python
  result = __truediv__()
  ```
- 功能说明：执行 `__truediv__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `__floordiv__() / __rfloordiv__()`

- api：`__floordiv__() / __rfloordiv__()`
- 参数：无。
- 返回值：`__floordiv__` 的公开结果值。
- 使用示例：

  ```python
  result = __floordiv__()
  ```
- 功能说明：执行 `__floordiv__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `__eq__(other)`

- api：`__eq__(other)`
- 参数：
  - `other`：另一侧操作数或比较对象，用于和当前对象组合、比较或广播；类型 `int | str | Expr | Symbol | SymbolDim`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
- 返回值：`__eq__` 的公开结果值。
- 使用示例：

  ```python
  result = __eq__(other=sample_other)
  ```
- 功能说明：执行 `__eq__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `is_dynamic()`

- api：`is_dynamic()`
- 参数：无。
- 返回值：`is_dynamic` 的公开结果值。
- 使用示例：

  ```python
  result = is_dynamic()
  ```
- 功能说明：执行 `is_dynamic`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。


## 额外补充

### 公开接口

#### 补充：`SymbolDim(value)`

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
- 非法输入按对应 API `注意事项` 中的异常类型处理。

#### 补充：`get_symbol()`

功能说明：

- 返回内部 `sympy.Basic` 表达式，供实现和测试读取当前规整结果。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

A = SymbolDim("A")
B = SymbolDim("B")

assert str((A + A).get_symbol()) == "2*A"
assert (A / A).get_symbol() == 1
assert str((A / B / 3).get_symbol()) == "(A/B)/3"
assert str((A // B // 3).get_symbol()) == "floor(floor(A/B)/3)"
```

注意事项：

- 返回值始终是 `sympy.Basic`。
- 该接口体现内部表达而不是最终公开文本。
- 显然更短的可约结果直接以简化后的内部表达返回，例如 `A / A -> 1`、`(A*B) / B -> A`、`(A*3) // 3 -> A`。
- 顺序敏感的链式真除法与整除仍需保留内部结构差异，例如 `(A/B)/3` 与 `(A/3)/B` 不得收成同一内部表达。

返回与限制：

- 返回 `sympy.Basic`。

#### 补充：`get_value()`

功能说明：

- 返回用于对外机械比较的当前值。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

A = SymbolDim("A")
B = SymbolDim("B")

assert SymbolDim(8).get_value() == 8
assert (A + A).get_value() == "2*A"
assert (A / A).get_value() == 1
assert (A / B / 3).get_value() == "A/(3*B)"
assert (A / 3 / B).get_value() == "A/(B*3)"
assert (A // B // 3).get_value() == "floor(floor(A/B)/3)"
```

注意事项：

- 静态表达式必须返回可与 Python 对应结果直接比较的具体值。
- 动态加、减、乘与其他非链式真除法表达式返回 `str(sp.simplify(expr))` 对应的稳定文本。
- 动态真除法链需要把分母按出现顺序重组为右侧乘积文本，以保持 `(A/B)/3` 与 `(A/3)/B` 的公开值可区分。
- 动态整除链必须保留嵌套 `floor(...)` 的顺序，例如 `floor(floor(A/B)/3)` 与 `floor(floor(A/3)/B)` 不得混同。
- 若结果已经化简为静态值或单个动态符号，直接返回该值对应的 `int`、`float` 或 `str`，不再保留冗余表达式文本。

返回与限制：

- 返回 `int | float | str`；动态表达式不返回 `sympy.Basic`。

#### 补充：`__repr__()`

功能说明：

- 返回当前内部表达式的字符串表示。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

A = SymbolDim("A")
B = SymbolDim("B")

assert repr(SymbolDim("N")) == "N"
assert repr(A / B / 3) == "(A/B)/3"
```

注意事项：

- 输出等于 `str(get_symbol())`。
- 当 `get_symbol()` 与 `get_value()` 的职责不同步时，`__repr__()` 以内部表达为准；例如 `repr(A / B / 3)` 与 `(A / B / 3).get_value()` 的文本可以不同。

返回与限制：

- 返回 `str`。

#### 补充：`__add__() / __radd__()`

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
- `A + A` 的内部表达与公开值都应表现为 `2*A`，`A + 0` 的内部表达与公开值都应表现为 `A`。
- 浮点操作数必须抛出 `NotImplementedError`。

返回与限制：

- 返回 `SymbolDim`。

#### 补充：`__sub__() / __rsub__()`

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

- 结果动态性遵循对应 API `注意事项` 中的传播规则。
- `str` 操作数复用构造路径的字符串词法校验；数值字面量字符串必须抛出 `ValueError`。
- `A - A` 的内部表达与公开值都应表现为 `0`。
- 链式减法的公开值使用 `str(sp.simplify(expr))` 对应的稳定文本。
- 浮点操作数必须抛出 `NotImplementedError`。

返回与限制：

- 返回 `SymbolDim`。

#### 补充：`__mul__() / __rmul__()`

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

- 结果动态性遵循对应 API `注意事项` 中的传播规则。
- `str` 操作数复用构造路径的字符串词法校验；数值字面量字符串必须抛出 `ValueError`。
- `A * 1` 的内部表达与公开值都应表现为 `A`。
- 浮点操作数必须抛出 `NotImplementedError`。

返回与限制：

- 返回 `SymbolDim`。

#### 补充：`__truediv__() / __rtruediv__()`

功能说明：

- 执行整数符号真除法并返回新的 `SymbolDim`。

参数说明：

- `other`（`int | str | sympy.Basic | SymbolDim`）：右操作数或左操作数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

A = SymbolDim("A")
B = SymbolDim("B")

assert str((A / B / 3).get_symbol()) == "(A/B)/3"
assert (A / B / 3).get_value() == "A/(3*B)"
assert (A / A).get_value() == 1
```

注意事项：

- 静态整数之间的真除法结果必须可通过 `get_value()` 与 Python `/` 结果直接比较。
- 动态真除法在内部表达上保留顺序敏感的链式结构，在公开值上给出可区分且稳定的文本。
- 当 `sp.simplify(...)` 能把结果收成更短的表达式或静态值时，内部表达可以直接采用简化结果，例如 `A / A -> 1`、`(A*B) / B -> A`、`(A*3) / 3 -> A`。
- `str` 操作数复用构造路径的字符串词法校验；数值字面量字符串必须抛出 `ValueError`。
- 浮点操作数必须抛出 `NotImplementedError`。

返回与限制：

- 返回 `SymbolDim`。

#### 补充：`__floordiv__() / __rfloordiv__()`

功能说明：

- 执行整数符号整除并返回新的 `SymbolDim`。

参数说明：

- `other`（`int | str | sympy.Basic | SymbolDim`）：右操作数或左操作数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

A = SymbolDim("A")
B = SymbolDim("B")

assert str((A // B // 3).get_symbol()) == "floor(floor(A/B)/3)"
assert (A // B // 3).get_value() == "floor(floor(A/B)/3)"
assert (A // A).get_value() == 1
```

注意事项：

- 静态整数之间的整除结果必须可通过 `get_value()` 与 Python `//` 结果直接比较。
- 动态整除在内部表达与公开值上都必须保留嵌套 `floor(...)` 的顺序信息。
- 当结果能直接约为更短的表达式或静态值时，内部表达与公开值都可以直接表现为该结果，例如 `A // A -> 1`、`(A*B) // B -> A`、`(A*3) // 3 -> A`。
- `str` 操作数复用构造路径的字符串词法校验；数值字面量字符串必须抛出 `ValueError`。
- 浮点操作数必须抛出 `NotImplementedError`。

返回与限制：

- 返回 `SymbolDim`。

#### 补充：`__eq__(other)`

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

#### 补充：`is_dynamic()`

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

- [`spec/symbol_variable/__init__.md`](../../spec/symbol_variable/__init__.md) 负责包级导入边界；本文件只定义 `SymbolDim` 对象本身的构造、算术、比较与动态性语义。
- [`spec/symbol_variable/symbol_shape.md`](../../spec/symbol_variable/symbol_shape.md) 负责多个 `SymbolDim` 的容器行为；本文件不定义切片、索引赋值或列表序列化。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md) 负责 `Memory` 如何消费 `SymbolDim` 组成的 `shape/stride`；本文件不定义 `Memory` 的 dtype、space、format 或默认 stride 生成。

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
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
- `get_symbol()` 返回内部 `sympy.Basic` 表达式：
  - 加、减、乘与显然更短的可约除法/整除结果可以直接以简化后的内部表达出现，例如 `A + A -> 2*A`、`A - A -> 0`、`A / A -> 1`、`(A*B) / B -> A`、`(A*3) // 3 -> A`。
  - 顺序敏感的链式真除法与整除在内部表达上仍需保持可区分性，例如 `(A / B) / 3` 与 `(A / 3) / B` 必须保留不同的 `sympy.Basic` 结构，`A // B // 3` 与 `A // 3 // B` 也必须保留不同的嵌套 `floor(...)` 结构。
- `get_value()` 的公开返回值为 `int | float | str`：
  - 静态表达式返回可直接与 Python 运算结果比较的具体值。
  - 动态加、减、乘与其他非链式真除法表达式返回 `str(sp.simplify(expr))` 对应的稳定文本。
  - 动态真除法链返回保持顺序可区分的公开文本，例如 `A / B / 3 -> "A/(3*B)"`，`A / 3 / B -> "A/(B*3)"`。
  - 动态整除链保持嵌套 `floor(...)` 的顺序信息，例如 `A // B // 3 -> "floor(floor(A/B)/3)"`，`A // 3 // B -> "floor(floor(A/3)/B)"`。
  - 若结果已经化简为静态值或单个动态符号，公开结果直接返回该值对应的 `int`、`float` 或 `str`，例如 `A / A -> 1`、`(A*B) / B -> "A"`。
- `__repr__()` 返回 `str(get_symbol())`，因此它描述的是内部表达，不承诺与 `get_value()` 完全相同。
- `sympy.Symbol` 若未显式声明整数假设，实现需统一为整数语义。
- 不额外承诺异常消息文本；兼容性只要求异常类型与公开行为稳定。
## 测试

- 测试文件：[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)
- 执行命令：`pytest -q test/symbol_variable/test_symbol_dim.py`
- 测试目标：保持输入域、动态性、异常分支回归覆盖，并锁定 `get_symbol()` 与 `get_value()` 在静态值、可约表达式、链式真除法、链式整除下的公开行为。
- 功能与用例清单：
  - `test_init_accepts_int`：验证 `int` 输入可构造 `SymbolDim`，且保持静态值语义。
  - `test_init_accepts_symbol_string`：验证符号名字符串在 `strip()` 后可构造 `SymbolDim`，并返回规整后的公开值。
  - `test_init_accepts_sympy_basic`：验证 `sympy.Basic` 输入可构造 `SymbolDim`，且自由符号统一为整数语义。
  - `test_arithmetic_ops`：验证 `+`、`-`、`*`、`/`、`//` 及反向运算返回 `SymbolDim`。
  - `test_equality`：验证 `__eq__()` 对 `int`、`str`、`sympy.Basic`、`SymbolDim` 的公开比较行为。
  - `test_is_dynamic`：验证 `is_dynamic()` 能区分静态整数与动态符号。
  - `test_numeric_string_rejected`：验证数值字面量字符串在构造、操作数、比较路径上均抛出 `ValueError`。
  - `test_blank_string_rejected`：验证空字符串与空白字符串在构造、操作数、比较路径上均抛出 `ValueError`。
  - `test_invalid_type_rejected`：验证除浮点外的其他非法类型在构造、操作数、比较路径上抛出 `TypeError`。
  - `test_static_arithmetic_get_value_semantics`：验证静态整数之间的 `+`、`-`、`*`、`/`、`//` 结果保持非动态，且 `get_value()` 可直接与 Python 结果比较。
  - `test_dynamic_mixed_add_sub_mul_semantics`：验证动态加、减、乘及链式减法在 `get_value()` 上的稳定文本。
  - `test_truediv_get_value_and_order_semantics`：验证真除法的内部表达、公开值、同项约分与链式顺序区分。
  - `test_floordiv_get_value_and_order_semantics`：验证整除的内部表达、公开值、同项约分与嵌套 `floor(...)` 顺序区分。
  - `test_mixed_expression_get_value_semantics`：验证混合表达式的动态性传播与 `get_value()` 稳定性。
  - `test_float_constructor_rejected`：验证浮点构造输入抛出 `NotImplementedError`。
  - `test_float_operands_rejected`：验证浮点算术操作数在正向/反向路径上抛出 `NotImplementedError`。
