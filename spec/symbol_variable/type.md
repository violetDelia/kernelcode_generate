# type.md

## 功能简介

[immutable]用于定义基础数据类型枚举 `NumericType` 和张量布局格式枚举 `Farmat`。

## [immutable]文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`榕`
- `spec`：[`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)
- `test`：[`test/symbol_variable/test_type.py`](../../test/symbol_variable/test_type.py)
- `功能实现`：[`kernel_gen/symbol_variable/type.py`](../../kernel_gen/symbol_variable/type.py)

## 依赖

- `enum.Enum`：用于定义枚举。
- `kernel_gen.symbol_variable.type`：作为 `NumericType` 与 `Farmat` 的唯一有效导入入口。

## 目标

- 提供稳定、可枚举、可比较的数值类型与布局格式常量集合。
- 明确模块级公开导出边界（`__all__` 与 `import *`）。
- 约束 `Farmat` 的公开成员与访问边界，仅允许 `Norm` 与 `CLast`。
- 为上游比较类公开接口提供稳定的布尔 dtype 标识 `NumericType.Bool`。

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
from kernel_gen.symbol_variable.type import NumericType

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
assert NumericType.Bool.value == "bool"
assert NumericType.Int32 is not NumericType.Float32
```

注意事项：

- 公开兼容性同时覆盖成员可见性、成员名称与 `.value` 字符串；调用方可以依赖当前 `.value` 与 dtype 标识一一对应。
- 成员名称和值必须一一对应，不允许同义别名。
- 当前公开成员分为：
  - 有符号整型：`Int8`、`Int16`、`Int32`、`Int64`
  - 无符号整型：`Uint8`、`Uint16`、`Uint32`、`Uint64`
  - 浮点类型：`Float16`、`BFloat16`、`Float32`、`Float64`
  - 布尔类型：`Bool`
- `NumericType.Bool` 的 `.value` 固定为 `"bool"`，用于承载 `nn.eq` / `nn.ne` / `nn.lt` / `nn.le` / `nn.gt` / `nn.ge` 等公开比较接口的 predicate 结果。
- 未列出的 dtype 不属于当前 spec 范围。

返回与限制：

- 成员支持 `is` 与 `==` 比较，语义与标准 `Enum` 一致。
- `.value` 属于公开接口，必须保持为当前 spec 列出的 dtype 字符串。

### `Farmat`

功能说明：

- 张量布局格式枚举。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable.type import Farmat

assert Farmat.Norm.name == "Norm"
assert Farmat.CLast.name == "CLast"
```

注意事项：

- [immutable]当前公开成员包括 `Norm` 与 `CLast`。
- [immutable]`Norm` 表示通道维不在最后一维的常见布局别名。
- [immutable]`CLast` 表示通道维位于最后一维的常见布局别名。
- 上述“常见布局别名”仅用于帮助理解成员语义，不新增公开成员、字符串等价关系或外部别名契约。
- 公开兼容性仅保证成员可见性与成员名称；`.value` 的具体取值不作为公开契约，调用方不得通过 `.value`、字符串或其他等价关系推导布局语义。

返回与限制：

- 成员支持 `is` 与 `==` 比较，语义与标准 `Enum` 一致。
- 返回的成员仅承诺 `Enum` 身份、可见性与 `.name` 稳定；不承诺 `.value` 可用于外部布局判等、字符串解析或别名兼容。
- “常见布局别名”描述不构成新增导出成员、字符串匹配规则或与其他布局名的公开等价关系。

## 测试

- 测试文件：[`test/symbol_variable/test_type.py`](../../test/symbol_variable/test_type.py)
- 执行命令：`pytest -q test/symbol_variable/test_type.py`；`pytest -q test/operation/test_operation_nn.py -k 'test_nn_compare_predicate or test_nn_compare_alias or test_nn_compare_implicit_broadcast'`

### 测试目标

- 验证 `NumericType` 既有公开成员、名称和值稳定；`Bool` 由交叉链路单独验证。
- 验证 `NumericType.Bool` 作为公开枚举成员可用于比较类接口返回值。
- 验证 `Farmat` 仅公开 `Norm` 与 `CLast`。
- 验证 `__all__` 与 `import *` 的公开边界。
- 验证旧路径 `symbol_variable.type` 不可导入。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| TY-001 | 成员值 | `NumericType` 既有成员值稳定 | 已导入 `kernel_gen.symbol_variable.type` | 读取既有成员 `.value` | 与约定字符串一致 |
| TY-002 | 成员边界 | `Farmat` 公开成员 | 已导入 `Farmat` | 仅可访问 `Norm`/`CLast` | 不存在额外布局名 |
| TY-003 | 导出边界 | `__all__` 内容 | 已导入模块 | 读取 `__all__` | 严格等于 `["NumericType", "Farmat"]` |
| TY-004 | 导出边界 | `import *` 暴露范围 | 已导入模块 | 执行 `from kernel_gen.symbol_variable.type import *` | 仅暴露 `Farmat`/`NumericType` |
| TY-005 | 成员访问 | `NumericType` 既有成员访问 | 已导入 `NumericType` | 读取既有成员 `.name` | 与约定成员名一致 |
| TY-006 | 导入边界 | 旧路径导入 | 已安装包 | `importlib.import_module("symbol_variable.type")` | 抛 `ModuleNotFoundError` |
| TY-007 | 布尔类型 | `NumericType.Bool` 作为比较结果 dtype 的公开成员 | 已导入 `NumericType` 与 nn 比较接口 | 执行 `eq`/`ne`/`lt`/`le`/`gt`/`ge` 并读取结果 `dtype` | 返回值 `dtype` 为 `NumericType.Bool`，与公开成员语义一致 |
