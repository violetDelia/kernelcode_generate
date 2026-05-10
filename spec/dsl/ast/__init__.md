# DSL AST 包根 API

## 功能简介

- `kernel_gen.dsl.ast` 聚合 AST 节点、parser 与 MLIR 生成入口，提供稳定包根导入路径。
- 包根只导出当前公开节点与入口；旧节点名、旧 builder、旧 `kernel_gen.dsl.mlir_gen` 兼容路径不属于公开 API。

## API 列表

- `parse(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> ModuleAST`
- `parse_function(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> FunctionAST`
- `mlir_gen(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> ModuleOp`
- `class DslAstVisitor(fn: DslCallable, runtime_args: tuple[DslRuntimeArg, ...] = ())`
- `DSLNode: type[DSLNode]`
- `ValueAST: type[ValueAST]`
- `StatementAST: type[StatementAST]`
- `AttrAST: type[AttrAST]`
- `PythonObjectAttrAST: type[PythonObjectAttrAST]`
- `ListAST: type[ListAST]`
- `TupleAST: type[TupleAST]`
- `IntTypeAttrAST: type[IntTypeAttrAST]`
- `FloatTypeAttrAST: type[FloatTypeAttrAST]`
- `BoolTypeAttrAST: type[BoolTypeAttrAST]`
- `MemorySpaceAttrAST: type[MemorySpaceAttrAST]`
- `SourceLocation: type[SourceLocation]`
- `Diagnostic: type[Diagnostic]`
- `ModuleAST: type[ModuleAST]`
- `FunctionAST: type[FunctionAST]`
- `MemoryAST: type[MemoryAST]`
- `SymbolDimAST: type[SymbolDimAST]`
- `ConstValueAST: type[ConstValueAST]`
- `BoolValueAST: type[BoolValueAST]`
- `SymbolListAST: type[SymbolListAST]`
- `BlockAST: type[BlockAST]`
- `BoundExprAST: type[BoundExprAST]`
- `ReturnAST: type[ReturnAST]`
- `CallAST: type[CallAST]`
- `ForAST: type[ForAST]`
- `IfAST: type[IfAST]`
- `SymbolAddAST: type[SymbolAddAST]`
- `SymbolSubAST: type[SymbolSubAST]`
- `SymbolMulAST: type[SymbolMulAST]`
- `SymbolTrueDivAST: type[SymbolTrueDivAST]`
- `SymbolFloorDivAST: type[SymbolFloorDivAST]`
- `SymbolEqAST: type[SymbolEqAST]`
- `SymbolNeAST: type[SymbolNeAST]`
- `SymbolLtAST: type[SymbolLtAST]`
- `SymbolLeAST: type[SymbolLeAST]`
- `SymbolGtAST: type[SymbolGtAST]`
- `SymbolGeAST: type[SymbolGeAST]`
- `DmaAllocAST: type[DmaAllocAST]`
- `DmaCopyAST: type[DmaCopyAST]`
- `DmaCastAST: type[DmaCastAST]`
- `DmaViewAST: type[DmaViewAST]`
- `DmaReshapeAST: type[DmaReshapeAST]`
- `DmaFlattenAST: type[DmaFlattenAST]`
- `DmaFreeAST: type[DmaFreeAST]`
- `DmaFillAST: type[DmaFillAST]`
- `DmaLoadAST: type[DmaLoadAST]`
- `DmaSliceAST: type[DmaSliceAST]`
- `DmaStoreAST: type[DmaStoreAST]`
- `DmaDesliceAST: type[DmaDesliceAST]`
- `NnImg2Col1dAST: type[NnImg2Col1dAST]`
- `NnImg2Col2dAST: type[NnImg2Col2dAST]`
- `NnBroadcastAST: type[NnBroadcastAST]`
- `NnBroadcastToAST: type[NnBroadcastToAST]`
- `NnTransposeAST: type[NnTransposeAST]`
- `NnReluAST: type[NnReluAST]`
- `NnSigmoidAST: type[NnSigmoidAST]`
- `NnTanhAST: type[NnTanhAST]`
- `NnLeakyReluAST: type[NnLeakyReluAST]`
- `NnHardSigmoidAST: type[NnHardSigmoidAST]`
- `NnExpAST: type[NnExpAST]`
- `NnReduceAST: type[NnReduceAST]`
- `NnReduceSumAST: type[NnReduceSumAST]`
- `NnReduceMinAST: type[NnReduceMinAST]`
- `NnReduceMaxAST: type[NnReduceMaxAST]`
- `NnSoftmaxAST: type[NnSoftmaxAST]`
- `MatmulAST: type[MatmulAST]`
- `FCAST: type[FCAST]`
- `ConvAST: type[ConvAST]`
- `NnAddAST: type[NnAddAST]`
- `NnSubAST: type[NnSubAST]`
- `NnMulAST: type[NnMulAST]`
- `NnTrueDivAST: type[NnTrueDivAST]`
- `NnFloorDivAST: type[NnFloorDivAST]`
- `NnEqAST: type[NnEqAST]`
- `NnNeAST: type[NnNeAST]`
- `NnLtAST: type[NnLtAST]`
- `NnLeAST: type[NnLeAST]`
- `NnGtAST: type[NnGtAST]`
- `NnGeAST: type[NnGeAST]`
- `ArchQueryAST: type[ArchQueryAST]`
- `ArchGetBlockIdAST: type[ArchGetBlockIdAST]`
- `ArchGetBlockNumAST: type[ArchGetBlockNumAST]`
- `ArchGetSubthreadIdAST: type[ArchGetSubthreadIdAST]`
- `ArchGetSubthreadNumAST: type[ArchGetSubthreadNumAST]`
- `ArchGetThreadIdAST: type[ArchGetThreadIdAST]`
- `ArchGetThreadNumAST: type[ArchGetThreadNumAST]`
- `ArchGetDynamicMemoryAST: type[ArchGetDynamicMemoryAST]`
- `ArchBarrierAST: type[ArchBarrierAST]`
- `ArchLaunchKernelAST: type[ArchLaunchKernelAST]`
- `KernelBinaryElewiseAST: type[KernelBinaryElewiseAST]`
- `KernelAddAST: type[KernelAddAST]`
- `KernelSubAST: type[KernelSubAST]`
- `KernelMulAST: type[KernelMulAST]`
- `KernelDivAST: type[KernelDivAST]`
- `KernelTrueDivAST: type[KernelTrueDivAST]`
- `KernelEqAST: type[KernelEqAST]`
- `KernelNeAST: type[KernelNeAST]`
- `KernelLtAST: type[KernelLtAST]`
- `KernelLeAST: type[KernelLeAST]`
- `KernelGtAST: type[KernelGtAST]`
- `KernelGeAST: type[KernelGeAST]`
- `KernelMatmulAST: type[KernelMatmulAST]`
- `KernelImg2Col1dAST: type[KernelImg2Col1dAST]`
- `KernelImg2Col2dAST: type[KernelImg2Col2dAST]`

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：`spec/dsl/ast/__init__.md`
- `功能实现`：`kernel_gen/dsl/ast/__init__.py`
- `test`：`test/dsl/ast/test_package.py`

