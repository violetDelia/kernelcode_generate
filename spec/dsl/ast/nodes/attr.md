# DSL AST 属性节点

## 功能简介

- `kernel_gen.dsl.ast.nodes.attr` 定义源码位置、诊断信息与属性类 AST 节点。
- 公开属性节点只承载类型、space、Python 元信息或普通列表/tuple；shape、stride、offset、size、perm 统一由 `SymbolListAST` 表示，不再公开 `ShapeListAST`、`ShapeAttrAST`、`StrideAttrAST`。

## API 列表

- `class SourceLocation(line: int, column: int)`
- `SourceLocation.from_py_ast(node: ast.AST) -> SourceLocation`
- `class Diagnostic(message: str, location: SourceLocation | None = None)`
- `class AttrAST(attr: Attribute, location: SourceLocation | None = None)`
- `class PythonObjectAttrAST(attr: PythonObjectAttrInput, location: SourceLocation | None = None)`
- `class ListAST(items: list[DSLNode], location: SourceLocation | None = None)`
- `class TupleAST(items: tuple[DSLNode, ...], location: SourceLocation | None = None)`
- `class IntTypeAttrAST(bits: int = 32, signed: bool = True, location: SourceLocation | None = None)`
- `class FloatTypeAttrAST(dtype: NumericType = NumericType.Float32, location: SourceLocation | None = None)`
- `class BoolTypeAttrAST(location: SourceLocation | None = None)`
- `class MemorySpaceAttrAST(space: MemorySpace, location: SourceLocation | None = None)`
- `MemorySpaceAttrAST.runtime_space_from_memory_type(memory_type: NnMemoryType) -> MemorySpace`

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：`spec/dsl/ast/nodes/attr.md`
- `功能实现`：`kernel_gen/dsl/ast/nodes/attr.py`
- `test`：`test/dsl/ast/nodes/test_attr.py`

## 依赖

- `xdsl.ir.Attribute`：`AttrAST` 承载的 MLIR attribute。
- `kernel_gen.symbol_variable.type.NumericType`：浮点类型属性输入来源。
- `kernel_gen.symbol_variable.type.Farmat`：format 元信息输入来源。
- `kernel_gen.symbol_variable.memory.MemorySpace`：memory space 属性输入来源。
- `kernel_gen.operation.arch.BarrierVisibility`：barrier visibility 元信息输入来源。
- `kernel_gen.operation.arch.BarrierScope`：barrier scope 元信息输入来源。
- `kernel_gen.dialect.nn.NnMemoryType`：`runtime_space_from_memory_type(...)` 的公开输入。
- `spec/dsl/ast/nodes/basic.md`：提供 `DSLNode`。

## 术语

- `PythonObjectAttrInput`：属性级 Python 元信息输入；稳定范围为 `str | int | float | bool | NumericType | Farmat | MemorySpace | BarrierVisibility | BarrierScope | type | Callable[..., DSLNode | None] | tuple[PythonObjectAttrInput, ...] | list[PythonObjectAttrInput] | None`。

## API详细说明

### `class SourceLocation(line: int, column: int)`

- api：`class SourceLocation(line: int, column: int)`
- 参数：
  - `line`：源码行号；类型 `int`；不允许 `None`。
  - `column`：源码列号；类型 `int`；不允许 `None`。
- 返回值：源码位置对象。
- 使用示例：

  ```python
  location = SourceLocation(1, 0)
  ```
- 功能说明：记录 Python AST 源码位置。
- 注意事项：`from_py_ast(...)` 只接受带 `lineno` 与 `col_offset` 的 Python AST 节点。

### `SourceLocation.from_py_ast(node: ast.AST) -> SourceLocation`

- api：`SourceLocation.from_py_ast(node: ast.AST) -> SourceLocation`
- 参数：
  - `node`：Python AST 节点；类型 `ast.AST`；必须带 `lineno` 与 `col_offset` 字段；不允许 `None`。
- 返回值：`SourceLocation`。
- 使用示例：

  ```python
  import ast
  from kernel_gen.dsl.ast.nodes.attr import SourceLocation

  node = ast.parse("x = 1").body[0]
  location = SourceLocation.from_py_ast(node)
  ```
- 功能说明：从 Python AST 标准位置字段构造 DSL AST 源码位置。
- 注意事项：缺少 `lineno` 或 `col_offset` 的节点不属于公开输入域；调用方不得依赖反射兜底。

### `class Diagnostic(message: str, location: SourceLocation | None = None)`

- api：`class Diagnostic(message: str, location: SourceLocation | None = None)`
- 参数：
  - `message`：诊断文本；类型 `str`；不允许空字符串。
  - `location`：源码位置；允许 `None`。
- 返回值：诊断对象。
- 使用示例：

  ```python
  diagnostic = Diagnostic("Missing runtime argument", SourceLocation(1, 0))
  ```
