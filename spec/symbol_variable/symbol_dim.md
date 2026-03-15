# symbol_dim.md

用于定义 `SymbolDim` 的行为规范、输入约束、公开 API 与测试要求。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)
- `test`：[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)
- `功能实现`：[`python/symbol_variable/symbol_dim.py`](../../python/symbol_variable/symbol_dim.py)

## 功能边界

- 模块对外提供 `SymbolDim(value)` 作为符号维度构造入口。
- 模块负责统一构造、算术与比较路径中的输入规范化规则。
- 不引入新的维度语义（如广播规则、约束求解、形状推导）。
- 不对 `sympy` 表达式做额外化简或优化，保持 `sympy` 默认行为。

## 兼容性

- `SymbolDim` 的构造、算术、比较与动态性判断接口保持不变。
- 公开构造入口为 `SymbolDim(value)`。
- 纯数字字符串继续拒绝，异常类型明确为 `ValueError`，且该规则同时适用于构造、算术与比较入口。
- `sympy.Symbol` 的假设保留规则需与实现与测试一致：仅在无显式假设时规范化。
- 非空且不属于“纯数字字符串”的 `str` 输入不新增额外语义校验，继续按 `sympy.symbols(..., integer=True, real=True)` 处理，以兼容既有调用。
- 若实现仍需要类型规整辅助函数，应使用私有命名（如 `_normalize_*`），不得再暴露新的公开 `convert_from_*` 系列名称。

## 依赖约定

- `sympy`：符号与表达式构造。

## Compat 说明

- 迁移后不再兼容旧路径 `symbol_variable.symbol_dim`，不提供 compat 转发模块。

## 术语

- 符号维度：由 `int` 或 `sympy` 表达式表示的维度值。
- 动态维度：表达式包含自由符号（`free_symbols`）的维度。
- 纯数字字符串：对输入字符串执行 `strip()` 后，结果非空且 `isdigit()` 为 `True` 的字符串，例如 `"12"`、`" 12 "`、`"001"`、`"１２"`、`"٠١٢"`。

## 输入规则总览

### 合法输入

- `int`：视为静态维度，转为 `sympy.Integer`。
- `sympy.Basic`：直接接收；若为未显式指定 `is_integer/is_real` 的 `sympy.Symbol`，按名称规范化为 `integer=True, real=True`。
- `str`：当且仅当字符串不是空白串，且不属于“纯数字字符串”时视为合法输入；后续按 `sympy.symbols(..., integer=True, real=True)` 构造符号。

### 非法输入

- 构造、算术、反向算术、比较中的纯数字字符串：抛 `ValueError`。
- 构造、算术、反向算术、比较中的空字符串或仅空白字符串：抛 `ValueError`。
- 不受支持的非 `int` / 非 `str` / 非 `SymbolDim` / 非 `sympy.Basic` 类型：抛 `TypeError`。

### 兼容性边界

- 本次规则统一仅针对“纯数字字符串”与空白字符串，不额外收紧其他字符串命名规则。
- `"+1"`、`"-1"`、`"3.14"`、`"1_0"`、`"1N"`、`"N1"` 等虽然外观接近数字，但因不属于“纯数字字符串”，继续按符号名处理。
- 前后空白不改变“是否为纯数字字符串”的判定结果：`" 12 "` 视为非法，`" N "` 仍可按符号 `N` 处理。
- Unicode 数字遵循 Python `str.isdigit()` 语义，仍视为纯数字字符串并拒绝。
- 异常消息文本不是兼容承诺；兼容性仅要求异常类型稳定为 `ValueError` 或 `TypeError`。

## 公开接口约束

### 构造入口

- `SymbolDim(value)` 是唯一公开的输入归一化与构造入口。
- 允许的 `value` 类型与 `_SymbolDim.__init__` 约定一致：`int`、合法 `str`、`sympy.Basic`。

### 命名约束

- 模块不公开 `convert_from_*` 系列接口。
- 仅允许私有辅助逻辑使用 `_normalize_str`、`_normalize_operand`、`_normalize_symbol` 等 `_normalize_*` 命名。

## 行为规范

### _SymbolDim

功能说明：

- 内部基类，封装符号维度值与基础算术/比较运算。

#### 初始化

接口：`__init__(sym: int | str | sympy.Basic)`

功能说明：

- `int`：转为 `sympy.Integer`。
- `str`：必须先经过统一字符串校验。
- 纯数字字符串（按 `strip().isdigit()` 判定）抛 `ValueError`。
- 空字符串或仅空白字符串抛 `ValueError`。
- 其余字符串转为 `sympy.symbols(sym, integer=True, real=True)`。
- `sympy.Basic`：若为 `sympy.Symbol` 且 `is_integer/is_real` 均为 `None`（无显式假设），按名称重新构造为 `sympy.symbols(name, integer=True, real=True)`；否则保留原有假设并直接保存。
- 其他类型抛 `TypeError`。

#### 操作数规范化

功能说明：

- 内部应抽取统一的操作数规范化逻辑，用于算术与比较路径复用。
- `int` 转为 `sympy.Integer`。
- `str` 与构造路径复用同一字符串校验规则，而不是单独放宽。
- 纯数字字符串（如 `"12"`、`" 12 "`、`"１２"`）必须抛 `ValueError`，不得在运算或比较路径中被当作符号名接受。
- 空字符串或仅空白字符串抛 `ValueError`。
- 其他字符串转为 `sympy.symbols(str, integer=True, real=True)`，与构造保持同一假设策略。
- `SymbolDim` 操作数使用其 `get_symbol()`。
- 其他类型抛 `TypeError`。

