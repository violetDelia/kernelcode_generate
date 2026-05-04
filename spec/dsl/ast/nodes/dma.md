# DSL AST DMA 节点

## 功能简介

- `kernel_gen.dsl.ast.nodes.dma` 定义 DMA helper 对应 AST 节点。
- DMA 节点成员使用 `ValueAST`、`SymbolListAST`、类型属性与 space 属性表达；不公开旧 `ShapeListAST`、`DTypeAttrAST` 或裸 `DSLNode` 宽泛字段。

## API 列表

- `class DmaAllocAST(shape: SymbolListAST, dtype: IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST, space: MemorySpaceAttrAST = ..., stride: SymbolListAST | None = None, location: SourceLocation | None = None)`
- `class DmaCopyAST(source: ValueAST, space: MemorySpaceAttrAST, location: SourceLocation | None = None)`
- `class DmaCastAST(source: ValueAST, dtype: IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST, memoryspace: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`
- `class DmaViewAST(source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST, location: SourceLocation | None = None)`
- `class DmaReshapeAST(source: ValueAST, shape: SymbolListAST, location: SourceLocation | None = None)`
- `class DmaFlattenAST(source: ValueAST, location: SourceLocation | None = None)`
- `class DmaFreeAST(value: ValueAST, location: SourceLocation | None = None)`
- `class DmaFillAST(target: ValueAST, value: ConstValueAST | SymbolDimAST, location: SourceLocation | None = None)`
- `class DmaLoadAST(source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST | None = None, space: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`
- `class DmaSliceAST(source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST | None = None, space: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`
- `class DmaStoreAST(target: ValueAST, source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST | None = None, space: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`
- `class DmaDesliceAST(target: ValueAST, source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST | None = None, space: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：`spec/dsl/ast/nodes/dma.md`
- `功能实现`：`kernel_gen/dsl/ast/nodes/dma.py`
- `test`：`test/dsl/ast/nodes/test_dma.py`

## 依赖

- `spec/dsl/ast/nodes/basic.md`：`ValueAST`、`StatementAST`、`MemoryAST`。
- `spec/dsl/ast/nodes/symbol.md`：`SymbolListAST`、`ConstValueAST`、`SymbolDimAST` 与 symbol 表达式节点。
- `spec/dsl/ast/nodes/attr.md`：类型属性与 `MemorySpaceAttrAST`。
- `kernel_gen.dialect.dma`：最终发射的 DMA dialect op。

## 额外补充

- 会产生 memory 值的 DMA 节点必须实现 `result_memory() -> Memory | None`：`DmaAllocAST`、`DmaCopyAST`、`DmaCastAST`、`DmaViewAST`、`DmaReshapeAST`、`DmaFlattenAST`、`DmaLoadAST`、`DmaSliceAST`。
- `result_memory()` 只能读取自身成员节点的 `result_memory()` / `result_symbols()`，不得依赖 `DslAstVisitor` 私有状态。
- emit 阶段构造 runtime `Memory` 对应 `NnMemoryType` 时复用 `MemoryAST.type_from_memory(...)`，不得复制 dtype/space 分支表。
- `DmaCopyAST.emit_mlir(...)`、`DmaCastAST.emit_mlir(...)`、`DmaViewAST.emit_mlir(...)`、`DmaReshapeAST.emit_mlir(...)`、`DmaFlattenAST.emit_mlir(...)`、`DmaLoadAST.emit_mlir(...)` 与 `DmaSliceAST.emit_mlir(...)` 必须从自身 `result_memory()` 获取结果类型；若 AST 无法给出结果 memory，必须稳定失败，不得从已发射 SSA type 反推 dtype 或 space；`DmaLoadAST` / `DmaSliceAST` 可用公开 `size` 参数名构造结果 shape/stride type。
- `DmaLoadAST.emit_mlir(...)` 与 `DmaSliceAST.emit_mlir(...)` 若结果类型包含匿名 `?` 生成的 `runtime_dim_*` shape，或公开 size 名与 SSA operand 的 symbol 文本不一致，`dma.alloc` 必须使用 full-rank dynamic shape operands，避免符号子集形态把未知 operand 与结果 shape 误判为不一致。
- 公开 AST 测试必须覆盖动态 `alloc` shape / stride、`IntTypeAttrAST` signed / unsigned dtype、`load` / `slice` 动态 `TensorAxisAccessAST` size、`fill` bool / int / float / symbol / string value matrix、Operation source/target 公开输入、动态 flatten shape 以及 `free` / `fill` / `view` / `reshape` / `flatten` / `load` / `slice` / `store` / `deslice` 的公开错误矩阵；对应测试入口为 `test_dma_alloc_emit_mlir_handles_parameterized_public_shape_expressions`、`test_dma_emit_mlir_handles_dynamic_public_memory_paths`、`test_dma_fill_emit_mlir_handles_public_value_and_dtype_matrix`、`test_dma_emit_mlir_reports_public_error_matrix` 与 `test_dma_flatten_public_dynamic_and_scalar_shape_matrix`。
- 读类 DMA 对公开命名但 SSA 类型未知的 alloc 边界由 `test_dma_slice_uses_full_rank_dynamic_shape_for_unknown_named_result` 覆盖。

## API详细说明

### `class DmaAllocAST(shape: SymbolListAST, dtype: IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST, space: MemorySpaceAttrAST = ..., stride: SymbolListAST | None = None, location: SourceLocation | None = None)`

- api：`class DmaAllocAST(shape: SymbolListAST, dtype: IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST, space: MemorySpaceAttrAST = ..., stride: SymbolListAST | None = None, location: SourceLocation | None = None)`
- 参数：
  - `shape`：形状序列；类型 `SymbolListAST`；无默认值；不允许 None；每个维度必须满足符号维度公开合同。
  - `dtype`：数值类型；类型 `IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST`；无默认值；不允许 None；必须是公开 NumericType 或公开类型属性。
  - `space`：内存空间；类型 `MemorySpaceAttrAST`；默认值 `...`；传入时必须是公开 MemorySpace 或 MemorySpaceAttrAST。
  - `stride`：步幅序列；类型 `SymbolListAST | None`；默认值 `None`；传入时长度必须与 shape 语义匹配。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = DmaAllocAST(shape=shape, dtype=dtype, space=space, stride=stride, location=location)
    ```
