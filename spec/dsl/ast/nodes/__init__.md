# DSL AST 节点包根

## 功能简介

- `kernel_gen.dsl.ast.nodes` 聚合 `attr`、`basic`、`symbol`、`control_flow`、`dma`、`nn`、`arch` 中的公开节点类。
- 本文件只定义节点 facade 合同，不定义节点行为；节点行为分别见对应子 spec。

## API 列表

- `DSLNode: type[DSLNode]`
- `ValueAST: type[ValueAST]`
- `StatementAST: type[StatementAST]`
- `SourceLocation: type[SourceLocation]`
- `Diagnostic: type[Diagnostic]`
- `AttrAST: type[AttrAST]`
- `PythonObjectAttrAST: type[PythonObjectAttrAST]`
- `ListAST: type[ListAST]`
- `TupleAST: type[TupleAST]`
- `IntTypeAttrAST: type[IntTypeAttrAST]`
- `FloatTypeAttrAST: type[FloatTypeAttrAST]`
- `BoolTypeAttrAST: type[BoolTypeAttrAST]`
- `MemorySpaceAttrAST: type[MemorySpaceAttrAST]`
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
- `SymbolMinAST: type[SymbolMinAST]`
- `SymbolMaxAST: type[SymbolMaxAST]`
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
- `spec`：`spec/dsl/ast/nodes/__init__.md`
- `功能实现`：`kernel_gen/dsl/ast/nodes/__init__.py`
- `test`：`test/dsl/ast/nodes/test_package.py`

## 依赖

- `spec/dsl/ast/nodes/attr.md`：属性节点。
- `spec/dsl/ast/nodes/basic.md`：基础和值/语句节点。
- `spec/dsl/ast/nodes/symbol.md`：Symbol dialect 节点。
- `spec/dsl/ast/nodes/control_flow.md`：控制流节点。
- `spec/dsl/ast/nodes/dma.md`：DMA 节点。
- `spec/dsl/ast/nodes/nn.md`：NN 节点。
- `spec/dsl/ast/nodes/arch.md`：Arch 节点。
- `spec/dsl/ast/nodes/kernel.md`：Kernel out-first 节点。

## API详细说明

### `DSLNode: type[DSLNode]`

- api：`DSLNode: type[DSLNode]`
- 参数：无。
- 返回值：`type[DSLNode]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import DSLNode

    exported = DSLNode
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `DSLNode`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ValueAST: type[ValueAST]`

- api：`ValueAST: type[ValueAST]`
- 参数：无。
- 返回值：`type[ValueAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import ValueAST

    exported = ValueAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `ValueAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `StatementAST: type[StatementAST]`

- api：`StatementAST: type[StatementAST]`
- 参数：无。
- 返回值：`type[StatementAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import StatementAST

    exported = StatementAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `StatementAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SourceLocation: type[SourceLocation]`

- api：`SourceLocation: type[SourceLocation]`
- 参数：无。
- 返回值：`type[SourceLocation]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import SourceLocation

    exported = SourceLocation
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `SourceLocation`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `Diagnostic: type[Diagnostic]`