- 功能说明：保存 parser 或 emit 阶段的诊断信息。
- 注意事项：稳定错误文本由抛出 `KernelCodeError` 的调用点定义。

### `class AttrAST(attr: Attribute, location: SourceLocation | None = None)`

- api：`class AttrAST(attr: Attribute, location: SourceLocation | None = None)`
- 参数：
  - `attr`：xDSL attribute；类型 `Attribute`；不允许 `None`。
  - `location`：源码位置；允许 `None`。
- 返回值：`AttrAST`。
- 使用示例：

  ```python
  from xdsl.dialects.builtin import IntAttr
  from kernel_gen.dsl.ast.nodes.attr import AttrAST

  node = AttrAST(IntAttr(4))
  ```
- 功能说明：承载已经构造好的 xDSL attribute。
- 注意事项：本节点只表示属性级值；普通 DSL 值必须使用对应 value AST 节点。

### `class PythonObjectAttrAST(attr: PythonObjectAttrInput, location: SourceLocation | None = None)`

- api：`class PythonObjectAttrAST(attr: PythonObjectAttrInput, location: SourceLocation | None = None)`
- 参数：
  - `attr`：属性级 Python 元信息；类型 `PythonObjectAttrInput`；允许 `None` 仅用于显式表示缺省元信息。
  - `location`：源码位置；允许 `None`。
- 返回值：`PythonObjectAttrAST`。
- 使用示例：

  ```python
  from kernel_gen.dsl.ast.nodes.attr import PythonObjectAttrAST
  from kernel_gen.symbol_variable.type import Farmat

  node = PythonObjectAttrAST(Farmat.Norm)
  ```
- 功能说明：承载 parser 需要保留但不直接转成 xDSL attribute 的属性级 Python 元信息。
- 注意事项：`PythonObjectAttrAST` 不表示普通 DSL 值，不能替代 `ConstValueAST` 或 `BoolValueAST`；超出 `PythonObjectAttrInput` 稳定范围的输入不属于公开合同。

### `class ListAST(items: list[DSLNode], location: SourceLocation | None = None)`

- api：`class ListAST(items: list[DSLNode], location: SourceLocation | None = None)`
- 参数：
  - `items`：属性级列表成员；类型 `list[DSLNode]`；不允许 `None`；成员必须可按 DSL AST 节点处理。
  - `location`：源码位置；允许 `None`。
- 返回值：`ListAST`。
- 使用示例：

  ```python
  from kernel_gen.dsl.ast.nodes.attr import ListAST
  from kernel_gen.dsl.ast.nodes.symbol import ConstValueAST

  values = ListAST([ConstValueAST("axis"), ConstValueAST(1)])
  ```
- 功能说明：包装属性级列表结构，并在 emit 时逐项发射。
- 注意事项：shape、stride、offset、size、perm 必须使用 `SymbolListAST`。

### `class TupleAST(items: tuple[DSLNode, ...], location: SourceLocation | None = None)`

- api：`class TupleAST(items: tuple[DSLNode, ...], location: SourceLocation | None = None)`
- 参数：
  - `items`：属性级 tuple 成员；类型 `tuple[DSLNode, ...]`；不允许 `None`；成员必须可按 DSL AST 节点处理。
  - `location`：源码位置；允许 `None`。
- 返回值：`TupleAST`。
- 使用示例：

  ```python
  from kernel_gen.dsl.ast.nodes.attr import TupleAST
  from kernel_gen.dsl.ast.nodes.symbol import ConstValueAST

  pair = TupleAST((ConstValueAST("axis"), ConstValueAST(1)))
  ```
- 功能说明：包装属性级 tuple 结构，并在 emit 时逐项发射。
- 注意事项：shape、stride、offset、size、perm 必须使用 `SymbolListAST`。

### `class IntTypeAttrAST(bits: int = 32, signed: bool = True, location: SourceLocation | None = None)`

- api：`class IntTypeAttrAST(bits: int = 32, signed: bool = True, location: SourceLocation | None = None)`
- 参数：
  - `bits`：整数位宽；类型 `int`；默认 `32`；不允许 `None`。
  - `signed`：整数是否有符号；类型 `bool`；默认 `True`；不允许 `None`。
  - `location`：源码位置；允许 `None`。
- 返回值：`IntTypeAttrAST`；`emit_mlir(...)` 返回对应 xDSL integer type。
- 使用示例：

  ```python
  from kernel_gen.dsl.ast.nodes.attr import IntTypeAttrAST

  dtype = IntTypeAttrAST(bits=32, signed=True)
  ```
- 功能说明：替代旧 `DTypeAttrAST` 公开类型入口。
- 注意事项：仅承接整数类型属性；浮点与布尔类型必须使用对应 AST。

### `class FloatTypeAttrAST(dtype: NumericType = NumericType.Float32, location: SourceLocation | None = None)`

