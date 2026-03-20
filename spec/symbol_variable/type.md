# type.md

## 功能简介

[immutable]用于定义基础数据类型枚举 `NumericType` 和张量布局格式枚举 `Farmat`。

## [immutable]文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`榕`
- `spec`：[`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)
- `test`：[`test/symbol_variable/test_type.py`](../../test/symbol_variable/test_type.py)
- `功能实现`：[`python/symbol_variable/type.py`](../../python/symbol_variable/type.py)

## 依赖

- `enum.Enum`：用于定义枚举。
- `python.symbol_variable.type`：作为 `NumericType` 与 `Farmat` 的唯一有效导入入口。

## 目标

- 提供稳定、可枚举、可比较的数值类型与布局格式常量集合。
- 明确模块级公开导出边界（`__all__` 与 `import *`）。
- 约束 `Farmat` 的公开成员与访问边界，仅允许 `Norm` 与 `CLast`。

## 限制与边界

- [immutable]仅定义 `NumericType` 与 `Farmat` 两个枚举类型。
- [immutable]不负责内存对象、张量对象或其他模块的运行时语义。
- [immutable]不提供工厂函数、转换函数或其他辅助 API。
- 不定义 dtype 推导、类型提升、布局转换或字符串解析逻辑。
- 不提供旧路径 `symbol_variable.type` 的兼容入口。
- 不扩展到量化类型、复数类型、稀疏布局或其他未公开的枚举成员。

## 公开接口

### `NumericType`

功能说明：

- 数值类型枚举。

参数说明：

- 无参数。

使用示例：

```python
from python.symbol_variable.type import NumericType

assert NumericType.Int8.value == "int8"
assert NumericType.Int16.value == "int16"
assert NumericType.Int32.value == "int32"
assert NumericType.Int64.value == "int64"
assert NumericType.Uint8.value == "uint8"
assert NumericType.Uint16.value == "uint16"
assert NumericType.Uint32.value == "uint32"
assert NumericType.Uint64.value == "uint64"
assert NumericType.Float16.value == "float16"
assert NumericType.BFloat16.value == "bf16"
assert NumericType.Float32.value == "float32"
assert NumericType.Float64.value == "float64"
assert NumericType.Int32 is not NumericType.Float32
```

注意事项：

- 成员名称和值必须一一对应，不允许同义别名。
- 当前公开成员分为：
  - 有符号整型：`Int8`、`Int16`、`Int32`、`Int64`
  - 无符号整型：`Uint8`、`Uint16`、`Uint32`、`Uint64`
  - 浮点类型：`Float16`、`BFloat16`、`Float32`、`Float64`
- 未列出的 dtype 不属于当前 spec 范围。

返回与限制：

- 成员支持 `is` 与 `==` 比较，语义与标准 `Enum` 一致。

### `Farmat`

功能说明：

- 张量布局格式枚举。

参数说明：

- 无参数。

使用示例：

```python
from python.symbol_variable.type import Farmat

assert Farmat.Norm.name == "Norm"
assert Farmat.CLast.name == "CLast"
```

注意事项：

- [immutable]当前公开成员包括 `Norm` 与 `CLast`。
- [immutable]`Norm` 表示通道维不在最后一维的常见布局别名。
- [immutable]`CLast` 表示通道维位于最后一维的常见布局别名。

返回与限制：

- 成员支持 `is` 与 `==` 比较，语义与标准 `Enum` 一致。

## 额外补充

- 模块显式公开导出仅包括 `NumericType` 与 `Farmat`。
- `from python.symbol_variable.type import *` 必须严格受 `__all__` 控制。
- `Enum`、`annotations` 或其他实现细节不属于公开 API。
- `python.symbol_variable.type` 是唯一有效导入入口；旧路径 `symbol_variable.type` 不提供兼容入口。
- 访问未定义枚举成员时遵循 Python `Enum` 规则，抛 `AttributeError` 或 `KeyError`。
- `Farmat` 仅公开 `Norm` 与 `CLast`；兼容性约束以成员可见性、名称与导出边界为准。

## 测试

- 测试文件：[`test/symbol_variable/test_type.py`](../../test/symbol_variable/test_type.py)
- 执行命令：`pytest -q test/symbol_variable/test_type.py`

### 测试目标

- 验证 `NumericType` 公开成员、名称和值稳定。
- 验证 `Farmat` 仅公开 `Norm` 与 `CLast`。
- 验证 `__all__` 与 `import *` 的公开边界。
- 验证旧路径 `symbol_variable.type` 不可导入。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| TY-001 | 成员值 | `NumericType` 成员值稳定 | 已导入 `python.symbol_variable.type` | 读取成员 `.value` | 与约定字符串一致 |
| TY-002 | 成员边界 | `Farmat` 公开成员 | 已导入 `Farmat` | 仅可访问 `Norm`/`CLast` | 不存在额外布局名 |
| TY-003 | 导出边界 | `__all__` 内容 | 已导入模块 | 读取 `__all__` | 严格等于 `["NumericType", "Farmat"]` |
| TY-004 | 导出边界 | `import *` 暴露范围 | 已导入模块 | 执行 `from python.symbol_variable.type import *` | 仅暴露 `Farmat`/`NumericType` |
| TY-005 | 成员访问 | `NumericType` 成员访问 | 已导入 `NumericType` | 读取 `.name` | 与约定成员名一致 |