#### 基础方法

- `get_symbol()`：返回内部 `sympy` 表达式。
- `__repr__()`：返回 `str(get_symbol())`。

#### 算术运算

接口：`__add__ / __radd__ / __sub__ / __rsub__ / __mul__ / __rmul__ / __truediv__ / __rtruediv__`

功能说明：

- 支持 `int`、`str`、`SymbolDim`。
- `str` 操作数必须先通过与构造一致的统一字符串校验。
- 纯数字字符串与空白字符串在所有算术入口中均抛 `ValueError`。
- 其他 `str` 操作数统一按 `integer=True, real=True` 规范化。
- 返回新的 `SymbolDim`。

#### 比较运算

接口：`__eq__(other)`

功能说明：

- 支持 `int`、`str`、`SymbolDim`。
- `str` 操作数与算术运算保持相同校验与符号假设。
- 纯数字字符串与空白字符串在比较入口中抛 `ValueError`。
- 比较底层 `sympy` 表达式的等价性。

### SymbolDim

功能说明：

- 对外公开的符号维度类型，继承 `_SymbolDim`。
- 公开创建方式为 `SymbolDim(value)`。

#### 动态性判断

接口：`is_dynamic() -> bool`

功能说明：当 `get_symbol().free_symbols` 非空时返回 `True`。

## 返回与错误

### 成功返回

- 构造与算术运算返回 `SymbolDim`。
- `get_symbol` 返回 `sympy` 表达式。
- `is_dynamic` 与 `__eq__` 返回 `bool`。

### 失败返回

- `__init__` 传入不支持类型时抛 `TypeError`。
- `__init__` 传入纯数字字符串或空白字符串时抛 `ValueError`。
- 算术与比较运算遇到不支持类型时抛 `TypeError`。
- 算术与比较运算遇到纯数字字符串或空白字符串时抛 `ValueError`。

## 测试

- 测试文件：[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)
- 执行命令：`pytest -q test/symbol_variable/test_symbol_dim.py`

### 测试目标

- 覆盖构造、算术、比较、动态性判断与错误分支。
- 验证公开创建入口为 `SymbolDim(value)`。
- 验证 `str` 操作数与构造共享同一字符串校验与符号假设。
- 验证 `sympy.Symbol` 在“无显式假设”与“有显式假设”两种场景下的策略差异。
- 验证纯数字字符串在构造、算术、反向算术、比较路径中均触发 `ValueError`。
- 验证空白数字字符串（如 `" 12 "`）与 Unicode 数字字符串（如 `"１２"`）按纯数字字符串处理。
- 验证 `"+1"`、`"-1"`、`"3.14"` 等非纯数字字符串继续作为符号名处理，确保兼容边界清晰。

### 测试标准

- 全部测试用例通过，`pytest` 返回码为 0。
- 输出表达式与异常类型稳定。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| SD-001 | 构造 | int/str/sympy | N/A | `SymbolDim(8)`、`SymbolDim("N")`、`SymbolDim(sp.symbols("M"))` | 构造成功，符号假设一致 |
| SD-002 | 构造 | 数字字符串 | N/A | `SymbolDim("12")` | 抛 `ValueError` |
| SD-003 | 运算 | add/sub/mul/div | N/A | `SymbolDim("N") + 2` 等 | 返回 `SymbolDim`，表达式正确 |
| SD-004 | 反向运算 | radd/rsub/rmul/rtruediv | N/A | `1 + SymbolDim("N")` | 返回 `SymbolDim` |
| SD-005 | 动态性/构造 | is_dynamic/direct-init | N/A | `SymbolDim(8).is_dynamic()`、`SymbolDim(32)` | 动态性与直接构造行为正确 |
| SD-006 | 相等 | int/str/SymbolDim | N/A | `SymbolDim("N") == "N"` | True |
| SD-007 | 异常 | 非法类型 | N/A | `SymbolDim(3) + 1.0` | 抛 `TypeError` |
| SD-008 | 表现 | get_symbol/repr | N/A | `repr(SymbolDim("N"))` | 与 `str(get_symbol())` 一致 |
| SD-009 | 规范化 | str 操作数 | N/A | `SymbolDim("N") + "N"` | 符号假设一致 |
| SD-010 | 规范化 | sympy.Symbol 无假设 | N/A | `SymbolDim(sp.Symbol("N"))` | 规范化为 integer/real |
| SD-011 | 兼容 | sympy.Symbol 有假设 | N/A | `SymbolDim(sp.Symbol("Q", integer=False))` | 保持原假设 |
| SD-012 | 统一校验 | 运算中的纯数字字符串 | N/A | `SymbolDim("N") + "12"`、`"12" / SymbolDim("N")` | 均抛 `ValueError` |
| SD-013 | 统一校验 | 比较中的纯数字字符串 | N/A | `SymbolDim("N") == "12"` | 抛 `ValueError` |
| SD-014 | 边界 | 空白数字字符串 | N/A | `SymbolDim(" 12 ")`、`SymbolDim("N") + " 12 "` | 均抛 `ValueError` |
| SD-015 | 兼容 | 非纯数字字符串 | N/A | `SymbolDim("+1")`、`SymbolDim("N") + "3.14"` | 继续按符号名处理 |
| SD-016 | 边界 | Unicode 数字字符串 | N/A | `SymbolDim("１２")`、`SymbolDim("N") == "٠١٢"` | 均抛 `ValueError` |
| SD-017 | 公开接口 | 构造入口 | N/A | `SymbolDim(32)` | 使用公开构造器完成创建 |