- api：`class FloatTypeAttrAST(dtype: NumericType = NumericType.Float32, location: SourceLocation | None = None)`
- 参数：
  - `dtype`：浮点类型；类型 `NumericType`；默认 `NumericType.Float32`；不允许 `None`。
  - `location`：源码位置；允许 `None`。
- 返回值：`FloatTypeAttrAST`；`emit_mlir(...)` 返回对应 xDSL floating point type。
- 使用示例：

  ```python
  from kernel_gen.dsl.ast.nodes.attr import FloatTypeAttrAST
  from kernel_gen.symbol_variable.type import NumericType

  dtype = FloatTypeAttrAST(NumericType.Float32)
  ```
- 功能说明：承载 DSL 浮点 dtype 属性。
- 注意事项：只接受公开 `NumericType` 浮点枚举成员；整数与布尔类型必须使用对应 AST。

### `class BoolTypeAttrAST(location: SourceLocation | None = None)`

- api：`class BoolTypeAttrAST(location: SourceLocation | None = None)`
- 参数：
  - `location`：源码位置；允许 `None`。
- 返回值：`BoolTypeAttrAST`；`emit_mlir(...)` 返回 `i1`。
- 使用示例：

  ```python
  from kernel_gen.dsl.ast.nodes.attr import BoolTypeAttrAST

  dtype = BoolTypeAttrAST()
  ```
- 功能说明：承载 DSL 布尔 dtype 属性。
- 注意事项：`BoolTypeAttrAST` 固定发射 `i1`。

### `class MemorySpaceAttrAST(space: MemorySpace, location: SourceLocation | None = None)`

- api：`class MemorySpaceAttrAST(space: MemorySpace, location: SourceLocation | None = None)`
- 参数：
  - `space`：runtime memory space；类型 `MemorySpace`。
  - `location`：源码位置；允许 `None`。
- 返回值：`MemorySpaceAttrAST`。
- 使用示例：

  ```python
  from kernel_gen.dsl.ast.nodes.attr import MemorySpaceAttrAST
  from kernel_gen.symbol_variable.memory import MemorySpace

  space = MemorySpaceAttrAST(MemorySpace.GM)
  ```
- 功能说明：承载 DSL memory space 属性并发射为 `NnMemorySpaceAttr`。
- 注意事项：不支持的 `MemorySpace` 必须抛出 `KernelCodeError`。

### `MemorySpaceAttrAST.runtime_space_from_memory_type(memory_type: NnMemoryType) -> MemorySpace`

- api：`MemorySpaceAttrAST.runtime_space_from_memory_type(memory_type: NnMemoryType) -> MemorySpace`
- 参数：
  - `memory_type`：xDSL `NnMemoryType`；不允许 `None`；必须携带可映射到 runtime `MemorySpace` 的公开 space attr。
- 返回值：`MemorySpace`。
- 使用示例：

  ```python
  from kernel_gen.dsl.ast.nodes.attr import MemorySpaceAttrAST

  runtime_space = MemorySpaceAttrAST.runtime_space_from_memory_type(memory_type)
  ```
- 功能说明：从 IR 层 `NnMemoryType` 还原 runtime `MemorySpace`。
- 注意事项：未映射或非法 memory space 必须抛出 `KernelCodeError`。

## 测试

- 测试文件：`test/dsl/ast/nodes/test_attr.py`
- 执行命令：`pytest -q test/dsl/ast/nodes/test_attr.py`

### 测试目标

- 源码位置、诊断、公开类型属性、space 属性和旧 attr 节点非公开化。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-NODES-ATTR-001 | 生成/编译 | attr source location and diagnostic store fields | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_attr_source_location_and_diagnostic_store_fields`。 | 生成源码、IR 文本或编译结果体现“attr source location and diagnostic store fields”场景。 | `test_attr_source_location_and_diagnostic_store_fields` |
| TC-DSL-AST-NODES-ATTR-002 | 生成/编译 | attr ast emits wrapped xdsl attribute | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_attr_ast_emits_wrapped_xdsl_attribute`。 | 生成源码、IR 文本或编译结果体现“attr ast emits wrapped xdsl attribute”场景。 | `test_attr_ast_emits_wrapped_xdsl_attribute` |
| TC-DSL-AST-NODES-ATTR-003 | 生成/编译 | specific attr nodes emit xdsl attrs | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_specific_attr_nodes_emit_xdsl_attrs`。 | 生成源码、IR 文本或编译结果体现“specific attr nodes emit xdsl attrs”场景。 | `test_specific_attr_nodes_emit_xdsl_attrs` |
| TC-DSL-AST-NODES-ATTR-004 | 执行结果 | memory space attr restores runtime space | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_memory_space_attr_restores_runtime_space`。 | 命令返回码、输出、执行结果或状态变更体现“memory space attr restores runtime space”场景。 | `test_memory_space_attr_restores_runtime_space` |
