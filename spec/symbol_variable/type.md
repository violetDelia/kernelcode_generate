# type.md

## 功能简介

[immutable]用于定义基础数据类型枚举 `NumericType` 和张量布局格式枚举 `Farmat`。

## API 列表

- `class NumericType(Enum)`
- `class Farmat(Enum)`
- `FLOAT_DTYPES`
- `INT_DTYPES`
- `ARITHMETIC_DTYPE_ORDER`
- `ARITHMETIC_DTYPE_RANK`
- `NN_FLOAT_DTYPES`
- `is_integer_dtype(dtype: NumericType) -> bool`
- `is_float_dtype(dtype: NumericType) -> bool`

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`小李飞刀`
- `spec`：`spec/symbol_variable/type.md`
- `功能实现`：`kernel_gen/symbol_variable/type.py`
- `test`：`test/symbol_variable/test_type.py`

## [immutable]文档信息

- `spec`：[`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)
- `test`：[`test/symbol_variable/type.py`](../../test/symbol_variable/type.py)
- `功能实现`：[`kernel_gen/symbol_variable/type.py`](../../kernel_gen/symbol_variable/type.py)

## 依赖

- `enum.Enum`：用于定义枚举。
- [`spec/symbol_variable/__init__.md`](../../spec/symbol_variable/__init__.md)：包级重导出与 legacy 路径边界来源。

## 目标

- 提供稳定、可枚举、可比较的数值类型与布局格式常量集合。
- 明确模块级公开 API 可达性与 `import *` 导出边界。
- 约束 `Farmat` 的公开成员与访问边界，仅允许 `Norm` 与 `CLast`。
- 为上游比较类公开接口提供稳定的布尔 dtype 标识 `NumericType.Bool`。
- 为 `Memory.clone(...)`、operation family 与 pass/DSL 公共入口提供最小 dtype family 查询能力。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- [immutable]仅定义 `NumericType` 与 `Farmat` 两个枚举类型。
- [immutable]不负责内存对象、张量对象或其他模块的运行时语义。
- [immutable]不提供工厂函数、转换函数或其他辅助 API。
- 上述旧口径在本轮继续保持“不提供工厂构造、转换、promotion、字符串解析或包根重导出 helper”的含义；当前新增公开范围仅限下文列出的 dtype family 常量与两个 dtype family 查询 helper。
- 当前额外公开的模块级 dtype family 真源为 `FLOAT_DTYPES` / `INT_DTYPES` / `NN_FLOAT_DTYPES`，dtype promotion 常量真源为 `ARITHMETIC_DTYPE_ORDER` / `ARITHMETIC_DTYPE_RANK`，查询 helper 为 `is_integer_dtype(...)` 与 `is_float_dtype(...)`；helper 只接受 `NumericType`，不承担工厂构造、字符串解析或自动转换。
- 仅定义 arithmetic promotion 的稳定顺序与 rank 常量，不定义完整 dtype 推导、布局转换或字符串解析逻辑。
- 当前支持从 `kernel_gen.symbol_variable.type` 直接导入，也支持通过 `kernel_gen.symbol_variable` 包入口重导出导入；包级入口边界由 [`spec/symbol_variable/__init__.md`](../../spec/symbol_variable/__init__.md) 负责。
- `FLOAT_DTYPES`、`INT_DTYPES`、`NN_FLOAT_DTYPES`、`ARITHMETIC_DTYPE_ORDER`、`ARITHMETIC_DTYPE_RANK`、`is_integer_dtype(...)` 与 `is_float_dtype(...)` 只在 `kernel_gen.symbol_variable.type` 子模块公开，不进入 `kernel_gen.symbol_variable` 包根稳定导出集合。
- 不提供旧路径 `symbol_variable.type` 的兼容入口；该规则与包级 legacy 路径禁用保持一致。
- 不扩展到量化类型、复数类型、稀疏布局或其他未公开的枚举成员。
## API详细说明

### `class NumericType(Enum)`

- api：`class NumericType(Enum)`
- 参数：无。
- 返回值：`NumericType` 枚举类型对象。
- 使用示例：

  ```python
  numeric_type = NumericType()
  ```
- 功能说明：定义 `NumericType` 公开枚举类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class Farmat(Enum)`

- api：`class Farmat(Enum)`
- 参数：无。
- 返回值：`Farmat` 枚举类型对象。
- 使用示例：

  ```python
  farmat = Farmat()
  ```
- 功能说明：定义 `Farmat` 公开枚举类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `FLOAT_DTYPES`

- api：`FLOAT_DTYPES`
- 参数：无。
- 返回值：公开常量值。
- 使用示例：

  ```python
from kernel_gen.symbol_variable.type import FLOAT_DTYPES

api_ref = FLOAT_DTYPES
```
- 功能说明：定义 `FLOAT_DTYPES` 公开常量。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；未列入 API 的内部状态不对外承诺。

### `INT_DTYPES`

- api：`INT_DTYPES`
- 参数：无。
- 返回值：公开常量值。
- 使用示例：

  ```python
from kernel_gen.symbol_variable.type import INT_DTYPES

api_ref = INT_DTYPES
```
- 功能说明：定义 `INT_DTYPES` 公开常量。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；未列入 API 的内部状态不对外承诺。

### `ARITHMETIC_DTYPE_ORDER`

- api：`ARITHMETIC_DTYPE_ORDER`
- 参数：无。
- 返回值：公开常量值。
- 使用示例：

  ```python
from kernel_gen.symbol_variable.type import ARITHMETIC_DTYPE_ORDER

api_ref = ARITHMETIC_DTYPE_ORDER
```
- 功能说明：定义 `ARITHMETIC_DTYPE_ORDER` 公开常量。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；未列入 API 的内部状态不对外承诺。

### `ARITHMETIC_DTYPE_RANK`

- api：`ARITHMETIC_DTYPE_RANK`
- 参数：无。
- 返回值：公开常量值。
- 使用示例：

  ```python
from kernel_gen.symbol_variable.type import ARITHMETIC_DTYPE_RANK

api_ref = ARITHMETIC_DTYPE_RANK
```
- 功能说明：定义 `ARITHMETIC_DTYPE_RANK` 公开常量。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；未列入 API 的内部状态不对外承诺。

### `NN_FLOAT_DTYPES`

- api：`NN_FLOAT_DTYPES`
- 参数：无。
- 返回值：公开常量值。
- 使用示例：

  ```python
from kernel_gen.symbol_variable.type import NN_FLOAT_DTYPES

api_ref = NN_FLOAT_DTYPES
```
- 功能说明：定义 `NN_FLOAT_DTYPES` 公开常量。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；未列入 API 的内部状态不对外承诺。

### `is_integer_dtype(dtype: NumericType) -> bool`

- api：`is_integer_dtype(dtype: NumericType) -> bool`
- 参数：
  - `dtype`：数据类型，定义张量、内存或符号对象的元素类型；类型 `NumericType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```python
  result = is_integer_dtype(dtype=sample_dtype)
  ```
- 功能说明：执行 `is_integer_dtype`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。

### `is_float_dtype(dtype: NumericType) -> bool`

- api：`is_float_dtype(dtype: NumericType) -> bool`
- 参数：
  - `dtype`：数据类型，定义张量、内存或符号对象的元素类型；类型 `NumericType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```python
  result = is_float_dtype(dtype=sample_dtype)
  ```
- 功能说明：执行 `is_float_dtype`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。


## 额外补充

### 相邻值说明

- `__init__.md` 负责包级导出集合、`kernel_gen.symbol_variable` 的 `__all__` 与 `import *`；本文件只定义 `type.py` 模块本身的枚举语义与模块级导出边界。
- `memory.md` 负责 `NumericType` / `Farmat` 在 `Memory` 中如何被消费，本文件不定义内存对象行为。
- `operation/nn` 相关测试只把 `NumericType.Bool` 当作公开成员消费，不在本文件重复定义比较算子语义。

### 公开语义说明

### `NumericType` 枚举成员与兼容说明

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

### `Farmat` 枚举成员与兼容说明

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

### dtype family 常量与 helper 语义

#### `FLOAT_DTYPES`

功能说明：

- 当前公开浮点 dtype family 真源。

使用示例：

```python
from kernel_gen.symbol_variable.type import FLOAT_DTYPES, NumericType

assert NumericType.Float32 in FLOAT_DTYPES
assert NumericType.Bool not in FLOAT_DTYPES
```

注意事项：

- 固定覆盖 `Float16`、`BFloat16`、`Float32`、`Float64`。
- 不包含整数成员与 `Bool`。
- `dtype_constants.FLOAT_DTYPES` 必须复用该对象，不再自维护重复集合。

返回与限制：

- 返回 `set[NumericType]`。

#### `INT_DTYPES`

功能说明：

- 当前公开整数 dtype family 真源。

使用示例：

```python
from kernel_gen.symbol_variable.type import INT_DTYPES, NumericType

assert NumericType.Int32 in INT_DTYPES
assert NumericType.Bool not in INT_DTYPES
```

注意事项：

- 固定覆盖 `Int8/16/32/64` 与 `Uint8/16/32/64`。
- 不包含浮点成员与 `Bool`。
- `dtype_constants.INT_DTYPES` 必须复用该对象，不再自维护重复集合。

返回与限制：

- 返回 `set[NumericType]`。

#### `ARITHMETIC_DTYPE_ORDER`

功能说明：

- 当前公开 arithmetic promotion 顺序真源。

使用示例：

```python
from kernel_gen.symbol_variable.type import ARITHMETIC_DTYPE_ORDER, NumericType

assert ARITHMETIC_DTYPE_ORDER[0] is NumericType.Int8
assert ARITHMETIC_DTYPE_ORDER[-1] is NumericType.Float64
```

注意事项：

- 固定顺序为 `Int8`、`Uint8`、`Int16`、`Uint16`、`Int32`、`Uint32`、`Int64`、`Uint64`、`Float16`、`BFloat16`、`Float32`、`Float64`。
- `NumericType.Bool` 不参与 arithmetic promotion 顺序。

返回与限制：

- 返回 `tuple[NumericType, ...]`。

#### `ARITHMETIC_DTYPE_RANK`

功能说明：

- 当前公开 arithmetic promotion rank 真源。

使用示例：

```python
from kernel_gen.symbol_variable.type import ARITHMETIC_DTYPE_RANK, NumericType

assert ARITHMETIC_DTYPE_RANK[NumericType.Float32] > ARITHMETIC_DTYPE_RANK[NumericType.Int32]
```

注意事项：

- 必须由 `ARITHMETIC_DTYPE_ORDER` 派生，键集合与 `ARITHMETIC_DTYPE_ORDER` 保持一致。

返回与限制：

- 返回 `dict[NumericType, int]`。

#### `NN_FLOAT_DTYPES`

功能说明：

- 当前公开 nn family 浮点 dtype 集合真源。

使用示例：

```python
from kernel_gen.symbol_variable.type import FLOAT_DTYPES, NN_FLOAT_DTYPES

assert NN_FLOAT_DTYPES is FLOAT_DTYPES
```

注意事项：

- 当前必须与 `FLOAT_DTYPES` 保持同一对象身份，避免 nn family 维护第二套浮点集合。

返回与限制：

- 返回 `set[NumericType]`。

#### `is_integer_dtype(dtype: NumericType) -> bool`

功能说明：

- 判断传入 `dtype` 是否属于当前公开整数 family。

参数说明：

- `dtype (NumericType)`：待判断的公开 dtype 枚举成员。

使用示例：

```python
from kernel_gen.symbol_variable.type import NumericType, is_integer_dtype

assert is_integer_dtype(NumericType.Int32) is True
assert is_integer_dtype(NumericType.Uint64) is True
assert is_integer_dtype(NumericType.Bool) is False
```

注意事项：

- 当前整数 family 固定覆盖 `Int8/16/32/64` 与 `Uint8/16/32/64`。
- `NumericType.Bool` 不属于整数 family。
- helper 必须拒绝非 `NumericType` 输入，禁止把字符串、`.value`、其他枚举或任意对象当作可接受入口。

返回与限制：

- 返回 `bool`。
- 非 `NumericType` 输入必须抛出 `TypeError`。

#### `is_float_dtype(dtype: NumericType) -> bool`

功能说明：

- 判断传入 `dtype` 是否属于当前公开浮点 family。

参数说明：

- `dtype (NumericType)`：待判断的公开 dtype 枚举成员。

使用示例：

```python
from kernel_gen.symbol_variable.type import NumericType, is_float_dtype

assert is_float_dtype(NumericType.Float16) is True
assert is_float_dtype(NumericType.BFloat16) is True
assert is_float_dtype(NumericType.Int32) is False
```

注意事项：

- 当前浮点 family 固定覆盖 `Float16`、`BFloat16`、`Float32`、`Float64`。
- `Bool` 与所有整数成员都必须返回 `False`。
- helper 只做 family 判断，不提供字符串字面量到 `NumericType` 的解析。

返回与限制：

- 返回 `bool`。
- 非 `NumericType` 输入必须抛出 `TypeError`。

## 测试

- 测试文件：[`test/symbol_variable/test_type.py`](../../test/symbol_variable/test_type.py)
- 执行命令：`pytest -q test/symbol_variable/test_type.py`；`pytest -q test/operation/nn/test_package.py -k 'test_nn_compare_predicate or test_nn_compare_alias or test_nn_compare_implicit_broadcast'`

### 测试分层

- 主测试：[`test/symbol_variable/test_type.py`](../../test/symbol_variable/test_type.py) 负责枚举成员、`FLOAT_DTYPES` / `INT_DTYPES`、`is_integer_dtype(...)` / `is_float_dtype(...)`、模块级公开 API 可达性、模块级 `import *` 与 legacy 子模块路径。
- 交叉验证：[`test/operation/nn/test_package.py`](../../test/operation/nn/test_package.py) 只验证 `NumericType.Bool` 被上游比较接口稳定消费。

### 测试目标

- 验证 `NumericType` 既有公开成员、名称和值稳定；`Bool` 由交叉链路单独验证。
- 验证 `NumericType.Bool` 作为公开枚举成员可用于比较类接口返回值。
- 验证 `Farmat` 仅公开 `Norm` 与 `CLast`。
- 验证 `FLOAT_DTYPES` / `INT_DTYPES` 内容与 `is_integer_dtype(...)` / `is_float_dtype(...)` 的 family 结果、非法输入与子模块公开边界。
- 验证模块级公开 API 可达性与 `import *` 的公开边界。
- 验证旧路径 `symbol_variable.type` 不可导入。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| TY-001 | 成员值 | `NumericType` 既有成员值稳定 | 已导入 `kernel_gen.symbol_variable.type` | 读取既有成员 `.value` | 与约定字符串一致 |
| TY-002 | 成员边界 | `Farmat` 公开成员 | 已导入 `Farmat` | 仅可访问 `Norm`/`CLast` | 不存在额外布局名 |
| TY-003 | 导出边界 | 模块公开 API 可达性 | 已导入模块 | 读取 `NumericType/Farmat/is_integer_dtype/is_float_dtype`，并确认无 `Memory/MemorySpace` 混入 | 仅已定义公开 API 可达，未定义名字不作为模块级公开接口出现 |
| TY-004 | 导出边界 | `import *` 暴露范围 | 已导入模块 | 执行 `from kernel_gen.symbol_variable.type import *` | 仅暴露 `Farmat`/`NumericType`/`FLOAT_DTYPES`/`INT_DTYPES`/`is_integer_dtype`/`is_float_dtype` |
| TY-004A | dtype family 常量 | 模块级 dtype family 真源 | 已导入 `FLOAT_DTYPES` / `INT_DTYPES` | 读取集合内容并检查 `Bool` 不属于任一集合 | 内容与公开 dtype family 一致 |
| TY-005 | 成员访问 | `NumericType` 既有成员访问 | 已导入 `NumericType` | 读取既有成员 `.name` | 与约定成员名一致 |
| TY-006 | 导入边界 | 旧路径导入 | 已安装包 | `importlib.import_module("symbol_variable.type")` | 抛 `ModuleNotFoundError` |
| TY-007 | 布尔类型 | `NumericType.Bool` 作为比较结果 dtype 的公开成员 | 已导入 `NumericType` 与 nn 比较接口 | 执行 `eq`/`ne`/`lt`/`le`/`gt`/`ge` 并读取结果 `dtype` | 返回值 `dtype` 为 `NumericType.Bool`，与公开成员语义一致 |
| TY-008 | family helper | 整数 family 判断 | 已导入 `is_integer_dtype` | 分别传入 `Int32` / `Uint64` / `Bool` | 结果为 `True / True / False` |
| TY-009 | family helper | 浮点 family 判断 | 已导入 `is_float_dtype` | 分别传入 `Float16` / `BFloat16` / `Int32` | 结果为 `True / True / False` |
| TY-010 | family helper | 非法输入拒绝 | 已导入 helper | 传入字符串或其他非 `NumericType` 对象 | 抛 `TypeError` |
| TY-011 | 包根边界 | helper 不进入包根 | 已导入 `kernel_gen.symbol_variable` | 读取 `is_integer_dtype` / `is_float_dtype` | 包根不存在这两个名称 |
