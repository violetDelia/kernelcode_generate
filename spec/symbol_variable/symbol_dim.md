# symbol_dim.md

用于描述 `SymbolDim` 类的行为与约束，表示一个整数或未知大小的符号维度。使用sympy

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：[`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)
- `test`：[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)
- `功能实现`：[`cpp_gen/cpp_gen/symbol_variable/symbol_dim.py`](../../python/symbol_variable/symbol_dim.py)

## 背景

`SymbolDim` 用于表示张量维度的“确定整数值”或“未知符号值”。它在运算中保持符号表达式能力，用于推导和组合维度关系。

## 类说明

### 类名

- `SymbolDim`

### 目标

- 表示一个确定整数或符号表达式。
- 支持常见算术运算与比较。
- 可判断是否为动态符号维度。

### 依赖

- `sympy`

## 构造与字段

### 构造参数

`SymbolDim(sym)`


### 字段


### 约束


## 行为约定

### 基础方法

- `get_symbol()`
  - 返回内部符号表达式。

- `__repr__() -> str`
  - 返回内部符号表达式的字符串形式。

- `is_dynamic() -> bool`
  - 当表达式包含自由符号时返回 `True`。
  - 纯整数常量返回 `False`。


### 算术运算
支持常见的运算

### 比较运算

支持和int/symboldim的比较

## 异常与错误

- 不支持的类型：抛出 `TypeError`。
- `sym` 为纯数字字符串：抛出错误（实现允许使用 `AssertionError` 或 `ValueError`，需保证能明确提示非法输入）。

## 使用示例

```python

n = SymbolDim("N")
m = SymbolDim(32)

assert n.is_dynamic() is True
assert m.is_dynamic() is False

k = n + m
p = 2 * n + "C"
q = n * m

assert k == n + m
```

## 测试建议

- 初始化：`int`、`str`、`sympy.Basic`。
- 非法输入：纯数字字符串、未知类型。
- 动态判断：常量与符号表达式。
- 算术运算：`+ - * /` 的左右操作数覆盖。
- 相等性判断：`int/str/SymbolDim` 三种比较路径。