- 功能说明：执行 `DmaAllocAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class DmaCopyAST(source: ValueAST, space: MemorySpaceAttrAST, location: SourceLocation | None = None)`

- api：`class DmaCopyAST(source: ValueAST, space: MemorySpaceAttrAST, location: SourceLocation | None = None)`
- 参数：
  - `source`：源码对象或 source 属性；类型 `ValueAST`；无默认值；不得写入不可序列化的公开状态。
  - `space`：内存空间；类型 `MemorySpaceAttrAST`；无默认值；传入时必须是公开 MemorySpace 或 MemorySpaceAttrAST。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = DmaCopyAST(source=source, space=space, location=location)
    ```
- 功能说明：执行 `DmaCopyAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class DmaCastAST(source: ValueAST, dtype: IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST, memoryspace: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`

- api：`class DmaCastAST(source: ValueAST, dtype: IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST, memoryspace: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`
- 参数：
  - `source`：源码对象或 source 属性；类型 `ValueAST`；无默认值；不得写入不可序列化的公开状态。
  - `dtype`：数值类型；类型 `IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST`；无默认值；不允许 None；必须是公开 NumericType 或公开类型属性。
  - `memoryspace`：目标内存空间；类型 `MemorySpaceAttrAST | None`；默认值 `None`；None 表示沿用源对象空间。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = DmaCastAST(source=source, dtype=dtype, memoryspace=memoryspace, location=location)
    ```
- 功能说明：执行 `DmaCastAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class DmaViewAST(source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST, location: SourceLocation | None = None)`

- api：`class DmaViewAST(source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST, location: SourceLocation | None = None)`
- 参数：
  - `source`：源码对象或 source 属性；类型 `ValueAST`；无默认值；不得写入不可序列化的公开状态。
  - `offset`：偏移序列；类型 `SymbolListAST`；无默认值；不允许 None；每个偏移必须是公开 ShapeInput。
  - `size`：大小序列；类型 `SymbolListAST`；无默认值；不允许 None；每个分量必须是公开 ShapeInput。
  - `stride`：步幅序列；类型 `SymbolListAST`；无默认值；传入时长度必须与 shape 语义匹配。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = DmaViewAST(source=source, offset=offset, size=size, stride=stride, location=location)
    ```
- 功能说明：执行 `DmaViewAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class DmaReshapeAST(source: ValueAST, shape: SymbolListAST, location: SourceLocation | None = None)`

- api：`class DmaReshapeAST(source: ValueAST, shape: SymbolListAST, location: SourceLocation | None = None)`
- 参数：
  - `source`：源码对象或 source 属性；类型 `ValueAST`；无默认值；不得写入不可序列化的公开状态。
  - `shape`：形状序列；类型 `SymbolListAST`；无默认值；不允许 None；每个维度必须满足符号维度公开合同。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = DmaReshapeAST(source=source, shape=shape, location=location)
    ```
- 功能说明：执行 `DmaReshapeAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class DmaFlattenAST(source: ValueAST, location: SourceLocation | None = None)`

- api：`class DmaFlattenAST(source: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `source`：源码对象或 source 属性；类型 `ValueAST`；无默认值；不得写入不可序列化的公开状态。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = DmaFlattenAST(source=source, location=location)
    ```
- 功能说明：执行 `DmaFlattenAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class DmaFreeAST(value: ValueAST, location: SourceLocation | None = None)`

- api：`class DmaFreeAST(value: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `value`：输入值；类型 `ValueAST`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = DmaFreeAST(value=value, location=location)
    ```
- 功能说明：执行 `DmaFreeAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class DmaFillAST(target: ValueAST, value: ConstValueAST | SymbolDimAST, location: SourceLocation | None = None)`

- api：`class DmaFillAST(target: ValueAST, value: ConstValueAST | SymbolDimAST, location: SourceLocation | None = None)`
- 参数：
  - `target`：目标内存或目标节点；类型 `ValueAST`；无默认值；不允许 None；作为写入、填充或回写位置。
  - `value`：输入值；类型 `ConstValueAST | SymbolDimAST`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = DmaFillAST(target=target, value=value, location=location)
    ```
- 功能说明：执行 `DmaFillAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class DmaLoadAST(source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST | None = None, space: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`

- api：`class DmaLoadAST(source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST | None = None, space: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`
- 参数：
  - `source`：源码对象或 source 属性；类型 `ValueAST`；无默认值；不得写入不可序列化的公开状态。
  - `offset`：偏移序列；类型 `SymbolListAST`；无默认值；不允许 None；每个偏移必须是公开 ShapeInput。
  - `size`：大小序列；类型 `SymbolListAST`；无默认值；不允许 None；每个分量必须是公开 ShapeInput。
  - `stride`：步幅序列；类型 `SymbolListAST | None`；默认值 `None`；传入时长度必须与 shape 语义匹配。
  - `space`：内存空间；类型 `MemorySpaceAttrAST | None`；默认值 `None`；传入时必须是公开 MemorySpace 或 MemorySpaceAttrAST。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = DmaLoadAST(source=source, offset=offset, size=size, stride=stride, space=space, location=location)
    ```
- 功能说明：执行 `DmaLoadAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class DmaSliceAST(source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST | None = None, space: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`

- api：`class DmaSliceAST(source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST | None = None, space: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`
- 参数：
  - `source`：源码对象或 source 属性；类型 `ValueAST`；无默认值；不得写入不可序列化的公开状态。
  - `offset`：偏移序列；类型 `SymbolListAST`；无默认值；不允许 None；每个偏移必须是公开 ShapeInput。
  - `size`：大小序列；类型 `SymbolListAST`；无默认值；不允许 None；每个分量必须是公开 ShapeInput。
  - `stride`：步幅序列；类型 `SymbolListAST | None`；默认值 `None`；传入时长度必须与 shape 语义匹配。
  - `space`：内存空间；类型 `MemorySpaceAttrAST | None`；默认值 `None`；传入时必须是公开 MemorySpace 或 MemorySpaceAttrAST。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = DmaSliceAST(source=source, offset=offset, size=size, stride=stride, space=space, location=location)
    ```
- 功能说明：执行 `DmaSliceAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class DmaStoreAST(target: ValueAST, source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST | None = None, space: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`

- api：`class DmaStoreAST(target: ValueAST, source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST | None = None, space: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`
- 参数：
  - `target`：目标内存或目标节点；类型 `ValueAST`；无默认值；不允许 None；作为写入、填充或回写位置。
  - `source`：源码对象或 source 属性；类型 `ValueAST`；无默认值；不得写入不可序列化的公开状态。
  - `offset`：偏移序列；类型 `SymbolListAST`；无默认值；不允许 None；每个偏移必须是公开 ShapeInput。
  - `size`：大小序列；类型 `SymbolListAST`；无默认值；不允许 None；每个分量必须是公开 ShapeInput。
  - `stride`：步幅序列；类型 `SymbolListAST | None`；默认值 `None`；传入时长度必须与 shape 语义匹配。
  - `space`：内存空间；类型 `MemorySpaceAttrAST | None`；默认值 `None`；传入时必须是公开 MemorySpace 或 MemorySpaceAttrAST。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = DmaStoreAST(target=target, source=source, offset=offset, size=size, stride=stride, space=space, location=location)
    ```
- 功能说明：执行 `DmaStoreAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class DmaDesliceAST(target: ValueAST, source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST | None = None, space: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`

- api：`class DmaDesliceAST(target: ValueAST, source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST | None = None, space: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`
- 参数：
  - `target`：目标内存或目标节点；类型 `ValueAST`；无默认值；不允许 None；作为写入、填充或回写位置。
  - `source`：源码对象或 source 属性；类型 `ValueAST`；无默认值；不得写入不可序列化的公开状态。
  - `offset`：偏移序列；类型 `SymbolListAST`；无默认值；不允许 None；每个偏移必须是公开 ShapeInput。
  - `size`：大小序列；类型 `SymbolListAST`；无默认值；不允许 None；每个分量必须是公开 ShapeInput。
  - `stride`：步幅序列；类型 `SymbolListAST | None`；默认值 `None`；传入时长度必须与 shape 语义匹配。
  - `space`：内存空间；类型 `MemorySpaceAttrAST | None`；默认值 `None`；传入时必须是公开 MemorySpace 或 MemorySpaceAttrAST。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = DmaDesliceAST(target=target, source=source, offset=offset, size=size, stride=stride, space=space, location=location)
    ```
- 功能说明：执行 `DmaDesliceAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

## 测试

- 测试文件：`test/dsl/ast/nodes/test_dma.py`
- 执行命令：`pytest -q test/dsl/ast/nodes/test_dma.py`

### 测试目标

- DMA AST 构造、字段类型、target-first 写回语义与 `SymbolListAST` 参数。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-NODES-DMA-001 | 内存/DMA | DMA alloc normalizes shape dtype space and stride nodes | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_alloc_normalizes_shape_dtype_space_and_stride_nodes`。 | 内存类型、布局、搬运结果或 verifier 行为体现“DMA alloc normalizes shape dtype space and stride nodes”场景。 | `test_dma_alloc_normalizes_shape_dtype_space_and_stride_nodes` |
| TC-DSL-AST-NODES-DMA-002 | 生成/编译 | DMA read nodes keep source first contract | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_dma_read_nodes_keep_source_first_contract`。 | 生成源码、IR 文本或编译结果体现“DMA read nodes keep source first contract”场景。 | `test_dma_read_nodes_keep_source_first_contract` |
| TC-DSL-AST-NODES-DMA-003 | 内存/DMA | DMA write nodes keep target first contract | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_write_nodes_keep_target_first_contract`。 | 内存类型、布局、搬运结果或 verifier 行为体现“DMA write nodes keep target first contract”场景。 | `test_dma_write_nodes_keep_target_first_contract` |
| TC-DSL-AST-NODES-DMA-004 | 执行结果 | DMA result nodes require AST result memory for result type | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_dma_result_nodes_require_ast_result_memory_for_result_type`。 | copy/cast/view/reshape/flatten/load/slice 无解析期 result memory 时按稳定错误失败。 | `test_dma_result_nodes_require_ast_result_memory_for_result_type` |
| TC-DSL-AST-NODES-DMA-005 | 内存/DMA | DMA result memory handles parameterized public shapes | 准备多组公开 MemoryAST、shape、stride、dtype 与 space 输入。 | 运行 `test_dma_result_memory_handles_parameterized_public_shapes`。 | `result_memory()` 稳定推导 alloc/copy/cast/view/reshape/flatten/load/slice 的 shape、dtype 与 space。 | `test_dma_result_memory_handles_parameterized_public_shapes` |
| TC-DSL-AST-NODES-DMA-006 | 边界/异常 | DMA emit MLIR accepts public nodes and reports public errors | 准备公开 Context、Block 与 MemoryAST 输入。 | 运行 `test_dma_emit_mlir_accepts_public_nodes_and_reports_public_errors`。 | 公开 DMA AST 节点可发射为 MLIR op 或语句；非法公开参数按稳定 `KernelCodeError` 文本失败。 | `test_dma_emit_mlir_accepts_public_nodes_and_reports_public_errors` |
| TC-DSL-AST-NODES-DMA-007 | 符号语义 | DMA alloc emit MLIR handles parameterized public shape expressions | 准备随机化公开 symbol 表达式、dtype、space 与 stride 输入。 | 运行 `test_dma_alloc_emit_mlir_handles_parameterized_public_shape_expressions`。 | `DmaAllocAST.emit_mlir(...)` 覆盖 add/sub/mul/truediv/floordiv shape 表达式、bool/int dtype 与 contiguous stride 合同。 | `test_dma_alloc_emit_mlir_handles_parameterized_public_shape_expressions` |
| TC-DSL-AST-NODES-DMA-008 | 内存/DMA | DMA emit MLIR handles dynamic public memory paths | 准备含符号 shape 的公开 MemoryAST 与切片参数。 | 运行 `test_dma_emit_mlir_handles_dynamic_public_memory_paths`。 | copy/cast/view/reshape/flatten/load/slice/store/deslice 通过公开 AST 入口处理动态内存路径。 | `test_dma_emit_mlir_handles_dynamic_public_memory_paths` |
| TC-DSL-AST-NODES-DMA-009 | 边界/异常 | DMA fill emit MLIR handles public value and dtype matrix | 准备 bool/int/float dtype 的公开 MemoryAST 与标量/symbol/string 值。 | 运行 `test_dma_fill_emit_mlir_handles_public_value_and_dtype_matrix`。 | `DmaFillAST.emit_mlir(...)` 覆盖公开 value/dtype 矩阵，非法组合按稳定 `KernelCodeError` 文本失败。 | `test_dma_fill_emit_mlir_handles_public_value_and_dtype_matrix` |
| TC-DSL-AST-NODES-DMA-010 | 边界/异常 | DMA emit MLIR reports public error matrix | 准备非法公开 ValueAST、MemoryAST、shape/stride 参数与 dtype 输入。 | 运行 `test_dma_emit_mlir_reports_public_error_matrix`。 | DMA AST 对非法 source/target/offset/size/stride/dtype 按稳定 `KernelCodeError` 文本失败。 | `test_dma_emit_mlir_reports_public_error_matrix` |
| TC-DSL-AST-NODES-DMA-011 | 符号语义 | DMA flatten public dynamic and scalar shape matrix | 准备多维符号 shape 与 rank-0 公开 MemoryAST 输入。 | 运行 `test_dma_flatten_public_dynamic_and_scalar_shape_matrix`。 | `DmaFlattenAST.emit_mlir(...)` 覆盖动态 shape 乘积与标量输入公开路径。 | `test_dma_flatten_public_dynamic_and_scalar_shape_matrix` |
