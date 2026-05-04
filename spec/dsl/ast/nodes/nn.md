# DSL AST NN 节点

## 功能简介

- `kernel_gen.dsl.ast.nodes.nn` 定义 NN helper 对应 AST 节点。
- 每个公开 NN operation 对应唯一具体 AST 节点；不公开 `kind`/`op` 字符串分派节点。
- parser 在解析阶段决定生成 symbol 节点还是 NN 节点，emit 阶段不再根据同一节点的输入类型改派 dialect。

## API 列表

- `class NnImg2Col1dAST(source: ValueAST, kw: SymbolDimAST | ConstValueAST, sw: SymbolDimAST | ConstValueAST = ..., dw: SymbolDimAST | ConstValueAST = ..., pl: SymbolDimAST | ConstValueAST = ..., pr: SymbolDimAST | ConstValueAST = ..., location: SourceLocation | None = None)`
- `class NnImg2Col2dAST(source: ValueAST, kh: SymbolDimAST | ConstValueAST, kw: SymbolDimAST | ConstValueAST, sh: SymbolDimAST | ConstValueAST = ..., sw: SymbolDimAST | ConstValueAST = ..., dh: SymbolDimAST | ConstValueAST = ..., dw: SymbolDimAST | ConstValueAST = ..., ph: SymbolDimAST | ConstValueAST = ..., pw: SymbolDimAST | ConstValueAST = ..., pl: SymbolDimAST | ConstValueAST = ..., pr: SymbolDimAST | ConstValueAST = ..., location: SourceLocation | None = None)`
- `class NnBroadcastAST(value: ValueAST, target: ValueAST, location: SourceLocation | None = None)`
- `class NnBroadcastToAST(source: ValueAST, target_shape: SymbolListAST, space: MemorySpaceAttrAST, location: SourceLocation | None = None)`
- `class NnTransposeAST(value: ValueAST, perm: SymbolListAST, location: SourceLocation | None = None)`
- `class NnReluAST(value: ValueAST, location: SourceLocation | None = None)`
- `class NnSigmoidAST(value: ValueAST, location: SourceLocation | None = None)`
- `class NnTanhAST(value: ValueAST, location: SourceLocation | None = None)`
- `class NnLeakyReluAST(value: ValueAST, alpha: ConstValueAST | SymbolDimAST, location: SourceLocation | None = None)`
- `class NnHardSigmoidAST(value: ValueAST, alpha: ConstValueAST | SymbolDimAST, beta: ConstValueAST | SymbolDimAST, location: SourceLocation | None = None)`
- `class NnExpAST(value: ValueAST, location: SourceLocation | None = None)`
- `class NnReduceAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, keepdim: BoolValueAST | None = None, location: SourceLocation | None = None)`
- `class NnReduceSumAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, keepdim: BoolValueAST | None = None, location: SourceLocation | None = None)`
- `class NnReduceMinAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, keepdim: BoolValueAST | None = None, location: SourceLocation | None = None)`
- `class NnReduceMaxAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, keepdim: BoolValueAST | None = None, location: SourceLocation | None = None)`
- `class NnSoftmaxAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, location: SourceLocation | None = None)`
- `class MatmulAST(lhs: ValueAST, rhs: ValueAST, memoryspace: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`
- `class FCAST(value: ValueAST, weight: ValueAST, location: SourceLocation | None = None)`
- `class ConvAST(value: ValueAST, weight: ValueAST, stride: SymbolListAST, padding: SymbolListAST, dilation: SymbolListAST, groups: SymbolDimAST | ConstValueAST | None = None, location: SourceLocation | None = None)`
- `class NnAddAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class NnSubAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class NnMulAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class NnTrueDivAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class NnFloorDivAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class NnEqAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class NnNeAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class NnLtAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class NnLeAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class NnGtAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class NnGeAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：`spec/dsl/ast/nodes/nn.md`
- `功能实现`：`kernel_gen/dsl/ast/nodes/nn.py`
- `test`：`test/dsl/ast/nodes/test_nn.py`

## 依赖

- `spec/dsl/ast/nodes/basic.md`：`ValueAST`、`MemoryAST`、`BoolValueAST`。
- `spec/dsl/ast/nodes/symbol.md`：`SymbolListAST`、`ConstValueAST`、`SymbolDimAST`。
- `spec/dsl/ast/nodes/attr.md`：`MemorySpaceAttrAST`。
- `kernel_gen.dialect.nn`：最终发射的 NN dialect op。

## 额外补充

- 会产生 memory 值的 NN 节点必须通过自身 `result_memory() -> Memory | None` 暴露解析期结果语义。
- 当前必须覆盖赋值绑定需要的节点：`NnImg2Col1dAST`、`NnImg2Col2dAST`、`NnReduceAST` 及其具体 reduce 子类、`MatmulAST`、`NnAddAST`、`NnSubAST`、`NnMulAST`、`NnTrueDivAST`、`NnFloorDivAST`、`NnEqAST`、`NnNeAST`、`NnLtAST`、`NnLeAST`、`NnGtAST`、`NnGeAST`。
- `result_memory()` 只能读取成员节点的公开 `result_memory()` / `result_symbol()`，并复用 `kernel_gen.operation.nn` 公开 operation 语义，不得在 visitor 内写 NN 专用推导。
- emit 阶段构造 runtime `Memory` 对应 `NnMemoryType` 时复用 `MemoryAST.type_from_memory(...)`，不得复制 dtype/space 分支表。
- `NnReduceAST` 承接 reduce 共同行为；具体 `NnReduceSumAST` / `NnReduceMinAST` / `NnReduceMaxAST` 只绑定对应 operation 语义与 dialect op，不重复实现 axis/keepdim/result type 推导。
- 公开 AST 测试必须覆盖固定种子/矩阵化的符号 shape 广播、dtype cast、memory/symbol 二元路径、Operation operand、img2col 参数语义缺失、结构化 conv/matmul/fc 错误边界以及“可发射 memory 但不是 tensor argument”的错误边界；测试入口为 `test_nn_emit_mlir_handles_symbolic_compare_and_scalar_cast_matrix`、`test_nn_emit_mlir_rejects_memory_producing_non_argument_nodes`、`test_nn_reduce_base_and_img2col_public_unavailable_paths`、`test_nn_emit_mlir_handles_structured_public_nodes_and_dynamic_conv`、`test_nn_emit_mlir_reports_public_operation_value_errors` 与 `test_nn_emit_mlir_operation_operand_and_result_memory_matrix`。

## API详细说明

### `class NnImg2Col1dAST(source: ValueAST, kw: SymbolDimAST | ConstValueAST, sw: SymbolDimAST | ConstValueAST = ..., dw: SymbolDimAST | ConstValueAST = ..., pl: SymbolDimAST | ConstValueAST = ..., pr: SymbolDimAST | ConstValueAST = ..., location: SourceLocation | None = None)`

- api：`class NnImg2Col1dAST(source: ValueAST, kw: SymbolDimAST | ConstValueAST, sw: SymbolDimAST | ConstValueAST = ..., dw: SymbolDimAST | ConstValueAST = ..., pl: SymbolDimAST | ConstValueAST = ..., pr: SymbolDimAST | ConstValueAST = ..., location: SourceLocation | None = None)`
- 参数：
  - `source`：源码对象或 source 属性；类型 `ValueAST`；无默认值；不得写入不可序列化的公开状态。
  - `kw`：一维卷积 kernel width；类型 `SymbolDimAST | ConstValueAST`；无默认值；不允许 None。
  - `sw`：width 方向 stride；类型 `SymbolDimAST | ConstValueAST`；默认值 `...`；默认值按签名。
  - `dw`：width 方向 dilation；类型 `SymbolDimAST | ConstValueAST`；默认值 `...`；默认值按签名。
  - `pl`：left padding；类型 `SymbolDimAST | ConstValueAST`；默认值 `...`；默认值按签名。
  - `pr`：right padding；类型 `SymbolDimAST | ConstValueAST`；默认值 `...`；默认值按签名。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnImg2Col1dAST(source=source, kw=kw, sw=sw, dw=dw, pl=pl, pr=pr, location=location)
    ```
