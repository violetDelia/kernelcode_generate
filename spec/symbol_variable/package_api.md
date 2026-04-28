# package_api.md

## 功能简介

用于定义 `kernel_gen.symbol_variable` 包入口的稳定导出集合。本文只回答三件事：包入口暴露哪些名字、这些名字与子模块对象是否同一、哪些路径明确不再支持。

## API 列表

- `kernel_gen.symbol_variable`
- `SymbolDim(value: int | str | Expr | Symbol)`
- `SymbolList(shapes: list[int | str | SymbolDim])`
- `SymbolShape(shapes: list[int | str | SymbolDim])`
- `class LocalSpaceMeta(name: str, max_size: int | None, align: int)`
- `class Memory(shape: ShapeLike, dtype: NumericType | None = None, space: MemorySpace = MemorySpace.GM, stride: ShapeLike | None = None, format: Farmat = Farmat.Norm)`
- `Memory.get_shape(self) -> list[int | str]`
- `Memory.get_stride(self) -> list[int | SymbolDim] | None`
- `Memory.get_type(self) -> NumericType`
- `Memory.get_space(self) -> MemorySpace`
- `Memory.get_format(self) -> Farmat`
- `Memory.clone(self, dtype: NumericType | None = None, space: MemorySpace | None = None) -> Memory`
- `class MemorySpace(Enum)`
- `class NumericType(Enum)`
- `class Farmat(Enum)`
- `kernel_gen.symbol_variable.type.FLOAT_DTYPES`
- `kernel_gen.symbol_variable.type.INT_DTYPES`
- `kernel_gen.symbol_variable.type.ARITHMETIC_DTYPE_ORDER`
- `kernel_gen.symbol_variable.type.ARITHMETIC_DTYPE_RANK`
- `kernel_gen.symbol_variable.type.NN_FLOAT_DTYPES`
- `kernel_gen.symbol_variable.type.is_integer_dtype(dtype: NumericType) -> bool`
- `kernel_gen.symbol_variable.type.is_float_dtype(dtype: NumericType) -> bool`
- `kernel_gen.symbol_variable.ptr.Ptr(*dtype: object)`

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md)
- `test`：[`test/symbol_variable/test_package_api.py`](../../test/symbol_variable/test_package_api.py)
- `功能实现`：[`kernel_gen/symbol_variable/__init__.py`](../../kernel_gen/symbol_variable/__init__.py)

## 关联模块

| 模块 | 公开对象 |
|---|---|
| [`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py) | `SymbolDim` |
| [`kernel_gen/symbol_variable/symbol_shape.py`](../../kernel_gen/symbol_variable/symbol_shape.py) | `SymbolList`、`SymbolShape` |
| [`kernel_gen/symbol_variable/memory.py`](../../kernel_gen/symbol_variable/memory.py) | `LocalSpaceMeta`、`Memory`、`MemorySpace` |
| [`kernel_gen/symbol_variable/type.py`](../../kernel_gen/symbol_variable/type.py) | `NumericType`、`Farmat`；`FLOAT_DTYPES`、`INT_DTYPES`、`ARITHMETIC_DTYPE_ORDER`、`ARITHMETIC_DTYPE_RANK`、`NN_FLOAT_DTYPES`、`is_integer_dtype`、`is_float_dtype` 仅子模块入口 |
| [`kernel_gen/symbol_variable/ptr.py`](../../kernel_gen/symbol_variable/ptr.py) | `Ptr`，只保留子模块入口 |

## 包入口合同

### 稳定导出集合

包入口只导出以下名称：

- `Farmat`
- `LocalSpaceMeta`
- `Memory`
- `MemorySpace`
- `NumericType`
- `SymbolDim`
- `SymbolList`
- `SymbolShape`

使用示例：

```python
from kernel_gen.symbol_variable import Memory, NumericType, SymbolDim

mem = Memory([SymbolDim("N"), 32], NumericType.Float32)
```

约束：

- `from kernel_gen.symbol_variable import Name` 只承诺上面这组名称可稳定导入。
- `from kernel_gen.symbol_variable import *` 只能暴露上面的集合。
- 包入口不额外暴露 `Ptr`、实现细节或旧兼容名字。
- `kernel_gen.symbol_variable.type.FLOAT_DTYPES`、`kernel_gen.symbol_variable.type.INT_DTYPES`、`kernel_gen.symbol_variable.type.ARITHMETIC_DTYPE_ORDER`、`kernel_gen.symbol_variable.type.ARITHMETIC_DTYPE_RANK`、`kernel_gen.symbol_variable.type.NN_FLOAT_DTYPES`、`kernel_gen.symbol_variable.type.is_integer_dtype` 与 `kernel_gen.symbol_variable.type.is_float_dtype` 若存在，也只允许通过子模块入口导入；包入口不重导出这些 dtype family / promotion 入口。

### 对象同一性

包入口重导出的对象必须与各自子模块中的对象保持同一性，不允许包层再包装一层。

使用示例：

```python
from kernel_gen.symbol_variable import Memory as PackageMemory
from kernel_gen.symbol_variable.memory import Memory as ModuleMemory

assert PackageMemory is ModuleMemory
```

### 仅子模块入口

`Ptr` 继续作为子模块 API 存在，但不进入包入口导出集合。`FLOAT_DTYPES`、`INT_DTYPES`、`ARITHMETIC_DTYPE_ORDER`、`ARITHMETIC_DTYPE_RANK`、`NN_FLOAT_DTYPES`、`is_integer_dtype` 与 `is_float_dtype` 也属于同类“仅子模块入口”的公开接口。

使用示例：

```python
from kernel_gen.symbol_variable.ptr import Ptr
from kernel_gen.symbol_variable.type import ARITHMETIC_DTYPE_ORDER, FLOAT_DTYPES, INT_DTYPES, is_float_dtype, is_integer_dtype
```

### 旧路径禁用

以下导入路径不是公开入口：

- `symbol_variable`
- `symbol_variable.symbol_dim`
- `symbol_variable.symbol_shape`
- `symbol_variable.memory`
- `symbol_variable.type`

使用示例：

```python
import importlib

importlib.import_module("kernel_gen.symbol_variable")
```

约束：

- 旧路径导入必须失败。
- 包入口唯一有效前缀是 `kernel_gen.symbol_variable`。

## 测试分层

| 目标 | 用例 |
|---|---|
| 包入口可导入 | [`test_python_symbol_variable_imports`](../../test/symbol_variable/test_package_api.py) |
| 旧路径禁用 | [`test_legacy_import_disabled`](../../test/symbol_variable/test_package_api.py)、[`test_legacy_submodule_import_disabled`](../../test/symbol_variable/test_package_api.py) |
| 对象同一性 | [`test_python_package_type_exports`](../../test/symbol_variable/test_package_api.py) |
| 包入口稳定导出 / `import *` | [`test_python_package_exports_match_public_contract`](../../test/symbol_variable/test_package_api.py)、[`test_python_package_import_star_exports_only_public_names`](../../test/symbol_variable/test_package_api.py) |