## 依赖

- `spec/dsl/ast/parser.md`：`parse(...)` 与 `parse_function(...)`。
- `spec/dsl/ast/mlir_gen.md`：`mlir_gen(...)`。
- `spec/dsl/ast/nodes/__init__.md`：公开节点聚合。
- `spec/dsl/ast/dsl_ast.md`：`DslAstVisitor`。
- `spec/dsl/ast/nodes/kernel.md`：kernel out-first AST 节点。

## API详细说明

### `parse(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> ModuleAST`

- api：`parse(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> ModuleAST`
- 参数：
  - `fn`：DSL Python 函数；类型 `Callable[..., DslFunctionReturn]`；无默认值；不允许 None；函数源码必须可被公开 parser 读取。
  - `runtime_args`：运行时参数序列；类型 `tuple[DslRuntimeArg, ...]`；无默认值；默认值为空 tuple；每个参数必须是公开 DSL runtime 支持的类型。
- 返回值：`ModuleAST`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import parse

    module_ast = parse(kernel, lhs, rhs)
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `parse`，提供 DSL AST 解析、visitor 或 MLIR 生成公开入口。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `parse_function(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> FunctionAST`

- api：`parse_function(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> FunctionAST`
- 参数：
  - `fn`：DSL Python 函数；类型 `Callable[..., DslFunctionReturn]`；无默认值；不允许 None；函数源码必须可被公开 parser 读取。
  - `runtime_args`：运行时参数序列；类型 `tuple[DslRuntimeArg, ...]`；无默认值；默认值为空 tuple；每个参数必须是公开 DSL runtime 支持的类型。