- 功能说明：执行 `NnImg2Col1dAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnImg2Col2dAST(source: ValueAST, kh: SymbolDimAST | ConstValueAST, kw: SymbolDimAST | ConstValueAST, sh: SymbolDimAST | ConstValueAST = ..., sw: SymbolDimAST | ConstValueAST = ..., dh: SymbolDimAST | ConstValueAST = ..., dw: SymbolDimAST | ConstValueAST = ..., ph: SymbolDimAST | ConstValueAST = ..., pw: SymbolDimAST | ConstValueAST = ..., pl: SymbolDimAST | ConstValueAST = ..., pr: SymbolDimAST | ConstValueAST = ..., location: SourceLocation | None = None)`

- api：`class NnImg2Col2dAST(source: ValueAST, kh: SymbolDimAST | ConstValueAST, kw: SymbolDimAST | ConstValueAST, sh: SymbolDimAST | ConstValueAST = ..., sw: SymbolDimAST | ConstValueAST = ..., dh: SymbolDimAST | ConstValueAST = ..., dw: SymbolDimAST | ConstValueAST = ..., ph: SymbolDimAST | ConstValueAST = ..., pw: SymbolDimAST | ConstValueAST = ..., pl: SymbolDimAST | ConstValueAST = ..., pr: SymbolDimAST | ConstValueAST = ..., location: SourceLocation | None = None)`
- 参数：
  - `source`：源码对象或 source 属性；类型 `ValueAST`；无默认值；不得写入不可序列化的公开状态。
  - `kh`：二维卷积 kernel height；类型 `SymbolDimAST | ConstValueAST`；无默认值；不允许 None。
  - `kw`：一维卷积 kernel width；类型 `SymbolDimAST | ConstValueAST`；无默认值；不允许 None。
  - `sh`：height 方向 stride；类型 `SymbolDimAST | ConstValueAST`；默认值 `...`；默认值按签名。
  - `sw`：width 方向 stride；类型 `SymbolDimAST | ConstValueAST`；默认值 `...`；默认值按签名。
  - `dh`：height 方向 dilation；类型 `SymbolDimAST | ConstValueAST`；默认值 `...`；默认值按签名。
  - `dw`：width 方向 dilation；类型 `SymbolDimAST | ConstValueAST`；默认值 `...`；默认值按签名。
  - `ph`：height padding；类型 `SymbolDimAST | ConstValueAST`；默认值 `...`；默认值按签名。
  - `pw`：width padding；类型 `SymbolDimAST | ConstValueAST`；默认值 `...`；默认值按签名。
  - `pl`：left padding；类型 `SymbolDimAST | ConstValueAST`；默认值 `...`；默认值按签名。
  - `pr`：right padding；类型 `SymbolDimAST | ConstValueAST`；默认值 `...`；默认值按签名。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnImg2Col2dAST(source=source, kh=kh, kw=kw, sh=sh, sw=sw, dh=dh, dw=dw, ph=ph, pw=pw, pl=pl, pr=pr, location=location)
    ```
- 功能说明：执行 `NnImg2Col2dAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnBroadcastAST(value: ValueAST, target: ValueAST, location: SourceLocation | None = None)`

- api：`class NnBroadcastAST(value: ValueAST, target: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `value`：输入值；类型 `ValueAST`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `target`：目标内存或目标节点；类型 `ValueAST`；无默认值；不允许 None；作为写入、填充或回写位置。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnBroadcastAST(value=value, target=target, location=location)
    ```
- 功能说明：执行 `NnBroadcastAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnBroadcastToAST(source: ValueAST, target_shape: SymbolListAST, space: MemorySpaceAttrAST, location: SourceLocation | None = None)`

- api：`class NnBroadcastToAST(source: ValueAST, target_shape: SymbolListAST, space: MemorySpaceAttrAST, location: SourceLocation | None = None)`
- 参数：
  - `source`：源码对象或 source 属性；类型 `ValueAST`；无默认值；不得写入不可序列化的公开状态。
  - `target_shape`：`target_shape` 参数；类型 `SymbolListAST`；无默认值；不允许 None。
  - `space`：内存空间；类型 `MemorySpaceAttrAST`；无默认值；传入时必须是公开 MemorySpace 或 MemorySpaceAttrAST。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnBroadcastToAST(source=source, target_shape=target_shape, space=space, location=location)
    ```
- 功能说明：执行 `NnBroadcastToAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnTransposeAST(value: ValueAST, perm: SymbolListAST, location: SourceLocation | None = None)`

- api：`class NnTransposeAST(value: ValueAST, perm: SymbolListAST, location: SourceLocation | None = None)`
- 参数：
  - `value`：输入值；类型 `ValueAST`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `perm`：transpose 维度排列；类型 `SymbolListAST`；无默认值；不允许 None；每个轴必须是公开符号/常量维度。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnTransposeAST(value=value, perm=perm, location=location)
    ```
- 功能说明：执行 `NnTransposeAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnReluAST(value: ValueAST, location: SourceLocation | None = None)`

- api：`class NnReluAST(value: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `value`：输入值；类型 `ValueAST`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnReluAST(value=value, location=location)
    ```
- 功能说明：执行 `NnReluAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnSigmoidAST(value: ValueAST, location: SourceLocation | None = None)`

- api：`class NnSigmoidAST(value: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `value`：输入值；类型 `ValueAST`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnSigmoidAST(value=value, location=location)
    ```
- 功能说明：执行 `NnSigmoidAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnTanhAST(value: ValueAST, location: SourceLocation | None = None)`

- api：`class NnTanhAST(value: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `value`：输入值；类型 `ValueAST`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnTanhAST(value=value, location=location)
    ```
- 功能说明：执行 `NnTanhAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnLeakyReluAST(value: ValueAST, alpha: ConstValueAST | SymbolDimAST, location: SourceLocation | None = None)`

- api：`class NnLeakyReluAST(value: ValueAST, alpha: ConstValueAST | SymbolDimAST, location: SourceLocation | None = None)`
- 参数：
  - `value`：输入值；类型 `ValueAST`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `alpha`：激活参数 alpha；类型 `ConstValueAST | SymbolDimAST`；无默认值；不允许 None。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnLeakyReluAST(value=value, alpha=alpha, location=location)
    ```
- 功能说明：执行 `NnLeakyReluAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnHardSigmoidAST(value: ValueAST, alpha: ConstValueAST | SymbolDimAST, beta: ConstValueAST | SymbolDimAST, location: SourceLocation | None = None)`

- api：`class NnHardSigmoidAST(value: ValueAST, alpha: ConstValueAST | SymbolDimAST, beta: ConstValueAST | SymbolDimAST, location: SourceLocation | None = None)`
- 参数：
  - `value`：输入值；类型 `ValueAST`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `alpha`：激活参数 alpha；类型 `ConstValueAST | SymbolDimAST`；无默认值；不允许 None。
  - `beta`：激活参数 beta；类型 `ConstValueAST | SymbolDimAST`；无默认值；不允许 None。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnHardSigmoidAST(value=value, alpha=alpha, beta=beta, location=location)
    ```
- 功能说明：执行 `NnHardSigmoidAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnExpAST(value: ValueAST, location: SourceLocation | None = None)`

- api：`class NnExpAST(value: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `value`：输入值；类型 `ValueAST`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnExpAST(value=value, location=location)
    ```
- 功能说明：执行 `NnExpAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnReduceAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, keepdim: BoolValueAST | None = None, location: SourceLocation | None = None)`

- api：`class NnReduceAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, keepdim: BoolValueAST | None = None, location: SourceLocation | None = None)`
- 参数：
  - `value`：被归约的公开 AST 值节点；类型 `ValueAST`；无默认值；不允许 `None`。
  - `axis`：归约轴；类型 `SymbolDimAST | ConstValueAST | None`；默认值 `None`；`None` 表示由具体 reduce 子类按公开合同处理默认轴。
  - `keepdim`：是否保留归约维；类型 `BoolValueAST | None`；默认值 `None`；`None` 表示由具体 reduce 子类按公开合同处理默认值。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；用于诊断定位。
- 返回值：`NnReduceAST` 实例。
- 使用示例：

  ```python
  reduce_ast = NnReduceAST(value, axis=axis, keepdim=keepdim)
  ```
- 功能说明：定义 reduce family 的共享 AST 基类，承接 `value/axis/keepdim/location` 公共字段。
- 注意事项：该类只作为 reduce family 的公开 AST 结构入口；具体发射语义由 `NnReduceSumAST`、`NnReduceMinAST` 与 `NnReduceMaxAST` 约束，不得扩展为未定义 reduce op。

### `class NnReduceSumAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, keepdim: BoolValueAST | None = None, location: SourceLocation | None = None)`

- api：`class NnReduceSumAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, keepdim: BoolValueAST | None = None, location: SourceLocation | None = None)`
- 参数：
  - `value`：输入值；类型 `ValueAST`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `axis`：归约或 softmax 轴；类型 `SymbolDimAST | ConstValueAST | None`；默认值 `None`；None 表示使用实现定义的默认轴。
  - `keepdim`：归约后是否保留维度；类型 `BoolValueAST | None`；默认值 `None`；默认值按签名。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnReduceSumAST(value=value, axis=axis, keepdim=keepdim, location=location)
    ```
- 功能说明：执行 `NnReduceSumAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnReduceMinAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, keepdim: BoolValueAST | None = None, location: SourceLocation | None = None)`

- api：`class NnReduceMinAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, keepdim: BoolValueAST | None = None, location: SourceLocation | None = None)`
- 参数：
  - `value`：输入值；类型 `ValueAST`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `axis`：归约或 softmax 轴；类型 `SymbolDimAST | ConstValueAST | None`；默认值 `None`；None 表示使用实现定义的默认轴。
  - `keepdim`：归约后是否保留维度；类型 `BoolValueAST | None`；默认值 `None`；默认值按签名。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnReduceMinAST(value=value, axis=axis, keepdim=keepdim, location=location)
    ```
- 功能说明：执行 `NnReduceMinAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnReduceMaxAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, keepdim: BoolValueAST | None = None, location: SourceLocation | None = None)`

- api：`class NnReduceMaxAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, keepdim: BoolValueAST | None = None, location: SourceLocation | None = None)`
- 参数：
  - `value`：输入值；类型 `ValueAST`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `axis`：归约或 softmax 轴；类型 `SymbolDimAST | ConstValueAST | None`；默认值 `None`；None 表示使用实现定义的默认轴。
  - `keepdim`：归约后是否保留维度；类型 `BoolValueAST | None`；默认值 `None`；默认值按签名。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnReduceMaxAST(value=value, axis=axis, keepdim=keepdim, location=location)
    ```
