# symbol_dim.md

用于定义 `SymbolDim` 的开发者设计规范。`SymbolDim` 是维度表达的统一入口，既支持静态整数维度，也支持基于符号的动态维度。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`榕`
- `spec`：[`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)
- `test`：[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)
- `功能实现`：[`python/symbol_variable/symbol_dim.py`](../../python/symbol_variable/symbol_dim.py)

## 范围与目标

- 统一输入规整：`int`、合法 `str`、`sympy.Basic`。
- 统一表达与运算：支持基础算术、相等比较、动态性判断。
- 保持 `sympy` 语义，不引入额外化简或求解。
- 不负责广播、约束求解、形状推导或高阶语义。

## 依赖约定

- `sympy`：符号与表达式构造。

## 术语

- 静态维度：由整数表示的维度。
- 动态维度：表达式包含自由符号的维度。
- 纯数字字符串：对输入字符串执行 `strip()` 后结果非空且 `isdigit()` 为 `True` 的字符串，例如 `"12"`、`" 12 "`、`"001"`、`"１２"`、`"٠١٢"`。

## 兼容性与边界

- 公共构造入口仅为 `SymbolDim(value)`。
- 纯数字字符串与空白字符串继续拒绝，异常类型为 `ValueError`。
- 非纯数字字符串继续作为符号名处理（例如 `"+1"`、`"-1"`、`"3.14"`）。
- `sympy.Symbol` 若未显式设置 `is_integer/is_real`，需统一规范化为 `integer=True, real=True`。
- 不提供旧路径 `symbol_variable.symbol_dim` 的 compat 转发模块。

## 输入规整规则

### 合法输入

- `int`：转为 `sympy.Integer`。
- `sympy.Basic`：直接接收；若为未设定整数/实数假设的 `sympy.Symbol`，按名称规范化为 `integer=True, real=True`。
- `str`：仅当非空白且非纯数字字符串时合法，按 `sympy.symbols(..., integer=True, real=True)` 构造。

### 非法输入

- 纯数字字符串：抛 `ValueError`。
- 空白字符串：抛 `ValueError`。
- 不支持的其他类型：抛 `TypeError`。

## 公开 API

### `SymbolDim(value)`

功能说明：

- 统一的公开构造入口。

示例：

```python
from python.symbol_variable.symbol_dim import SymbolDim
import sympy as sp

SymbolDim(32)
SymbolDim("N")
SymbolDim(sp.Symbol("M"))
```

### `get_symbol()`

功能说明：

- 返回内部 `sympy` 表达式。

示例：

```python
from python.symbol_variable.symbol_dim import SymbolDim

dim = SymbolDim("N")
sym = dim.get_symbol()
```

### `__repr__()`

功能说明：

- 返回 `str(get_symbol())`。

示例：

```python
from python.symbol_variable.symbol_dim import SymbolDim

assert repr(SymbolDim("N")) == "N"
```

### `__add__ / __radd__`

功能说明：

- 符号加法，返回 `SymbolDim`。

示例：

```python
from python.symbol_variable.symbol_dim import SymbolDim

SymbolDim("N") + 2
2 + SymbolDim("N")
```

### `__sub__ / __rsub__`

功能说明：

- 符号减法，返回 `SymbolDim`。

示例：

```python
from python.symbol_variable.symbol_dim import SymbolDim

SymbolDim("N") - "M"
10 - SymbolDim("N")
```

### `__mul__ / __rmul__`

功能说明：

- 符号乘法，返回 `SymbolDim`。

示例：

```python
from python.symbol_variable.symbol_dim import SymbolDim

SymbolDim("N") * 4
4 * SymbolDim("N")
```

### `__truediv__ / __rtruediv__`

功能说明：

- 符号除法，返回 `SymbolDim`。

示例：

```python
from python.symbol_variable.symbol_dim import SymbolDim

SymbolDim("N") / 2
"K" / SymbolDim("N")
```

### `__eq__`

功能说明：

- 比较底层 `sympy` 表达式等价性，返回 `bool`。

示例：

```python
from python.symbol_variable.symbol_dim import SymbolDim

assert SymbolDim(4) == 4
assert SymbolDim("N") == "N"
assert SymbolDim("N") == SymbolDim("N")
```

### `is_dynamic()`

功能说明：

- 当表达式包含自由符号时返回 `True`。

示例：

```python
from python.symbol_variable.symbol_dim import SymbolDim

assert SymbolDim(8).is_dynamic() is False
assert SymbolDim("N").is_dynamic() is True
```

## 内部实现约束

### `_normalize_str(value)`

- `strip()` 后为空抛 `ValueError`。
- 纯数字字符串抛 `ValueError`。
- 其余字符串返回规整后的符号名。

示例：

```python
from python.symbol_variable.symbol_dim import _SymbolDim

_SymbolDim._normalize_str(" N ")
```

### `_symbol_from_str(value)`

- 统一按 `sympy.symbols(value, integer=True, real=True)` 构造。

示例：

```python
from python.symbol_variable.symbol_dim import _SymbolDim

_SymbolDim._symbol_from_str("N")
```

### `_normalize_symbol(sym)`

- 若 `sym` 为 `sympy.Symbol` 且 `is_integer/is_real` 均为 `None`，需按名称规范化为 `integer=True, real=True`。

示例：

```python
import sympy as sp
from python.symbol_variable.symbol_dim import _SymbolDim

_SymbolDim._normalize_symbol(sp.Symbol("N"))
```

### `_normalize_operand(value)`

- 统一规整算术与比较操作数，规则与构造一致。

示例：

```python
from python.symbol_variable.symbol_dim import _SymbolDim

_SymbolDim._normalize_operand(4)
_SymbolDim._normalize_operand("M")
```

## 错误与异常

- 构造或运算遇到非法类型：`TypeError`。
- 构造或运算遇到纯数字字符串或空白字符串：`ValueError`。
- 异常消息文本不是兼容承诺，兼容性只要求异常类型稳定。

## 测试

- 测试文件：[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)
- 执行命令：`pytest -q test/symbol_variable/test_symbol_dim.py`

### 测试目标

- 覆盖构造、运算、比较、动态性判断与错误分支。
- 验证字符串规整规则在构造与运算入口一致。
- 验证 `sympy.Symbol` 的假设规范化策略。

### 测试清单

| 用例 ID | 约束点 | 对应测试 |
| --- | --- | --- |
| SD-001 | 构造支持 `int/str/sympy.Basic` | `test_init_accepts_int_str_sympy` |
| SD-002 | 构造拒绝纯数字字符串 | `test_init_rejects_numeric_string` |
| SD-017 | 构造拒绝空白字符串 | `test_init_rejects_blank_string` |
| SD-003 | 基础算术运算 | `test_arithmetic_ops` |
| SD-012 | 运算拒绝纯数字/空白字符串 | `test_arithmetic_rejects_numeric_string` |
| SD-004 | 反向算术运算 | `test_reverse_arithmetic_ops` |
| SD-005 | 动态性判断与构造入口 | `test_dynamic_and_construct` |
| SD-006 | 相等比较 | `test_equality` |
| SD-013 | 比较拒绝纯数字/空白字符串 | `test_compare_rejects_numeric_string` |
| SD-009 | 字符串操作数规整 | `test_string_operand_unification` |
| SD-015 | 非纯数字字符串兼容 | `test_non_numeric_string_allowed` |
| SD-010 | 无显式假设的 `sympy.Symbol` 规范化 | `test_symbol_without_assumption_normalized` |
| SD-011 | 有显式假设的 `sympy.Symbol` 保持原样 | `test_symbol_with_assumption_kept` |
| SD-007 | 非法类型错误 | `test_invalid_types_raise` |
| SD-008 | `get_symbol` 与 `repr` 一致性 | `test_get_symbol_and_repr` |