- 返回值：`FunctionAST`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import parse_function

    function_ast = parse_function(kernel, lhs, rhs)
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `parse_function`，提供 DSL AST 解析、visitor 或 MLIR 生成公开入口。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `mlir_gen(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> ModuleOp`

- api：`mlir_gen(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> ModuleOp`
- 参数：
  - `fn`：DSL Python 函数；类型 `Callable[..., DslFunctionReturn]`；无默认值；不允许 None；函数源码必须可被公开 parser 读取。
  - `runtime_args`：运行时参数序列；类型 `tuple[DslRuntimeArg, ...]`；无默认值；默认值为空 tuple；每个参数必须是公开 DSL runtime 支持的类型。
- 返回值：`ModuleOp`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import mlir_gen

    module_op = mlir_gen(kernel, lhs, rhs)
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `mlir_gen`，提供 DSL AST 解析、visitor 或 MLIR 生成公开入口。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `class DslAstVisitor(fn: DslCallable, runtime_args: tuple[DslRuntimeArg, ...] = ())`

- api：`class DslAstVisitor(fn: DslCallable, runtime_args: tuple[DslRuntimeArg, ...] = ())`
- 参数：
  - `fn`：DSL Python 函数；类型 `DslCallable`；无默认值；不允许 None；函数源码必须可被公开 parser 读取。
  - `runtime_args`：运行时参数序列；类型 `tuple[DslRuntimeArg, ...]`；默认值 `()`；默认值为空 tuple；每个参数必须是公开 DSL runtime 支持的类型。