- api：`Diagnostic: type[Diagnostic]`
- 参数：无。
- 返回值：`type[Diagnostic]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import Diagnostic

    exported = Diagnostic
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `Diagnostic`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `AttrAST: type[AttrAST]`

- api：`AttrAST: type[AttrAST]`
- 参数：无。
- 返回值：`type[AttrAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import AttrAST

    exported = AttrAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `AttrAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `PythonObjectAttrAST: type[PythonObjectAttrAST]`

- api：`PythonObjectAttrAST: type[PythonObjectAttrAST]`
- 参数：无。
- 返回值：`type[PythonObjectAttrAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import PythonObjectAttrAST

    exported = PythonObjectAttrAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `PythonObjectAttrAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ListAST: type[ListAST]`

- api：`ListAST: type[ListAST]`
- 参数：无。
- 返回值：`type[ListAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import ListAST

    exported = ListAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `ListAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `TupleAST: type[TupleAST]`

- api：`TupleAST: type[TupleAST]`
- 参数：无。
- 返回值：`type[TupleAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import TupleAST

    exported = TupleAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `TupleAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `IntTypeAttrAST: type[IntTypeAttrAST]`

- api：`IntTypeAttrAST: type[IntTypeAttrAST]`
- 参数：无。
- 返回值：`type[IntTypeAttrAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import IntTypeAttrAST

    exported = IntTypeAttrAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `IntTypeAttrAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `FloatTypeAttrAST: type[FloatTypeAttrAST]`

- api：`FloatTypeAttrAST: type[FloatTypeAttrAST]`
- 参数：无。
- 返回值：`type[FloatTypeAttrAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import FloatTypeAttrAST

    exported = FloatTypeAttrAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `FloatTypeAttrAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `BoolTypeAttrAST: type[BoolTypeAttrAST]`

- api：`BoolTypeAttrAST: type[BoolTypeAttrAST]`
- 参数：无。
- 返回值：`type[BoolTypeAttrAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import BoolTypeAttrAST

    exported = BoolTypeAttrAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `BoolTypeAttrAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `MemorySpaceAttrAST: type[MemorySpaceAttrAST]`

- api：`MemorySpaceAttrAST: type[MemorySpaceAttrAST]`
- 参数：无。
- 返回值：`type[MemorySpaceAttrAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import MemorySpaceAttrAST

    exported = MemorySpaceAttrAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `MemorySpaceAttrAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ModuleAST: type[ModuleAST]`

- api：`ModuleAST: type[ModuleAST]`
- 参数：无。
- 返回值：`type[ModuleAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import ModuleAST

    exported = ModuleAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `ModuleAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `FunctionAST: type[FunctionAST]`

- api：`FunctionAST: type[FunctionAST]`
- 参数：无。
- 返回值：`type[FunctionAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import FunctionAST

    exported = FunctionAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `FunctionAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `MemoryAST: type[MemoryAST]`

- api：`MemoryAST: type[MemoryAST]`
- 参数：无。
- 返回值：`type[MemoryAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import MemoryAST

    exported = MemoryAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `MemoryAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolDimAST: type[SymbolDimAST]`

- api：`SymbolDimAST: type[SymbolDimAST]`
- 参数：无。
- 返回值：`type[SymbolDimAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import SymbolDimAST

    exported = SymbolDimAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `SymbolDimAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ConstValueAST: type[ConstValueAST]`

- api：`ConstValueAST: type[ConstValueAST]`
- 参数：无。
- 返回值：`type[ConstValueAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import ConstValueAST

    exported = ConstValueAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `ConstValueAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `BoolValueAST: type[BoolValueAST]`

- api：`BoolValueAST: type[BoolValueAST]`
- 参数：无。
- 返回值：`type[BoolValueAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import BoolValueAST

    exported = BoolValueAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `BoolValueAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolListAST: type[SymbolListAST]`

- api：`SymbolListAST: type[SymbolListAST]`
- 参数：无。
- 返回值：`type[SymbolListAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import SymbolListAST

    exported = SymbolListAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `SymbolListAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `BlockAST: type[BlockAST]`

- api：`BlockAST: type[BlockAST]`
- 参数：无。
- 返回值：`type[BlockAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import BlockAST

    exported = BlockAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `BlockAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `BoundExprAST: type[BoundExprAST]`

- api：`BoundExprAST: type[BoundExprAST]`
- 参数：无。
- 返回值：`type[BoundExprAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import BoundExprAST

    exported = BoundExprAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `BoundExprAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ReturnAST: type[ReturnAST]`

- api：`ReturnAST: type[ReturnAST]`
- 参数：无。
- 返回值：`type[ReturnAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import ReturnAST

    exported = ReturnAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `ReturnAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `CallAST: type[CallAST]`

- api：`CallAST: type[CallAST]`
- 参数：无。
- 返回值：`type[CallAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import CallAST

    exported = CallAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `CallAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ForAST: type[ForAST]`

- api：`ForAST: type[ForAST]`
- 参数：无。
- 返回值：`type[ForAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import ForAST

    exported = ForAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `ForAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `IfAST: type[IfAST]`

- api：`IfAST: type[IfAST]`
- 参数：无。
- 返回值：`type[IfAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import IfAST

    exported = IfAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `IfAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolAddAST: type[SymbolAddAST]`

- api：`SymbolAddAST: type[SymbolAddAST]`
- 参数：无。
- 返回值：`type[SymbolAddAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import SymbolAddAST

    exported = SymbolAddAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `SymbolAddAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolSubAST: type[SymbolSubAST]`

- api：`SymbolSubAST: type[SymbolSubAST]`
- 参数：无。
- 返回值：`type[SymbolSubAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import SymbolSubAST

    exported = SymbolSubAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `SymbolSubAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolMulAST: type[SymbolMulAST]`

- api：`SymbolMulAST: type[SymbolMulAST]`
- 参数：无。
- 返回值：`type[SymbolMulAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import SymbolMulAST

    exported = SymbolMulAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `SymbolMulAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolTrueDivAST: type[SymbolTrueDivAST]`

- api：`SymbolTrueDivAST: type[SymbolTrueDivAST]`
- 参数：无。
- 返回值：`type[SymbolTrueDivAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import SymbolTrueDivAST

    exported = SymbolTrueDivAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `SymbolTrueDivAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolFloorDivAST: type[SymbolFloorDivAST]`

- api：`SymbolFloorDivAST: type[SymbolFloorDivAST]`
- 参数：无。
- 返回值：`type[SymbolFloorDivAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import SymbolFloorDivAST

    exported = SymbolFloorDivAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `SymbolFloorDivAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolMinAST: type[SymbolMinAST]`

- api：`SymbolMinAST: type[SymbolMinAST]`
- 参数：无。
- 返回值：`type[SymbolMinAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import SymbolMinAST

    exported = SymbolMinAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `SymbolMinAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolMaxAST: type[SymbolMaxAST]`

- api：`SymbolMaxAST: type[SymbolMaxAST]`
- 参数：无。
- 返回值：`type[SymbolMaxAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import SymbolMaxAST

    exported = SymbolMaxAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `SymbolMaxAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolEqAST: type[SymbolEqAST]`

- api：`SymbolEqAST: type[SymbolEqAST]`
- 参数：无。
- 返回值：`type[SymbolEqAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import SymbolEqAST

    exported = SymbolEqAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `SymbolEqAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolNeAST: type[SymbolNeAST]`

- api：`SymbolNeAST: type[SymbolNeAST]`
- 参数：无。
- 返回值：`type[SymbolNeAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import SymbolNeAST

    exported = SymbolNeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `SymbolNeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolLtAST: type[SymbolLtAST]`

- api：`SymbolLtAST: type[SymbolLtAST]`
- 参数：无。
- 返回值：`type[SymbolLtAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import SymbolLtAST

    exported = SymbolLtAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `SymbolLtAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolLeAST: type[SymbolLeAST]`

- api：`SymbolLeAST: type[SymbolLeAST]`
- 参数：无。
- 返回值：`type[SymbolLeAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import SymbolLeAST

    exported = SymbolLeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `SymbolLeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolGtAST: type[SymbolGtAST]`

- api：`SymbolGtAST: type[SymbolGtAST]`
- 参数：无。
- 返回值：`type[SymbolGtAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import SymbolGtAST

    exported = SymbolGtAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `SymbolGtAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `SymbolGeAST: type[SymbolGeAST]`

- api：`SymbolGeAST: type[SymbolGeAST]`
- 参数：无。
- 返回值：`type[SymbolGeAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import SymbolGeAST

    exported = SymbolGeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `SymbolGeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaAllocAST: type[DmaAllocAST]`

- api：`DmaAllocAST: type[DmaAllocAST]`
- 参数：无。
- 返回值：`type[DmaAllocAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import DmaAllocAST

    exported = DmaAllocAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `DmaAllocAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaCopyAST: type[DmaCopyAST]`

- api：`DmaCopyAST: type[DmaCopyAST]`
- 参数：无。
- 返回值：`type[DmaCopyAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import DmaCopyAST

    exported = DmaCopyAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `DmaCopyAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaCastAST: type[DmaCastAST]`

- api：`DmaCastAST: type[DmaCastAST]`
- 参数：无。
- 返回值：`type[DmaCastAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import DmaCastAST

    exported = DmaCastAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `DmaCastAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaViewAST: type[DmaViewAST]`

- api：`DmaViewAST: type[DmaViewAST]`
- 参数：无。
- 返回值：`type[DmaViewAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import DmaViewAST

    exported = DmaViewAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `DmaViewAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaReshapeAST: type[DmaReshapeAST]`

- api：`DmaReshapeAST: type[DmaReshapeAST]`
- 参数：无。
- 返回值：`type[DmaReshapeAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import DmaReshapeAST

    exported = DmaReshapeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `DmaReshapeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaFlattenAST: type[DmaFlattenAST]`

- api：`DmaFlattenAST: type[DmaFlattenAST]`
- 参数：无。
- 返回值：`type[DmaFlattenAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import DmaFlattenAST

    exported = DmaFlattenAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `DmaFlattenAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaFreeAST: type[DmaFreeAST]`

- api：`DmaFreeAST: type[DmaFreeAST]`
- 参数：无。
- 返回值：`type[DmaFreeAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import DmaFreeAST

    exported = DmaFreeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `DmaFreeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaFillAST: type[DmaFillAST]`

- api：`DmaFillAST: type[DmaFillAST]`
- 参数：无。
- 返回值：`type[DmaFillAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import DmaFillAST

    exported = DmaFillAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `DmaFillAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaLoadAST: type[DmaLoadAST]`

- api：`DmaLoadAST: type[DmaLoadAST]`
- 参数：无。
- 返回值：`type[DmaLoadAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import DmaLoadAST

    exported = DmaLoadAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `DmaLoadAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaSliceAST: type[DmaSliceAST]`

- api：`DmaSliceAST: type[DmaSliceAST]`
- 参数：无。
- 返回值：`type[DmaSliceAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import DmaSliceAST

    exported = DmaSliceAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `DmaSliceAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaStoreAST: type[DmaStoreAST]`

- api：`DmaStoreAST: type[DmaStoreAST]`
- 参数：无。
- 返回值：`type[DmaStoreAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import DmaStoreAST

    exported = DmaStoreAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `DmaStoreAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `DmaDesliceAST: type[DmaDesliceAST]`

- api：`DmaDesliceAST: type[DmaDesliceAST]`
- 参数：无。
- 返回值：`type[DmaDesliceAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import DmaDesliceAST

    exported = DmaDesliceAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `DmaDesliceAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnImg2Col1dAST: type[NnImg2Col1dAST]`

- api：`NnImg2Col1dAST: type[NnImg2Col1dAST]`
- 参数：无。
- 返回值：`type[NnImg2Col1dAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnImg2Col1dAST

    exported = NnImg2Col1dAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnImg2Col1dAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnImg2Col2dAST: type[NnImg2Col2dAST]`

- api：`NnImg2Col2dAST: type[NnImg2Col2dAST]`
- 参数：无。
- 返回值：`type[NnImg2Col2dAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnImg2Col2dAST

    exported = NnImg2Col2dAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnImg2Col2dAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnBroadcastAST: type[NnBroadcastAST]`

- api：`NnBroadcastAST: type[NnBroadcastAST]`
- 参数：无。
- 返回值：`type[NnBroadcastAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnBroadcastAST

    exported = NnBroadcastAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnBroadcastAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnBroadcastToAST: type[NnBroadcastToAST]`

- api：`NnBroadcastToAST: type[NnBroadcastToAST]`
- 参数：无。
- 返回值：`type[NnBroadcastToAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnBroadcastToAST

    exported = NnBroadcastToAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnBroadcastToAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnTransposeAST: type[NnTransposeAST]`

- api：`NnTransposeAST: type[NnTransposeAST]`
- 参数：无。
- 返回值：`type[NnTransposeAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnTransposeAST

    exported = NnTransposeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnTransposeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnReluAST: type[NnReluAST]`

- api：`NnReluAST: type[NnReluAST]`
- 参数：无。
- 返回值：`type[NnReluAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnReluAST

    exported = NnReluAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnReluAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnSigmoidAST: type[NnSigmoidAST]`

- api：`NnSigmoidAST: type[NnSigmoidAST]`
- 参数：无。
- 返回值：`type[NnSigmoidAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnSigmoidAST

    exported = NnSigmoidAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnSigmoidAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnTanhAST: type[NnTanhAST]`

- api：`NnTanhAST: type[NnTanhAST]`
- 参数：无。
- 返回值：`type[NnTanhAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnTanhAST

    exported = NnTanhAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnTanhAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnLeakyReluAST: type[NnLeakyReluAST]`

- api：`NnLeakyReluAST: type[NnLeakyReluAST]`
- 参数：无。
- 返回值：`type[NnLeakyReluAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnLeakyReluAST

    exported = NnLeakyReluAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnLeakyReluAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnHardSigmoidAST: type[NnHardSigmoidAST]`

- api：`NnHardSigmoidAST: type[NnHardSigmoidAST]`
- 参数：无。
- 返回值：`type[NnHardSigmoidAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnHardSigmoidAST

    exported = NnHardSigmoidAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnHardSigmoidAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnExpAST: type[NnExpAST]`

- api：`NnExpAST: type[NnExpAST]`
- 参数：无。
- 返回值：`type[NnExpAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnExpAST

    exported = NnExpAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnExpAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnReduceAST: type[NnReduceAST]`

- api：`NnReduceAST: type[NnReduceAST]`
- 参数：无。
- 返回值：`type[NnReduceAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnReduceAST

    exported = NnReduceAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnReduceAST`，作为 reduce family 的公开共享基类。
- 注意事项：包根只承诺导出本条目声明的公开对象；具体 reduce operation 仍由 `NnReduceSumAST`、`NnReduceMinAST`、`NnReduceMaxAST` 承接。

### `NnReduceSumAST: type[NnReduceSumAST]`

- api：`NnReduceSumAST: type[NnReduceSumAST]`
- 参数：无。
- 返回值：`type[NnReduceSumAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnReduceSumAST

    exported = NnReduceSumAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnReduceSumAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnReduceMinAST: type[NnReduceMinAST]`

- api：`NnReduceMinAST: type[NnReduceMinAST]`
- 参数：无。
- 返回值：`type[NnReduceMinAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnReduceMinAST

    exported = NnReduceMinAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnReduceMinAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnReduceMaxAST: type[NnReduceMaxAST]`

- api：`NnReduceMaxAST: type[NnReduceMaxAST]`
- 参数：无。
- 返回值：`type[NnReduceMaxAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnReduceMaxAST

    exported = NnReduceMaxAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnReduceMaxAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnSoftmaxAST: type[NnSoftmaxAST]`

- api：`NnSoftmaxAST: type[NnSoftmaxAST]`
- 参数：无。
- 返回值：`type[NnSoftmaxAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnSoftmaxAST

    exported = NnSoftmaxAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnSoftmaxAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `MatmulAST: type[MatmulAST]`

- api：`MatmulAST: type[MatmulAST]`
- 参数：无。
- 返回值：`type[MatmulAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import MatmulAST

    exported = MatmulAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `MatmulAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `FCAST: type[FCAST]`

- api：`FCAST: type[FCAST]`
- 参数：无。
- 返回值：`type[FCAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import FCAST

    exported = FCAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `FCAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ConvAST: type[ConvAST]`

- api：`ConvAST: type[ConvAST]`
- 参数：无。
- 返回值：`type[ConvAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import ConvAST

    exported = ConvAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `ConvAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnAddAST: type[NnAddAST]`

- api：`NnAddAST: type[NnAddAST]`
- 参数：无。
- 返回值：`type[NnAddAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnAddAST

    exported = NnAddAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnAddAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnSubAST: type[NnSubAST]`

- api：`NnSubAST: type[NnSubAST]`
- 参数：无。
- 返回值：`type[NnSubAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnSubAST

    exported = NnSubAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnSubAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnMulAST: type[NnMulAST]`

- api：`NnMulAST: type[NnMulAST]`
- 参数：无。
- 返回值：`type[NnMulAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnMulAST

    exported = NnMulAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnMulAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnTrueDivAST: type[NnTrueDivAST]`

- api：`NnTrueDivAST: type[NnTrueDivAST]`
- 参数：无。
- 返回值：`type[NnTrueDivAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnTrueDivAST

    exported = NnTrueDivAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnTrueDivAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnFloorDivAST: type[NnFloorDivAST]`

- api：`NnFloorDivAST: type[NnFloorDivAST]`
- 参数：无。
- 返回值：`type[NnFloorDivAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnFloorDivAST

    exported = NnFloorDivAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnFloorDivAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnEqAST: type[NnEqAST]`

- api：`NnEqAST: type[NnEqAST]`
- 参数：无。
- 返回值：`type[NnEqAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnEqAST

    exported = NnEqAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnEqAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnNeAST: type[NnNeAST]`

- api：`NnNeAST: type[NnNeAST]`
- 参数：无。
- 返回值：`type[NnNeAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnNeAST

    exported = NnNeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnNeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnLtAST: type[NnLtAST]`

- api：`NnLtAST: type[NnLtAST]`
- 参数：无。
- 返回值：`type[NnLtAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnLtAST

    exported = NnLtAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnLtAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnLeAST: type[NnLeAST]`

- api：`NnLeAST: type[NnLeAST]`
- 参数：无。
- 返回值：`type[NnLeAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnLeAST

    exported = NnLeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnLeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnGtAST: type[NnGtAST]`

- api：`NnGtAST: type[NnGtAST]`
- 参数：无。
- 返回值：`type[NnGtAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnGtAST

    exported = NnGtAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnGtAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `NnGeAST: type[NnGeAST]`

- api：`NnGeAST: type[NnGeAST]`
- 参数：无。
- 返回值：`type[NnGeAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import NnGeAST

    exported = NnGeAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `NnGeAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchQueryAST: type[ArchQueryAST]`

- api：`ArchQueryAST: type[ArchQueryAST]`
- 参数：无。
- 返回值：`type[ArchQueryAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import ArchQueryAST

    exported = ArchQueryAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `ArchQueryAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchGetBlockIdAST: type[ArchGetBlockIdAST]`

- api：`ArchGetBlockIdAST: type[ArchGetBlockIdAST]`
- 参数：无。
- 返回值：`type[ArchGetBlockIdAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import ArchGetBlockIdAST

    exported = ArchGetBlockIdAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `ArchGetBlockIdAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchGetBlockNumAST: type[ArchGetBlockNumAST]`

- api：`ArchGetBlockNumAST: type[ArchGetBlockNumAST]`
- 参数：无。
- 返回值：`type[ArchGetBlockNumAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import ArchGetBlockNumAST

    exported = ArchGetBlockNumAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `ArchGetBlockNumAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchGetSubthreadIdAST: type[ArchGetSubthreadIdAST]`

- api：`ArchGetSubthreadIdAST: type[ArchGetSubthreadIdAST]`
- 参数：无。
- 返回值：`type[ArchGetSubthreadIdAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import ArchGetSubthreadIdAST

    exported = ArchGetSubthreadIdAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `ArchGetSubthreadIdAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchGetSubthreadNumAST: type[ArchGetSubthreadNumAST]`

- api：`ArchGetSubthreadNumAST: type[ArchGetSubthreadNumAST]`
- 参数：无。
- 返回值：`type[ArchGetSubthreadNumAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import ArchGetSubthreadNumAST

    exported = ArchGetSubthreadNumAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `ArchGetSubthreadNumAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchGetThreadIdAST: type[ArchGetThreadIdAST]`

- api：`ArchGetThreadIdAST: type[ArchGetThreadIdAST]`
- 参数：无。
- 返回值：`type[ArchGetThreadIdAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import ArchGetThreadIdAST

    exported = ArchGetThreadIdAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `ArchGetThreadIdAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchGetThreadNumAST: type[ArchGetThreadNumAST]`

- api：`ArchGetThreadNumAST: type[ArchGetThreadNumAST]`
- 参数：无。
- 返回值：`type[ArchGetThreadNumAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import ArchGetThreadNumAST

    exported = ArchGetThreadNumAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `ArchGetThreadNumAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchGetDynamicMemoryAST: type[ArchGetDynamicMemoryAST]`

- api：`ArchGetDynamicMemoryAST: type[ArchGetDynamicMemoryAST]`
- 参数：无。
- 返回值：`type[ArchGetDynamicMemoryAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import ArchGetDynamicMemoryAST

    exported = ArchGetDynamicMemoryAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `ArchGetDynamicMemoryAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchBarrierAST: type[ArchBarrierAST]`

- api：`ArchBarrierAST: type[ArchBarrierAST]`
- 参数：无。
- 返回值：`type[ArchBarrierAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import ArchBarrierAST

    exported = ArchBarrierAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `ArchBarrierAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

### `ArchLaunchKernelAST: type[ArchLaunchKernelAST]`

- api：`ArchLaunchKernelAST: type[ArchLaunchKernelAST]`
- 参数：无。
- 返回值：`type[ArchLaunchKernelAST]`；表示从 `kernel_gen.dsl.ast.nodes` 导入到的公开类型对象。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.nodes import ArchLaunchKernelAST

    exported = ArchLaunchKernelAST
    ```
- 功能说明：从 `kernel_gen.dsl.ast.nodes` 包根导出 `ArchLaunchKernelAST`，作为对应 AST 节点或类型的稳定导入对象。
- 注意事项：包根只承诺导出本条目声明的公开对象；行为语义以对应子 spec 的同名 API 详情为准，包根不得扩展额外 helper。

## 测试

- 测试文件：`test/dsl/ast/nodes/test_package.py`
- 执行命令：`pytest -q test/dsl/ast/nodes/test_package.py`

### 测试目标

- 节点包根导出当前公开节点。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-NODES-001 | 公开入口 | nodes package reexports current public nodes | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nodes_package_reexports_current_public_nodes`。 | 公开入口在“nodes package reexports current public nodes”场景下可导入、构造、注册或按名称发现。 | `test_nodes_package_reexports_current_public_nodes` |