- 功能说明：执行 `NnReduceMaxAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnSoftmaxAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, location: SourceLocation | None = None)`

- api：`class NnSoftmaxAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, location: SourceLocation | None = None)`
- 参数：
  - `value`：输入值；类型 `ValueAST`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `axis`：归约或 softmax 轴；类型 `SymbolDimAST | ConstValueAST | None`；默认值 `None`；None 表示使用实现定义的默认轴。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnSoftmaxAST(value=value, axis=axis, location=location)
    ```
- 功能说明：执行 `NnSoftmaxAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class MatmulAST(lhs: ValueAST, rhs: ValueAST, memoryspace: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`

- api：`class MatmulAST(lhs: ValueAST, rhs: ValueAST, memoryspace: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`
- 参数：
  - `lhs`：左操作数；类型 `ValueAST`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `ValueAST`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
  - `memoryspace`：目标内存空间；类型 `MemorySpaceAttrAST | None`；默认值 `None`；None 表示沿用源对象空间。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = MatmulAST(lhs=lhs, rhs=rhs, memoryspace=memoryspace, location=location)
    ```
- 功能说明：执行 `MatmulAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态；matmul 两侧 contracting 维度必须可证明相等，静态、命名符号与 runtime type-level 符号均要求完全一致；不得把任意两个 `runtime_dim_*` 互相匹配。

### `class FCAST(value: ValueAST, weight: ValueAST, location: SourceLocation | None = None)`

- api：`class FCAST(value: ValueAST, weight: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `value`：输入值；类型 `ValueAST`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `weight`：权重输入；类型 `ValueAST`；无默认值；不允许 None。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = FCAST(value=value, weight=weight, location=location)
    ```
- 功能说明：执行 `FCAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class ConvAST(value: ValueAST, weight: ValueAST, stride: SymbolListAST, padding: SymbolListAST, dilation: SymbolListAST, groups: SymbolDimAST | ConstValueAST | None = None, location: SourceLocation | None = None)`

- api：`class ConvAST(value: ValueAST, weight: ValueAST, stride: SymbolListAST, padding: SymbolListAST, dilation: SymbolListAST, groups: SymbolDimAST | ConstValueAST | None = None, location: SourceLocation | None = None)`
- 参数：
  - `value`：输入值；类型 `ValueAST`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `weight`：权重输入；类型 `ValueAST`；无默认值；不允许 None。
  - `stride`：步幅序列；类型 `SymbolListAST`；无默认值；传入时长度必须与 shape 语义匹配。
  - `padding`：padding 序列；类型 `SymbolListAST`；无默认值；不允许 None。
  - `dilation`：dilation 序列；类型 `SymbolListAST`；无默认值；不允许 None。
  - `groups`：分组数；类型 `SymbolDimAST | ConstValueAST | None`；默认值 `None`；None 表示使用默认分组语义。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = ConvAST(value=value, weight=weight, stride=stride, padding=padding, dilation=dilation, groups=groups, location=location)
    ```
- 功能说明：执行 `ConvAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnAddAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`

- api：`class NnAddAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `lhs`：左操作数；类型 `ValueAST`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `ValueAST`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnAddAST(lhs=lhs, rhs=rhs, location=location)
    ```
- 功能说明：执行 `NnAddAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnSubAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`

- api：`class NnSubAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `lhs`：左操作数；类型 `ValueAST`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `ValueAST`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnSubAST(lhs=lhs, rhs=rhs, location=location)
    ```
- 功能说明：执行 `NnSubAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnMulAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`

- api：`class NnMulAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `lhs`：左操作数；类型 `ValueAST`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `ValueAST`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnMulAST(lhs=lhs, rhs=rhs, location=location)
    ```
- 功能说明：执行 `NnMulAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnTrueDivAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`

- api：`class NnTrueDivAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `lhs`：左操作数；类型 `ValueAST`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `ValueAST`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnTrueDivAST(lhs=lhs, rhs=rhs, location=location)
    ```
- 功能说明：执行 `NnTrueDivAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnFloorDivAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`

- api：`class NnFloorDivAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `lhs`：左操作数；类型 `ValueAST`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `ValueAST`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnFloorDivAST(lhs=lhs, rhs=rhs, location=location)
    ```
- 功能说明：执行 `NnFloorDivAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnEqAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`

- api：`class NnEqAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `lhs`：左操作数；类型 `ValueAST`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `ValueAST`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnEqAST(lhs=lhs, rhs=rhs, location=location)
    ```
- 功能说明：执行 `NnEqAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnNeAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`

- api：`class NnNeAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `lhs`：左操作数；类型 `ValueAST`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `ValueAST`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnNeAST(lhs=lhs, rhs=rhs, location=location)
    ```
- 功能说明：执行 `NnNeAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnLtAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`

- api：`class NnLtAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `lhs`：左操作数；类型 `ValueAST`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `ValueAST`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnLtAST(lhs=lhs, rhs=rhs, location=location)
    ```
- 功能说明：执行 `NnLtAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnLeAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`

- api：`class NnLeAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `lhs`：左操作数；类型 `ValueAST`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `ValueAST`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnLeAST(lhs=lhs, rhs=rhs, location=location)
    ```
- 功能说明：执行 `NnLeAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnGtAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`

- api：`class NnGtAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `lhs`：左操作数；类型 `ValueAST`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `ValueAST`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnGtAST(lhs=lhs, rhs=rhs, location=location)
    ```
- 功能说明：执行 `NnGtAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class NnGeAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`

- api：`class NnGeAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- 参数：
  - `lhs`：左操作数；类型 `ValueAST`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `ValueAST`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = NnGeAST(lhs=lhs, rhs=rhs, location=location)
    ```
- 功能说明：执行 `NnGeAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

## 测试

- 测试文件：`test/dsl/ast/nodes/test_nn.py`
- 执行命令：`pytest -q test/dsl/ast/nodes/test_nn.py`

### 测试目标

- 每个公开 NN 节点构造与字段合同。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-NODES-NN-001 | 公开入口 | NN binary node stores exact operation kind and operands | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_binary_node_stores_exact_operation_kind_and_operands`。 | 公开入口在“NN binary node stores exact operation kind and operands”场景下可导入、构造、注册或按名称发现。 | `test_nn_binary_node_stores_exact_operation_kind_and_operands` |
| TC-DSL-AST-NODES-NN-002 | 公开入口 | NN unary node stores kind and optional parameters | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_unary_node_stores_kind_and_optional_parameters`。 | 公开入口在“NN unary node stores kind and optional parameters”场景下可导入、构造、注册或按名称发现。 | `test_nn_unary_node_stores_kind_and_optional_parameters` |
| TC-DSL-AST-NODES-NN-003 | 内存/DMA | NN broadcast to normalizes shape and space nodes | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_nn_broadcast_to_normalizes_shape_and_space_nodes`。 | 内存类型、布局、搬运结果或 verifier 行为体现“NN broadcast to normalizes shape and space nodes”场景。 | `test_nn_broadcast_to_normalizes_shape_and_space_nodes` |
| TC-DSL-AST-NODES-NN-004 | 公开入口 | NN matmul and img2col store structured members | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_matmul_and_img2col_store_structured_members`。 | 公开入口在“NN matmul and img2col store structured members”场景下可导入、构造、注册或按名称发现。 | `test_nn_matmul_and_img2col_store_structured_members` |
| TC-DSL-AST-NODES-NN-005 | 执行结果 | NN nodes do not expose legacy dispatch fields | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_nn_nodes_do_not_expose_legacy_dispatch_fields`。 | 命令返回码、输出、执行结果或状态变更体现“NN nodes do not expose legacy dispatch fields”场景。 | `test_nn_nodes_do_not_expose_legacy_dispatch_fields` |
| TC-DSL-AST-NODES-NN-006 | 公开入口 | NN reduce nodes share public base fields | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_reduce_nodes_share_public_base_fields`。 | 公开入口在“NN reduce nodes share public base fields”场景下可导入、构造、注册或按名称发现。 | `test_nn_reduce_nodes_share_public_base_fields` |
| TC-DSL-AST-NODES-NN-007 | 符号语义 | NN result memory handles parameterized public shapes | 准备静态与符号 shape 的公开 MemoryAST 输入。 | 运行 `test_nn_result_memory_handles_parameterized_public_shapes`。 | `result_memory()` 复用公开 operation 语义推导 matmul、elementwise、compare、reduce 与 img2col 结果。 | `test_nn_result_memory_handles_parameterized_public_shapes` |
| TC-DSL-AST-NODES-NN-008 | 边界/异常 | NN emit MLIR accepts public nodes and reports public errors | 准备公开 Context、Block 与 MemoryAST 输入。 | 运行 `test_nn_emit_mlir_accepts_public_nodes_and_reports_public_errors`。 | 公开 NN AST 节点可发射为 MLIR op；非法公开参数按稳定 `KernelCodeError` 文本失败。 | `test_nn_emit_mlir_accepts_public_nodes_and_reports_public_errors` |
| TC-DSL-AST-NODES-NN-009 | 符号语义 | NN emit MLIR handles parameterized public binary and compare paths | 准备 dtype、shape 与标量组合不同的公开 MemoryAST 输入。 | 运行 `test_nn_emit_mlir_handles_parameterized_public_binary_and_compare_paths`。 | elementwise 与 compare AST 覆盖 memory/memory、memory/symbol、symbol/memory、隐式 broadcast 与 dtype cast 公开路径。 | `test_nn_emit_mlir_handles_parameterized_public_binary_and_compare_paths` |
| TC-DSL-AST-NODES-NN-010 | 生成/编译 | NN emit MLIR handles structured public nodes and dynamic conv | 准备 matmul/fc/img2col/conv 所需静态与符号 shape 公开输入。 | 运行 `test_nn_emit_mlir_handles_structured_public_nodes_and_dynamic_conv`。 | 结构化 NN AST 通过公开入口发射对应 MLIR op；非法维度合同按稳定错误失败。 | `test_nn_emit_mlir_handles_structured_public_nodes_and_dynamic_conv` |
| TC-DSL-AST-NODES-NN-011 | 边界/异常 | NN emit MLIR reports public operation value errors | 准备会先发射 Operation 的公开 AST 子节点与非法公开值。 | 运行 `test_nn_emit_mlir_reports_public_operation_value_errors`。 | 非 tensor argument、非法 perm、axis 越界和 unsupported operand 均按公开 `KernelCodeError` 文本失败。 | `test_nn_emit_mlir_reports_public_operation_value_errors` |