- 返回值：`DslAstVisitor` 实例。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import DslAstVisitor

    visitor = DslAstVisitor(kernel, runtime_args=(lhs, rhs))
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `DslAstVisitor`，提供 DSL AST 解析、visitor 或 MLIR 生成公开入口。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DSLNode: type[DSLNode]`

- api：`DSLNode: type[DSLNode]`
- 参数：无。
- 返回值：`type[DSLNode]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import DSLNode

    exported = DSLNode
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `DSLNode`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ValueAST: type[ValueAST]`

- api：`ValueAST: type[ValueAST]`
- 参数：无。
- 返回值：`type[ValueAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import ValueAST

    exported = ValueAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `ValueAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `StatementAST: type[StatementAST]`

- api：`StatementAST: type[StatementAST]`
- 参数：无。
- 返回值：`type[StatementAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import StatementAST

    exported = StatementAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `StatementAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `AttrAST: type[AttrAST]`

- api：`AttrAST: type[AttrAST]`
- 参数：无。
- 返回值：`type[AttrAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import AttrAST

    exported = AttrAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `AttrAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `PythonObjectAttrAST: type[PythonObjectAttrAST]`

- api：`PythonObjectAttrAST: type[PythonObjectAttrAST]`
- 参数：无。
- 返回值：`type[PythonObjectAttrAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import PythonObjectAttrAST

    exported = PythonObjectAttrAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `PythonObjectAttrAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ListAST: type[ListAST]`

- api：`ListAST: type[ListAST]`
- 参数：无。
- 返回值：`type[ListAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import ListAST

    exported = ListAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `ListAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `TupleAST: type[TupleAST]`

- api：`TupleAST: type[TupleAST]`
- 参数：无。
- 返回值：`type[TupleAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import TupleAST

    exported = TupleAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `TupleAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `IntTypeAttrAST: type[IntTypeAttrAST]`

- api：`IntTypeAttrAST: type[IntTypeAttrAST]`
- 参数：无。
- 返回值：`type[IntTypeAttrAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import IntTypeAttrAST

    exported = IntTypeAttrAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `IntTypeAttrAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `FloatTypeAttrAST: type[FloatTypeAttrAST]`

- api：`FloatTypeAttrAST: type[FloatTypeAttrAST]`
- 参数：无。
- 返回值：`type[FloatTypeAttrAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import FloatTypeAttrAST

    exported = FloatTypeAttrAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `FloatTypeAttrAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `BoolTypeAttrAST: type[BoolTypeAttrAST]`

- api：`BoolTypeAttrAST: type[BoolTypeAttrAST]`
- 参数：无。
- 返回值：`type[BoolTypeAttrAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import BoolTypeAttrAST

    exported = BoolTypeAttrAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `BoolTypeAttrAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `MemorySpaceAttrAST: type[MemorySpaceAttrAST]`

- api：`MemorySpaceAttrAST: type[MemorySpaceAttrAST]`
- 参数：无。
- 返回值：`type[MemorySpaceAttrAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import MemorySpaceAttrAST

    exported = MemorySpaceAttrAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `MemorySpaceAttrAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SourceLocation: type[SourceLocation]`

- api：`SourceLocation: type[SourceLocation]`
- 参数：无。
- 返回值：`type[SourceLocation]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import SourceLocation

    exported = SourceLocation
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `SourceLocation`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `Diagnostic: type[Diagnostic]`

- api：`Diagnostic: type[Diagnostic]`
- 参数：无。
- 返回值：`type[Diagnostic]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import Diagnostic

    exported = Diagnostic
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `Diagnostic`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ModuleAST: type[ModuleAST]`

- api：`ModuleAST: type[ModuleAST]`
- 参数：无。
- 返回值：`type[ModuleAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import ModuleAST

    exported = ModuleAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `ModuleAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `FunctionAST: type[FunctionAST]`

- api：`FunctionAST: type[FunctionAST]`
- 参数：无。
- 返回值：`type[FunctionAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import FunctionAST

    exported = FunctionAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `FunctionAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `MemoryAST: type[MemoryAST]`

- api：`MemoryAST: type[MemoryAST]`
- 参数：无。
- 返回值：`type[MemoryAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import MemoryAST

    exported = MemoryAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `MemoryAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolDimAST: type[SymbolDimAST]`

- api：`SymbolDimAST: type[SymbolDimAST]`
- 参数：无。
- 返回值：`type[SymbolDimAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import SymbolDimAST

    exported = SymbolDimAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `SymbolDimAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ConstValueAST: type[ConstValueAST]`

- api：`ConstValueAST: type[ConstValueAST]`
- 参数：无。
- 返回值：`type[ConstValueAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import ConstValueAST

    exported = ConstValueAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `ConstValueAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `BoolValueAST: type[BoolValueAST]`

- api：`BoolValueAST: type[BoolValueAST]`
- 参数：无。
- 返回值：`type[BoolValueAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import BoolValueAST

    exported = BoolValueAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `BoolValueAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolListAST: type[SymbolListAST]`

- api：`SymbolListAST: type[SymbolListAST]`
- 参数：无。
- 返回值：`type[SymbolListAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import SymbolListAST

    exported = SymbolListAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `SymbolListAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `BlockAST: type[BlockAST]`

- api：`BlockAST: type[BlockAST]`
- 参数：无。
- 返回值：`type[BlockAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import BlockAST

    exported = BlockAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `BlockAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `BoundExprAST: type[BoundExprAST]`

- api：`BoundExprAST: type[BoundExprAST]`
- 参数：无。
- 返回值：`type[BoundExprAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import BoundExprAST

    exported = BoundExprAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `BoundExprAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ReturnAST: type[ReturnAST]`

- api：`ReturnAST: type[ReturnAST]`
- 参数：无。
- 返回值：`type[ReturnAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import ReturnAST

    exported = ReturnAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `ReturnAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `CallAST: type[CallAST]`

- api：`CallAST: type[CallAST]`
- 参数：无。
- 返回值：`type[CallAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import CallAST

    exported = CallAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `CallAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ForAST: type[ForAST]`

- api：`ForAST: type[ForAST]`
- 参数：无。
- 返回值：`type[ForAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import ForAST

    exported = ForAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `ForAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `IfAST: type[IfAST]`

- api：`IfAST: type[IfAST]`
- 参数：无。
- 返回值：`type[IfAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import IfAST

    exported = IfAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `IfAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolAddAST: type[SymbolAddAST]`

- api：`SymbolAddAST: type[SymbolAddAST]`
- 参数：无。
- 返回值：`type[SymbolAddAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import SymbolAddAST

    exported = SymbolAddAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `SymbolAddAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolSubAST: type[SymbolSubAST]`

- api：`SymbolSubAST: type[SymbolSubAST]`
- 参数：无。
- 返回值：`type[SymbolSubAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import SymbolSubAST

    exported = SymbolSubAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `SymbolSubAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolMulAST: type[SymbolMulAST]`

- api：`SymbolMulAST: type[SymbolMulAST]`
- 参数：无。
- 返回值：`type[SymbolMulAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import SymbolMulAST

    exported = SymbolMulAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `SymbolMulAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolTrueDivAST: type[SymbolTrueDivAST]`

- api：`SymbolTrueDivAST: type[SymbolTrueDivAST]`
- 参数：无。
- 返回值：`type[SymbolTrueDivAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import SymbolTrueDivAST

    exported = SymbolTrueDivAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `SymbolTrueDivAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolFloorDivAST: type[SymbolFloorDivAST]`

- api：`SymbolFloorDivAST: type[SymbolFloorDivAST]`
- 参数：无。
- 返回值：`type[SymbolFloorDivAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import SymbolFloorDivAST

    exported = SymbolFloorDivAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `SymbolFloorDivAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolEqAST: type[SymbolEqAST]`

- api：`SymbolEqAST: type[SymbolEqAST]`
- 参数：无。
- 返回值：`type[SymbolEqAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import SymbolEqAST

    exported = SymbolEqAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `SymbolEqAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolNeAST: type[SymbolNeAST]`

- api：`SymbolNeAST: type[SymbolNeAST]`
- 参数：无。
- 返回值：`type[SymbolNeAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import SymbolNeAST

    exported = SymbolNeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `SymbolNeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolLtAST: type[SymbolLtAST]`

- api：`SymbolLtAST: type[SymbolLtAST]`
- 参数：无。
- 返回值：`type[SymbolLtAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import SymbolLtAST

    exported = SymbolLtAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `SymbolLtAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolLeAST: type[SymbolLeAST]`

- api：`SymbolLeAST: type[SymbolLeAST]`
- 参数：无。
- 返回值：`type[SymbolLeAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import SymbolLeAST

    exported = SymbolLeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `SymbolLeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolGtAST: type[SymbolGtAST]`

- api：`SymbolGtAST: type[SymbolGtAST]`
- 参数：无。
- 返回值：`type[SymbolGtAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import SymbolGtAST

    exported = SymbolGtAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `SymbolGtAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolGeAST: type[SymbolGeAST]`

- api：`SymbolGeAST: type[SymbolGeAST]`
- 参数：无。
- 返回值：`type[SymbolGeAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import SymbolGeAST

    exported = SymbolGeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `SymbolGeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaAllocAST: type[DmaAllocAST]`

- api：`DmaAllocAST: type[DmaAllocAST]`
- 参数：无。
- 返回值：`type[DmaAllocAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import DmaAllocAST

    exported = DmaAllocAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `DmaAllocAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaCopyAST: type[DmaCopyAST]`

- api：`DmaCopyAST: type[DmaCopyAST]`
- 参数：无。
- 返回值：`type[DmaCopyAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import DmaCopyAST

    exported = DmaCopyAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `DmaCopyAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaCastAST: type[DmaCastAST]`

- api：`DmaCastAST: type[DmaCastAST]`
- 参数：无。
- 返回值：`type[DmaCastAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import DmaCastAST

    exported = DmaCastAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `DmaCastAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaViewAST: type[DmaViewAST]`

- api：`DmaViewAST: type[DmaViewAST]`
- 参数：无。
- 返回值：`type[DmaViewAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import DmaViewAST

    exported = DmaViewAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `DmaViewAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaReshapeAST: type[DmaReshapeAST]`

- api：`DmaReshapeAST: type[DmaReshapeAST]`
- 参数：无。
- 返回值：`type[DmaReshapeAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import DmaReshapeAST

    exported = DmaReshapeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `DmaReshapeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaFlattenAST: type[DmaFlattenAST]`

- api：`DmaFlattenAST: type[DmaFlattenAST]`
- 参数：无。
- 返回值：`type[DmaFlattenAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import DmaFlattenAST

    exported = DmaFlattenAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `DmaFlattenAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaFreeAST: type[DmaFreeAST]`

- api：`DmaFreeAST: type[DmaFreeAST]`
- 参数：无。
- 返回值：`type[DmaFreeAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import DmaFreeAST

    exported = DmaFreeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `DmaFreeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaFillAST: type[DmaFillAST]`

- api：`DmaFillAST: type[DmaFillAST]`
- 参数：无。
- 返回值：`type[DmaFillAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import DmaFillAST

    exported = DmaFillAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `DmaFillAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaLoadAST: type[DmaLoadAST]`

- api：`DmaLoadAST: type[DmaLoadAST]`
- 参数：无。
- 返回值：`type[DmaLoadAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import DmaLoadAST

    exported = DmaLoadAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `DmaLoadAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaSliceAST: type[DmaSliceAST]`

- api：`DmaSliceAST: type[DmaSliceAST]`
- 参数：无。
- 返回值：`type[DmaSliceAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import DmaSliceAST

    exported = DmaSliceAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `DmaSliceAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaStoreAST: type[DmaStoreAST]`

- api：`DmaStoreAST: type[DmaStoreAST]`
- 参数：无。
- 返回值：`type[DmaStoreAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import DmaStoreAST

    exported = DmaStoreAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `DmaStoreAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaDesliceAST: type[DmaDesliceAST]`

- api：`DmaDesliceAST: type[DmaDesliceAST]`
- 参数：无。
- 返回值：`type[DmaDesliceAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import DmaDesliceAST

    exported = DmaDesliceAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `DmaDesliceAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnImg2Col1dAST: type[NnImg2Col1dAST]`

- api：`NnImg2Col1dAST: type[NnImg2Col1dAST]`
- 参数：无。
- 返回值：`type[NnImg2Col1dAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnImg2Col1dAST

    exported = NnImg2Col1dAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnImg2Col1dAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnImg2Col2dAST: type[NnImg2Col2dAST]`

- api：`NnImg2Col2dAST: type[NnImg2Col2dAST]`
- 参数：无。
- 返回值：`type[NnImg2Col2dAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnImg2Col2dAST

    exported = NnImg2Col2dAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnImg2Col2dAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnBroadcastAST: type[NnBroadcastAST]`

- api：`NnBroadcastAST: type[NnBroadcastAST]`
- 参数：无。
- 返回值：`type[NnBroadcastAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnBroadcastAST

    exported = NnBroadcastAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnBroadcastAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnBroadcastToAST: type[NnBroadcastToAST]`

- api：`NnBroadcastToAST: type[NnBroadcastToAST]`
- 参数：无。
- 返回值：`type[NnBroadcastToAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnBroadcastToAST

    exported = NnBroadcastToAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnBroadcastToAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnTransposeAST: type[NnTransposeAST]`

- api：`NnTransposeAST: type[NnTransposeAST]`
- 参数：无。
- 返回值：`type[NnTransposeAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnTransposeAST

    exported = NnTransposeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnTransposeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnReluAST: type[NnReluAST]`

- api：`NnReluAST: type[NnReluAST]`
- 参数：无。
- 返回值：`type[NnReluAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnReluAST

    exported = NnReluAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnReluAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnSigmoidAST: type[NnSigmoidAST]`

- api：`NnSigmoidAST: type[NnSigmoidAST]`
- 参数：无。
- 返回值：`type[NnSigmoidAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnSigmoidAST

    exported = NnSigmoidAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnSigmoidAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnTanhAST: type[NnTanhAST]`

- api：`NnTanhAST: type[NnTanhAST]`
- 参数：无。
- 返回值：`type[NnTanhAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnTanhAST

    exported = NnTanhAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnTanhAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnLeakyReluAST: type[NnLeakyReluAST]`

- api：`NnLeakyReluAST: type[NnLeakyReluAST]`
- 参数：无。
- 返回值：`type[NnLeakyReluAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnLeakyReluAST

    exported = NnLeakyReluAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnLeakyReluAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnHardSigmoidAST: type[NnHardSigmoidAST]`

- api：`NnHardSigmoidAST: type[NnHardSigmoidAST]`
- 参数：无。
- 返回值：`type[NnHardSigmoidAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnHardSigmoidAST

    exported = NnHardSigmoidAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnHardSigmoidAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnExpAST: type[NnExpAST]`

- api：`NnExpAST: type[NnExpAST]`
- 参数：无。
- 返回值：`type[NnExpAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnExpAST

    exported = NnExpAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnExpAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnReduceAST: type[NnReduceAST]`

- api：`NnReduceAST: type[NnReduceAST]`
- 参数：无。
- 返回值：`type[NnReduceAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnReduceAST

    exported = NnReduceAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnReduceAST`，作为 reduce family 的公开共享基类。
- 注意事项：包根只承诺导出本条目声明的公开对象；具体 reduce operation 仍由 `NnReduceSumAST`、`NnReduceMinAST`、`NnReduceMaxAST` 承接。

### `NnReduceSumAST: type[NnReduceSumAST]`

- api：`NnReduceSumAST: type[NnReduceSumAST]`
- 参数：无。
- 返回值：`type[NnReduceSumAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnReduceSumAST

    exported = NnReduceSumAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnReduceSumAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnReduceMinAST: type[NnReduceMinAST]`

- api：`NnReduceMinAST: type[NnReduceMinAST]`
- 参数：无。
- 返回值：`type[NnReduceMinAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnReduceMinAST

    exported = NnReduceMinAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnReduceMinAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnReduceMaxAST: type[NnReduceMaxAST]`

- api：`NnReduceMaxAST: type[NnReduceMaxAST]`
- 参数：无。
- 返回值：`type[NnReduceMaxAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnReduceMaxAST

    exported = NnReduceMaxAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnReduceMaxAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnSoftmaxAST: type[NnSoftmaxAST]`

- api：`NnSoftmaxAST: type[NnSoftmaxAST]`
- 参数：无。
- 返回值：`type[NnSoftmaxAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnSoftmaxAST

    exported = NnSoftmaxAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnSoftmaxAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `MatmulAST: type[MatmulAST]`

- api：`MatmulAST: type[MatmulAST]`
- 参数：无。
- 返回值：`type[MatmulAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import MatmulAST

    exported = MatmulAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `MatmulAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `FCAST: type[FCAST]`

- api：`FCAST: type[FCAST]`
- 参数：无。
- 返回值：`type[FCAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import FCAST

    exported = FCAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `FCAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ConvAST: type[ConvAST]`

- api：`ConvAST: type[ConvAST]`
- 参数：无。
- 返回值：`type[ConvAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import ConvAST

    exported = ConvAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `ConvAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnAddAST: type[NnAddAST]`

- api：`NnAddAST: type[NnAddAST]`
- 参数：无。
- 返回值：`type[NnAddAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnAddAST

    exported = NnAddAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnAddAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnSubAST: type[NnSubAST]`

- api：`NnSubAST: type[NnSubAST]`
- 参数：无。
- 返回值：`type[NnSubAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnSubAST

    exported = NnSubAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnSubAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnMulAST: type[NnMulAST]`

- api：`NnMulAST: type[NnMulAST]`
- 参数：无。
- 返回值：`type[NnMulAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnMulAST

    exported = NnMulAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnMulAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnTrueDivAST: type[NnTrueDivAST]`

- api：`NnTrueDivAST: type[NnTrueDivAST]`
- 参数：无。
- 返回值：`type[NnTrueDivAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnTrueDivAST

    exported = NnTrueDivAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnTrueDivAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnFloorDivAST: type[NnFloorDivAST]`

- api：`NnFloorDivAST: type[NnFloorDivAST]`
- 参数：无。
- 返回值：`type[NnFloorDivAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnFloorDivAST

    exported = NnFloorDivAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnFloorDivAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnEqAST: type[NnEqAST]`

- api：`NnEqAST: type[NnEqAST]`
- 参数：无。
- 返回值：`type[NnEqAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnEqAST

    exported = NnEqAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnEqAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnNeAST: type[NnNeAST]`

- api：`NnNeAST: type[NnNeAST]`
- 参数：无。
- 返回值：`type[NnNeAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnNeAST

    exported = NnNeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnNeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnLtAST: type[NnLtAST]`

- api：`NnLtAST: type[NnLtAST]`
- 参数：无。
- 返回值：`type[NnLtAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnLtAST

    exported = NnLtAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnLtAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnLeAST: type[NnLeAST]`

- api：`NnLeAST: type[NnLeAST]`
- 参数：无。
- 返回值：`type[NnLeAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnLeAST

    exported = NnLeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnLeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnGtAST: type[NnGtAST]`

- api：`NnGtAST: type[NnGtAST]`
- 参数：无。
- 返回值：`type[NnGtAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnGtAST

    exported = NnGtAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnGtAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnGeAST: type[NnGeAST]`

- api：`NnGeAST: type[NnGeAST]`
- 参数：无。
- 返回值：`type[NnGeAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import NnGeAST

    exported = NnGeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `NnGeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchQueryAST: type[ArchQueryAST]`

- api：`ArchQueryAST: type[ArchQueryAST]`
- 参数：无。
- 返回值：`type[ArchQueryAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import ArchQueryAST

    exported = ArchQueryAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `ArchQueryAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchGetBlockIdAST: type[ArchGetBlockIdAST]`

- api：`ArchGetBlockIdAST: type[ArchGetBlockIdAST]`
- 参数：无。
- 返回值：`type[ArchGetBlockIdAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import ArchGetBlockIdAST

    exported = ArchGetBlockIdAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `ArchGetBlockIdAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchGetBlockNumAST: type[ArchGetBlockNumAST]`

- api：`ArchGetBlockNumAST: type[ArchGetBlockNumAST]`
- 参数：无。
- 返回值：`type[ArchGetBlockNumAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import ArchGetBlockNumAST

    exported = ArchGetBlockNumAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `ArchGetBlockNumAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchGetSubthreadIdAST: type[ArchGetSubthreadIdAST]`

- api：`ArchGetSubthreadIdAST: type[ArchGetSubthreadIdAST]`
- 参数：无。
- 返回值：`type[ArchGetSubthreadIdAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import ArchGetSubthreadIdAST

    exported = ArchGetSubthreadIdAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `ArchGetSubthreadIdAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchGetSubthreadNumAST: type[ArchGetSubthreadNumAST]`

- api：`ArchGetSubthreadNumAST: type[ArchGetSubthreadNumAST]`
- 参数：无。
- 返回值：`type[ArchGetSubthreadNumAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import ArchGetSubthreadNumAST

    exported = ArchGetSubthreadNumAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `ArchGetSubthreadNumAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchGetThreadIdAST: type[ArchGetThreadIdAST]`

- api：`ArchGetThreadIdAST: type[ArchGetThreadIdAST]`
- 参数：无。
- 返回值：`type[ArchGetThreadIdAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import ArchGetThreadIdAST

    exported = ArchGetThreadIdAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `ArchGetThreadIdAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchGetThreadNumAST: type[ArchGetThreadNumAST]`

- api：`ArchGetThreadNumAST: type[ArchGetThreadNumAST]`
- 参数：无。
- 返回值：`type[ArchGetThreadNumAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import ArchGetThreadNumAST

    exported = ArchGetThreadNumAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `ArchGetThreadNumAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchGetDynamicMemoryAST: type[ArchGetDynamicMemoryAST]`

- api：`ArchGetDynamicMemoryAST: type[ArchGetDynamicMemoryAST]`
- 参数：无。
- 返回值：`type[ArchGetDynamicMemoryAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import ArchGetDynamicMemoryAST

    exported = ArchGetDynamicMemoryAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `ArchGetDynamicMemoryAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchBarrierAST: type[ArchBarrierAST]`

- api：`ArchBarrierAST: type[ArchBarrierAST]`
- 参数：无。
- 返回值：`type[ArchBarrierAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import ArchBarrierAST

    exported = ArchBarrierAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `ArchBarrierAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchLaunchKernelAST: type[ArchLaunchKernelAST]`

- api：`ArchLaunchKernelAST: type[ArchLaunchKernelAST]`
- 参数：无。
- 返回值：`type[ArchLaunchKernelAST]`；表示从 `kernel_gen.dsl.ast` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast import ArchLaunchKernelAST

    exported = ArchLaunchKernelAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast` 包根导出 `ArchLaunchKernelAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

## 测试

- 测试文件：`test/dsl/ast/test_package.py`
- 执行命令：`pytest -q test/dsl/ast/test_package.py`

### 测试目标

- 包根公开 API 导出边界。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-001 | 公开入口 | ast package exports only current public nodes | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_ast_package_exports_only_current_public_nodes`。 | 公开入口在“ast package exports only current public nodes”场景下可导入、构造、注册或按名称发现。 | `test_ast_package_exports_only_current_public_nodes` |
