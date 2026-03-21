# symbol_dim.md

## 功能简介

[immutable]用于定义 `SymbolDim` 的开发者设计规范。`SymbolDim` 是维度表达的统一入口，既支持静态整数维度，也支持基于符号的动态维度。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)
- `功能实现`：[`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py)
- `test`：[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)

## 依赖

- `sympy`：符号与表达式构造。

## 术语

- 静态维度：由整数表示的维度。
- 动态维度：表达式包含自由符号的维度。
- 纯数字字符串：对输入字符串执行 `strip()` 后结果非空且 `isdigit()` 为 `True` 的字符串，例如 `"12"`、`" 12 "`、`"001"`、`"１２"`、`"٠١٢"`。

## 目标

- 统一输入规整：`int`、合法 `str`、`sympy.Basic`。
- 统一表达与运算：支持基础算术、相等比较、动态性判断。
- 保持 `sympy` 语义，不引入额外化简或求解。
- 不负责广播、约束求解、形状推导或高阶语义。

## 限制与边界

- 公共构造入口仅为 `SymbolDim(value)`。
- 纯数字字符串与空白字符串继续拒绝，异常类型为 `ValueError`。
- 非纯数字字符串继续作为符号名处理（例如 `"+1"`、`"-1"`、`"3.14"`）。
- `sympy.Symbol` 若未显式设置 `is_integer/is_real`，需统一规范化为 `integer=True, real=True`。

## 公开接口

### `SymbolDim(value)`

功能说明：

- 统一的公开构造入口。

参数说明：

- `value` (`int|str|sympy.Basic`): 输入维度。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
import sympy as sp

SymbolDim(32)
SymbolDim("N")
SymbolDim(sp.Symbol("M"))
```

注意事项：

- 纯数字字符串与空白字符串不被接受。

返回与限制：

- 返回 `SymbolDim` 实例。
- 非法输入抛出 `TypeError` 或 `ValueError`。

### `get_symbol()`

功能说明：

- 返回内部 `sympy` 表达式。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

dim = SymbolDim("N")
sym = dim.get_symbol()
```

注意事项：

- 返回类型为 `sympy.Basic`。

返回与限制：

- 返回 `sympy.Basic`。

### `__repr__()`

功能说明：

- 返回 `str(get_symbol())`。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

assert repr(SymbolDim("N")) == "N"
```

注意事项：

- 输出字符串由 `sympy` 表达式决定。

返回与限制：

- 返回 `str`。

### `__add__ / __radd__`

功能说明：

- 符号加法，返回 `SymbolDim`。

参数说明：

- `other` (`int|str|sympy.Basic|SymbolDim`): 右操作数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

SymbolDim("N") + 2
2 + SymbolDim("N")
```

注意事项：

- 操作数规整规则与构造一致。

返回与限制：

- 返回 `SymbolDim`。

### `__sub__ / __rsub__`

功能说明：

- 符号减法，返回 `SymbolDim`。

参数说明：

- `other` (`int|str|sympy.Basic|SymbolDim`): 右操作数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

SymbolDim("N") - "M"
10 - SymbolDim("N")
```

注意事项：

- 操作数规整规则与构造一致。

返回与限制：

- 返回 `SymbolDim`。

### `__mul__ / __rmul__`

功能说明：

- 符号乘法，返回 `SymbolDim`。

参数说明：

- `other` (`int|str|sympy.Basic|SymbolDim`): 右操作数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

SymbolDim("N") * 4
4 * SymbolDim("N")
```

注意事项：

- 操作数规整规则与构造一致。

返回与限制：

- 返回 `SymbolDim`。

### `__truediv__ / __rtruediv__`

功能说明：

- 符号除法，返回 `SymbolDim`。

参数说明：

- `other` (`int|str|sympy.Basic|SymbolDim`): 右操作数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

SymbolDim("N") / 2
"K" / SymbolDim("N")
```

注意事项：

- 操作数规整规则与构造一致。

返回与限制：

- 返回 `SymbolDim`。

### `__eq__`

功能说明：

- 比较底层 `sympy` 表达式等价性，返回 `bool`。

参数说明：

- `other` (`int|str|sympy.Basic|SymbolDim`): 右操作数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

assert SymbolDim(4) == 4
assert SymbolDim("N") == "N"
assert SymbolDim("N") == SymbolDim("N")
```

注意事项：

- 操作数规整规则与构造一致；非法输入继续抛 `TypeError` 或 `ValueError`。

返回与限制：

- 返回 `bool`。

### `is_dynamic()`

功能说明：

- 当表达式包含自由符号时返回 `True`。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

assert SymbolDim(8).is_dynamic() is False
assert SymbolDim("N").is_dynamic() is True
```

注意事项：

- 以 `sympy` 自由符号判断为准。

返回与限制：

- 返回 `bool`。

## 额外补充

- 合法输入：
  - `int`：转为 `sympy.Integer`。
  - `sympy.Basic`：直接接收；若为未设定整数/实数假设的 `sympy.Symbol`，按名称规范化为 `integer=True, real=True`。
  - `str`：仅当非空白且非纯数字字符串时合法，按 `sympy.symbols(..., integer=True, real=True)` 构造。
- 非法输入：
  - 纯数字字符串：抛 `ValueError`。
  - 空白字符串：抛 `ValueError`。
  - 不支持的其他类型：抛 `TypeError`。
- `_normalize_str(value)`：`strip()` 后为空或纯数字字符串抛 `ValueError`，其余字符串返回规整后的符号名。
- `_symbol_from_str(value)`：按 `sympy.symbols(value, integer=True, real=True)` 构造。
- `_normalize_symbol(sym)`：若 `sympy.Symbol` 未设置 `is_integer/is_real`，按名称规范化为 `integer=True, real=True`。
- `_normalize_operand(value)`：统一规整算术与比较操作数，规则与构造一致。
- 异常消息文本不作为兼容承诺，兼容性仅要求异常类型稳定。

## 测试

- 测试文件：[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)
- 执行命令：`pytest -q test/symbol_variable/test_symbol_dim.py`

### 测试目标

- 覆盖构造、运算、比较、动态性判断与错误分支。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| SD-001 | 构造 | `int` 输入 | N/A | `SymbolDim(4)` | 构造成功 |
| SD-002 | 构造 | `str` 符号输入 | N/A | `SymbolDim("N")` | 构造成功 |
| SD-003 | 构造 | `sympy.Basic` 输入 | N/A | `SymbolDim(sympy.Symbol("M"))` | 构造成功 |
| SD-004 | 运算 | 加减乘除 | N/A | `SymbolDim("N") + 2` | 返回 `SymbolDim` |
| SD-005 | 比较 | 等价性 | N/A | `SymbolDim("N") == "N"` | 返回 `True` |
| SD-006 | 动态性 | 动态判断 | N/A | `SymbolDim("N").is_dynamic()` | 返回 `True` |
| SD-007 | 异常 | 纯数字字符串 | N/A | `SymbolDim("12")` | 抛 `ValueError` |
| SD-008 | 异常 | 空白字符串 | N/A | `SymbolDim(" ")` | 抛 `ValueError` |
| SD-009 | 异常 | 非法类型 | N/A | `SymbolDim(object())` | 抛 `TypeError` |
