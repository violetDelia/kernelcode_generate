# symbol_dim.md

用于定义 `SymbolDim` 的行为规范，并描述本次重构的目标、边界与兼容性要求。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)
- `test`：[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)
- `功能实现`：[`symbol_variable/symbol_dim.py`](../../symbol_variable/symbol_dim.py)

## 重构目标

- 抽取并复用操作数规范化逻辑，减少算术/比较路径的重复代码。
- 明确并统一 `str` 与 `sympy.Symbol` 的符号假设策略，保证构造与运算结果一致。
- 明确异常类型与提示规则，保证非法输入可预测。
- 保持对外接口与行为稳定，便于现有调用方与测试无缝迁移。

## 重构边界

- 仅重构 `symbol_variable/symbol_dim.py` 内部实现，不新增对外 API。
- 不引入新的维度语义（如广播规则、约束求解、形状推导）。
- 不对 `sympy` 表达式做额外化简或优化，保持 `sympy` 默认行为。

## 兼容性

- `SymbolDim` 的构造、算术、比较与动态性判断接口保持不变。
- 数字字符串继续拒绝，异常类型明确为 `ValueError`。
- `sympy.Symbol` 的假设保留规则需与实现与测试一致：仅在无显式假设时规范化。

## 依赖约定

- `sympy`：符号与表达式构造。

## 术语

- 符号维度：由 `int` 或 `sympy` 表达式表示的维度值。
- 动态维度：表达式包含自由符号（`free_symbols`）的维度。

## 行为规范

### _SymbolDim

功能说明：

- 内部基类，封装符号维度值与基础算术/比较运算。

#### 初始化

接口：`__init__(sym: int | str | sympy.Basic)`

功能说明：

- `int`：转为 `sympy.Integer`。
- `str`：必须为非纯数字字符串，转为 `sympy.symbols(sym, integer=True, real=True)`；纯数字字符串抛 `ValueError`。
- `sympy.Basic`：若为 `sympy.Symbol` 且 `is_integer/is_real` 均为 `None`（无显式假设），按名称重新构造为 `sympy.symbols(name, integer=True, real=True)`；否则保留原有假设并直接保存。
- 其他类型抛 `TypeError`。

#### 操作数规范化

功能说明：

- 内部应抽取统一的操作数规范化逻辑，用于算术与比较路径复用。
- `int` 转为 `sympy.Integer`。
- `str` 转为 `sympy.symbols(str, integer=True, real=True)`，与构造保持同一假设策略。
- `SymbolDim` 操作数使用其 `get_symbol()`。
- 其他类型抛 `TypeError`。

#### 基础方法

- `get_symbol()`：返回内部 `sympy` 表达式。
- `__repr__()`：返回 `str(get_symbol())`。

#### 算术运算

接口：`__add__ / __radd__ / __sub__ / __rsub__ / __mul__ / __rmul__ / __truediv__ / __rtruediv__`

功能说明：

- 支持 `int`、`str`、`SymbolDim`。
- `str` 操作数统一按 `integer=True, real=True` 规范化。
- 返回新的 `SymbolDim`。

#### 比较运算

接口：`__eq__(other)`

功能说明：

- 支持 `int`、`str`、`SymbolDim`。
- `str` 操作数与算术运算保持相同符号假设。
- 比较底层 `sympy` 表达式的等价性。

### SymbolDim

功能说明：

- 对外公开的符号维度类型，继承 `_SymbolDim`。

#### 动态性判断

接口：`is_dynamic() -> bool`

功能说明：当 `get_symbol().free_symbols` 非空时返回 `True`。

#### 数值转换

接口：`convert_from_int(value: int)`

功能说明：将 `int` 转为 `SymbolDim`。

## 返回与错误

### 成功返回

- 构造与算术运算返回 `SymbolDim`。
- `get_symbol` 返回 `sympy` 表达式。
- `is_dynamic` 与 `__eq__` 返回 `bool`。

### 失败返回

- `__init__` 传入不支持类型时抛 `TypeError`。
- `__init__` 传入纯数字字符串时抛 `ValueError`。
- 算术与比较运算遇到不支持类型时抛 `TypeError`。

## 测试

- 测试文件：[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)
- 执行命令：`pytest -q test/symbol_variable/test_symbol_dim.py`

### 测试目标

- 覆盖构造、算术、比较、动态性判断与错误分支。
- 验证 `str` 操作数与构造的符号假设一致。
- 验证 `sympy.Symbol` 在“无显式假设”与“有显式假设”两种场景下的策略差异。

### 测试标准

- 全部测试用例通过，`pytest` 返回码为 0。
- 行为回归：重构前后的语义一致，输出表达式与异常类型稳定。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| SD-001 | 构造 | int/str/sympy | N/A | `SymbolDim(8)`、`SymbolDim("N")`、`SymbolDim(sp.symbols("M"))` | 构造成功，符号假设一致 |
| SD-002 | 构造 | 数字字符串 | N/A | `SymbolDim("12")` | 抛 `ValueError` |
| SD-003 | 运算 | add/sub/mul/div | N/A | `SymbolDim("N") + 2` 等 | 返回 `SymbolDim`，表达式正确 |
| SD-004 | 反向运算 | radd/rsub/rmul/rtruediv | N/A | `1 + SymbolDim("N")` | 返回 `SymbolDim` |
| SD-005 | 动态性/转换 | is_dynamic/convert | N/A | `SymbolDim(8).is_dynamic()` | 正确返回 |
| SD-006 | 相等 | int/str/SymbolDim | N/A | `SymbolDim("N") == "N"` | True |
| SD-007 | 异常 | 非法类型 | N/A | `SymbolDim(3) + 1.0` | 抛 `TypeError` |
| SD-008 | 表现 | get_symbol/repr | N/A | `repr(SymbolDim("N"))` | 与 `str(get_symbol())` 一致 |
| SD-009 | 规范化 | str 操作数 | N/A | `SymbolDim("N") + "N"` | 符号假设一致 |
| SD-010 | 规范化 | sympy.Symbol 无假设 | N/A | `SymbolDim(sp.Symbol("N"))` | 规范化为 integer/real |
| SD-011 | 兼容 | sympy.Symbol 有假设 | N/A | `SymbolDim(sp.Symbol("Q", integer=False))` | 保持原假设 |
