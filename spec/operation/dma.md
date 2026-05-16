# dma.md

## 功能简介

定义 `Memory` 的数据搬运、整块标量初始化、显式广播、视图变换与生命周期操作规范，提供 `alloc/fill/free/copy/cast/broadcast/load/store/slice/deslice/view/reshape/flatten` 的输入约束、输出语义与错误边界。该层面对高层 API，负责描述搬运意图、初始化意图、显式广播意图与视图范围；方言层语义由 [`spec/dialect/dma.md`](../../spec/dialect/dma.md) 定义。

## API 列表

- `alloc(shape: ShapeInput, dtype: NumericType, space: MemorySpace = MemorySpace.GM, stride: ShapeInput | None = None, format: Farmat = Farmat.Norm) -> Memory`
- `fill(target: Memory, value: int | float | str | SymbolDim) -> None`
- `free(value: Memory) -> None`
- `copy(source: Memory, space: MemorySpace) -> Memory`
- `broadcast(target: Memory, source: Memory) -> None`
- `load(source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None, space: MemorySpace | None = None) -> Memory`
- `store(target: Memory, source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None) -> None`
- `slice(source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None, space: MemorySpace | None = None) -> Memory`
- `deslice(target: Memory, source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None) -> None`
- `view(source: Memory, offset: ShapeInput, size: ShapeInput, stride: ShapeInput) -> Memory`
- `reshape(source: Memory, shape: ShapeInput) -> Memory`
- `flatten(source: Memory) -> Memory`
- `cast(source: Memory, dtype: NumericType, memoryspace: MemorySpace | None = None) -> Memory`
- `kernel_gen.operation.alloc(shape: ShapeInput, dtype: NumericType, space: MemorySpace = MemorySpace.GM, stride: ShapeInput | None = None, format: Farmat = Farmat.Norm) -> Memory`
- `kernel_gen.operation.dma.fill(target: Memory, value: int | float | str | SymbolDim) -> None`
- `kernel_gen.operation.dma.broadcast(target: Memory, source: Memory) -> None`
- `kernel_gen.operation.free(value: Memory) -> None`
- `kernel_gen.operation.copy(source: Memory, space: MemorySpace) -> Memory`
- `kernel_gen.operation.load(source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None, space: MemorySpace | None = None) -> Memory`
- `kernel_gen.operation.store(target: Memory, source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None) -> None`
- `kernel_gen.operation.slice(source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None, space: MemorySpace | None = None) -> Memory`
- `kernel_gen.operation.deslice(target: Memory, source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None) -> None`
- `kernel_gen.operation.view(source: Memory, offset: ShapeInput, size: ShapeInput, stride: ShapeInput) -> Memory`
- `kernel_gen.operation.reshape(source: Memory, shape: ShapeInput) -> Memory`
- `kernel_gen.operation.flatten(source: Memory) -> Memory`
- `kernel_gen.operation.cast(source: Memory, dtype: NumericType, memoryspace: MemorySpace | None = None) -> Memory`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/operation/dma.md`](../../spec/operation/dma.md)
- `功能实现`：[`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py)
- `test`：
  - [`test/operation/test_dma.py`](../../test/operation/test_dma.py)
  - [`test/operation/test_package.py`](../../test/operation/test_package.py)
  - [`test/dsl/ast/test_package.py`](../../test/dsl/ast/test_package.py)

## 依赖

- [`spec/dialect/dma.md`](../../spec/dialect/dma.md)：方言层搬运语义映射。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：`Memory`、`MemorySpace`、`shape/stride/format` 语义。
- [`spec/symbol_variable/symbol_shape.md`](../../spec/symbol_variable/symbol_shape.md)：`SymbolShape` 与索引列表规范。
- [`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)：`NumericType` 定义。
- [`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py)：高层 API 实现。
- [`kernel_gen/operation/__init__.py`](../../kernel_gen/operation/__init__.py)：定义 `kernel_gen.operation` 包级稳定导出集合，供本文件锁定顶层导出边界复用。
- [`kernel_gen/symbol_variable/memory.py`](../../kernel_gen/symbol_variable/memory.py)：`Memory` 与 `MemorySpace` 实现。

## 目标

- 为 `Memory` 提供统一、稳定的搬运与视图操作语义入口。
- 明确 `alloc/fill/free/copy/cast/broadcast/load/store/slice/deslice/view/reshape/flatten` 的输入约束、输出语义与错误边界。
- 保留动态 `shape` 与 `offsets/sizes/strides` 的表达能力，支持后续 lowering 保留切片信息。

## 额外补充

### 关系图

```text
alloc -> 产出新的 Memory 规格
fill -> 对现有 Memory 做整块标量初始化，不分配新 Memory
copy -> 保留 shape/stride/format，仅切换目标 space
broadcast -> 把 source 按公开 broadcast 规则显式物化写入 target
load -> 从 source 读取窗口，直接返回结果块
slice -> 用户侧返回值式 helper；lowering 时桥接为 alloc(target) + dma.slice(target, source, value)
view -> 仅保留 subview 窗口信息，不做搬运
reshape/flatten -> 仅改 shape/stride 元信息，不做搬运
store/deslice -> 把 source 写回 target 指定窗口
```

### 越界规则索引

| helper | 核对对象 | 统一规则 |
| --- | --- | --- |
| `load` | `offsets/sizes/strides` 对 `source.shape` | 对可静态判定场景执行 `offset + (size - 1) * stride < dim`，越界时报 `KernelCodeError` |
| `slice` | `offsets/sizes/strides` 对 `source.shape` | 与 `load` 共享同一组 rank / 正长度 / 越界规则 |
| `store` | `offsets/sizes/strides` 对 `target.shape`，且 `sizes == source.shape` | 先校验 rank，再校验 `sizes` 与源块一致，最后执行静态越界检查 |
| `deslice` | `offsets/sizes/strides` 对 `target.shape`，且 `sizes == source.shape` | 与 `store` 共享同一组大小与越界规则 |
| `view` | `offset/size/stride` 对 `source.shape` | 只检查窗口合法性，不要求 `numel` 相等；静态场景同样按 `offset + (size - 1) * stride < dim` 校验 |
| `reshape` | `shape` 对 `source` 连续布局与 `numel` | 不做窗口越界检查；只校验连续布局和静态 `numel` 一致 |
| `flatten` | `source` 连续布局 | 不做窗口越界检查；只校验连续布局 |

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本文件只定义 operation 层高层 API，不负责真实 DMA 硬件调度、带宽估算、异步执行、同步原语或 tile 策略选择。
- 本文件不负责逐元素算术、比较、归约、隐式 broadcast 或隐式 dtype 转换；显式广播必须通过 `broadcast(target, source)` 描述，元素表示变化必须通过显式 `cast` 描述。
- operation 到 dialect 的具体映射由 [`spec/dialect/dma.md`](../../spec/dialect/dma.md) 定义。
- `kernel_gen.operation.dma` 是 dma family 的完整稳定入口；`kernel_gen.operation` 顶层稳定重导出除 `fill` 与 `broadcast` 外的 dma helper。
- `fill` 与 `broadcast` 当前只属于 `kernel_gen.operation.dma` 子模块公开 API，不属于 `kernel_gen.operation` 顶层稳定导出集合。

### package-root 导出说明

| 入口 | 稳定公开 API | 说明 |
| --- | --- | --- |
| `kernel_gen.operation.dma` | `alloc / fill / free / copy / cast / broadcast / load / store / slice / deslice / view / reshape / flatten` | dma family 的完整稳定入口；`fill` 与 `broadcast` 只在该子模块路径公开 |
| `kernel_gen.operation` | `alloc / free / copy / cast / load / store / slice / deslice / view / reshape / flatten` | 包根重导出同一组 dma helper；不包含 `fill` 与 `broadcast`，且对象身份与 `kernel_gen.operation.dma` 保持一致 |

## API详细说明

### `alloc(shape: ShapeInput, dtype: NumericType, space: MemorySpace = MemorySpace.GM, stride: ShapeInput | None = None, format: Farmat = Farmat.Norm) -> Memory`

- api：`alloc(shape: ShapeInput, dtype: NumericType, space: MemorySpace = MemorySpace.GM, stride: ShapeInput | None = None, format: Farmat = Farmat.Norm) -> Memory`
- 参数：
  - `shape`：形状序列；类型 `ShapeInput`；无默认值；不允许 None；每个维度必须满足符号维度公开合同。
  - `dtype`：数值类型；类型 `NumericType`；无默认值；不允许 None；必须是公开 NumericType 或公开类型属性。
  - `space`：内存空间；类型 `MemorySpace`；默认值 `MemorySpace.GM`；传入时必须是公开 MemorySpace 或 MemorySpaceAttrAST。
  - `stride`：步幅序列；类型 `ShapeInput | None`；默认值 `None`；传入时长度必须与 shape 语义匹配。
  - `format`：内存布局格式；类型 `Farmat`；默认值 `Farmat.Norm`；必须是公开 Farmat 成员。
- 返回值：`Memory`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.operation import dma

    result = dma.alloc(shape=shape, dtype=dtype, space=space, stride=stride, format=format)
    ```
- 功能说明：执行 DMA operation `alloc` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `fill(target: Memory, value: int | float | str | SymbolDim) -> None`

- api：`fill(target: Memory, value: int | float | str | SymbolDim) -> None`
- 参数：
  - `target`：目标内存或目标节点；类型 `Memory`；无默认值；不允许 None；作为写入、填充或回写位置。
  - `value`：填充值；类型 `int | float | str | SymbolDim`；无默认值；不允许 None；`int` 不含 `bool`，`float` 必须有限，`str` 只允许 `"inf"` 与 `"-inf"`。
- 返回值：无返回值；调用成功表示对应 AST、IR 或 runtime 动作已完成。
- 使用示例：

  ```python
    from kernel_gen.operation import dma

    result = dma.fill(target=target, value=value)
    ```
- 功能说明：执行 DMA operation `fill` 的公开 Python 入口，表达对现有 `Memory` 的整块标量初始化意图。
- 注意事项：`target` 必须是公开 `Memory`；`value=True/False`、非有限 float（含 `inf/-inf/nan` float 对象）与任意非 `"inf"` / `"-inf"` 字符串必须在 helper 层拒绝；规范字符串 `"inf"` / `"-inf"` 只表达后续 MLIR 层面可物化的浮点无穷字面量。

### `free(value: Memory) -> None`

- api：`free(value: Memory) -> None`
- 参数：
  - `value`：输入值；类型 `Memory`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
- 返回值：无返回值；调用成功表示对应 AST、IR 或 runtime 动作已完成。
- 使用示例：

  ```python
    from kernel_gen.operation import dma

    result = dma.free(value=value)
    ```
- 功能说明：执行 DMA operation `free` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `copy(source: Memory, space: MemorySpace) -> Memory`

- api：`copy(source: Memory, space: MemorySpace) -> Memory`
- 参数：
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
  - `space`：内存空间；类型 `MemorySpace`；无默认值；传入时必须是公开 MemorySpace 或 MemorySpaceAttrAST。
- 返回值：`Memory`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.operation import dma

    result = dma.copy(source=source, space=space)
    ```
- 功能说明：执行 DMA operation `copy` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `broadcast(target: Memory, source: Memory) -> None`

- api：`broadcast(target: Memory, source: Memory) -> None`
- 参数：
  - `target`：目标 memory；类型 `Memory`；无默认值；不允许 None；作为显式广播物化写入位置。
  - `source`：源 memory；类型 `Memory`；无默认值；不允许 None；rank 必须小于等于 `target.rank`。
- 返回值：无返回值；调用成功表示 `source` 可按 broadcast 规则写入 `target`。
- 使用示例：

  ```python
    from kernel_gen.operation import dma

    dma.broadcast(target=target, source=source)
    ```
- 功能说明：校验显式 `dma.broadcast` 写回合同，不分配新 `Memory`。
- 注意事项：`source` 与 `target` dtype、space 必须一致；shape 按尾维对齐，静态维度只有相等或 source 维为 `1` 时兼容；动态维度保留运行期判断，不做 Python 侧 hack。

### `load(source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None, space: MemorySpace | None = None) -> Memory`

- api：`load(source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None, space: MemorySpace | None = None) -> Memory`
- 参数：
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
  - `offsets`：偏移序列；类型 `ShapeInput`；无默认值；不允许 None；长度必须与 sizes 匹配。
  - `sizes`：大小序列；类型 `ShapeInput`；无默认值；不允许 None；长度必须与 offsets 匹配。
  - `strides`：步幅序列；类型 `ShapeInput | None`；默认值 `None`；传入时长度必须与 sizes 或 shape 匹配。
  - `space`：内存空间；类型 `MemorySpace | None`；默认值 `None`；传入时必须是公开 MemorySpace 或 MemorySpaceAttrAST。
- 返回值：`Memory`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.operation import dma

    result = dma.load(source=source, offsets=offsets, sizes=sizes, strides=strides, space=space)
    ```
- 功能说明：执行 DMA operation `load` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `store(target: Memory, source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None) -> None`

- api：`store(target: Memory, source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None) -> None`
- 参数：
  - `target`：目标内存或目标节点；类型 `Memory`；无默认值；不允许 None；作为写入、填充或回写位置。
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
  - `offsets`：偏移序列；类型 `ShapeInput`；无默认值；不允许 None；长度必须与 sizes 匹配。
  - `sizes`：大小序列；类型 `ShapeInput`；无默认值；不允许 None；长度必须与 offsets 匹配。
  - `strides`：步幅序列；类型 `ShapeInput | None`；默认值 `None`；传入时长度必须与 sizes 或 shape 匹配。
- 返回值：无返回值；调用成功表示对应 AST、IR 或 runtime 动作已完成。
- 使用示例：

  ```python
    from kernel_gen.operation import dma

    result = dma.store(target=target, source=source, offsets=offsets, sizes=sizes, strides=strides)
    ```
- 功能说明：执行 DMA operation `store` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `slice(source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None, space: MemorySpace | None = None) -> Memory`

- api：`slice(source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None, space: MemorySpace | None = None) -> Memory`
- 参数：
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
  - `offsets`：偏移序列；类型 `ShapeInput`；无默认值；不允许 None；长度必须与 sizes 匹配。
  - `sizes`：大小序列；类型 `ShapeInput`；无默认值；不允许 None；长度必须与 offsets 匹配。
  - `strides`：步幅序列；类型 `ShapeInput | None`；默认值 `None`；传入时长度必须与 sizes 或 shape 匹配。
  - `space`：内存空间；类型 `MemorySpace | None`；默认值 `None`；传入时必须是公开 MemorySpace 或 MemorySpaceAttrAST。
- 返回值：`Memory`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.operation import dma

    result = dma.slice(source=source, offsets=offsets, sizes=sizes, strides=strides, space=space)
    ```
- 功能说明：执行 DMA operation `slice` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `deslice(target: Memory, source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None) -> None`

- api：`deslice(target: Memory, source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None) -> None`
- 参数：
  - `target`：目标内存或目标节点；类型 `Memory`；无默认值；不允许 None；作为写入、填充或回写位置。
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
  - `offsets`：偏移序列；类型 `ShapeInput`；无默认值；不允许 None；长度必须与 sizes 匹配。
  - `sizes`：大小序列；类型 `ShapeInput`；无默认值；不允许 None；长度必须与 offsets 匹配。
  - `strides`：步幅序列；类型 `ShapeInput | None`；默认值 `None`；传入时长度必须与 sizes 或 shape 匹配。
- 返回值：无返回值；调用成功表示对应 AST、IR 或 runtime 动作已完成。
- 使用示例：

  ```python
    from kernel_gen.operation import dma

    result = dma.deslice(target=target, source=source, offsets=offsets, sizes=sizes, strides=strides)
    ```
- 功能说明：执行 DMA operation `deslice` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `view(source: Memory, offset: ShapeInput, size: ShapeInput, stride: ShapeInput) -> Memory`

- api：`view(source: Memory, offset: ShapeInput, size: ShapeInput, stride: ShapeInput) -> Memory`
- 参数：
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
  - `offset`：偏移序列；类型 `ShapeInput`；无默认值；不允许 None；每个偏移必须是公开 ShapeInput。
  - `size`：大小序列；类型 `ShapeInput`；无默认值；不允许 None；每个分量必须是公开 ShapeInput。
  - `stride`：步幅序列；类型 `ShapeInput`；无默认值；传入时长度必须与 shape 语义匹配。
- 返回值：`Memory`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.operation import dma

    result = dma.view(source=source, offset=offset, size=size, stride=stride)
    ```
- 功能说明：执行 DMA operation `view` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `reshape(source: Memory, shape: ShapeInput) -> Memory`

- api：`reshape(source: Memory, shape: ShapeInput) -> Memory`
- 参数：
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
  - `shape`：形状序列；类型 `ShapeInput`；无默认值；不允许 None；每个维度必须满足符号维度公开合同。
- 返回值：`Memory`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.operation import dma

    result = dma.reshape(source=source, shape=shape)
    ```
- 功能说明：执行 DMA operation `reshape` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `flatten(source: Memory) -> Memory`

- api：`flatten(source: Memory) -> Memory`
- 参数：
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
- 返回值：`Memory`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.operation import dma

    result = dma.flatten(source=source)
    ```
- 功能说明：执行 DMA operation `flatten` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `cast(source: Memory, dtype: NumericType, memoryspace: MemorySpace | None = None) -> Memory`

- api：`cast(source: Memory, dtype: NumericType, memoryspace: MemorySpace | None = None) -> Memory`
- 参数：
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
  - `dtype`：数值类型；类型 `NumericType`；无默认值；不允许 None；必须是公开 NumericType 或公开类型属性。
  - `memoryspace`：目标内存空间；类型 `MemorySpace | None`；默认值 `None`；None 表示沿用源对象空间。
- 返回值：`Memory`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.operation import dma

    result = dma.cast(source=source, dtype=dtype, memoryspace=memoryspace)
    ```
- 功能说明：执行 DMA operation `cast` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `kernel_gen.operation.alloc(shape: ShapeInput, dtype: NumericType, space: MemorySpace = MemorySpace.GM, stride: ShapeInput | None = None, format: Farmat = Farmat.Norm) -> Memory`

- api：`kernel_gen.operation.alloc(shape: ShapeInput, dtype: NumericType, space: MemorySpace = MemorySpace.GM, stride: ShapeInput | None = None, format: Farmat = Farmat.Norm) -> Memory`
- 参数：
  - `shape`：形状序列；类型 `ShapeInput`；无默认值；不允许 None；每个维度必须满足符号维度公开合同。
  - `dtype`：数值类型；类型 `NumericType`；无默认值；不允许 None；必须是公开 NumericType 或公开类型属性。
  - `space`：内存空间；类型 `MemorySpace`；默认值 `MemorySpace.GM`；传入时必须是公开 MemorySpace 或 MemorySpaceAttrAST。
  - `stride`：步幅序列；类型 `ShapeInput | None`；默认值 `None`；传入时长度必须与 shape 语义匹配。
  - `format`：内存布局格式；类型 `Farmat`；默认值 `Farmat.Norm`；必须是公开 Farmat 成员。
- 返回值：`Memory`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    import kernel_gen.operation as operation

    result = operation.alloc(shape=shape, dtype=dtype, space=space, stride=stride, format=format)
    ```
- 功能说明：执行 DMA operation `kernel_gen.operation.alloc` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `kernel_gen.operation.dma.fill(target: Memory, value: int | float | str | SymbolDim) -> None`

- api：`kernel_gen.operation.dma.fill(target: Memory, value: int | float | str | SymbolDim) -> None`
- 参数：
  - `target`：目标内存或目标节点；类型 `Memory`；无默认值；不允许 None；作为写入、填充或回写位置。
  - `value`：填充值；类型 `int | float | str | SymbolDim`；无默认值；不允许 None；`int` 不含 `bool`，`float` 必须有限，`str` 只允许 `"inf"` 与 `"-inf"`。
- 返回值：无返回值；调用成功表示对应 AST、IR 或 runtime 动作已完成。
- 使用示例：

  ```python
    import kernel_gen.operation as operation

    operation.dma.fill(target=target, value=value)
    ```
- 功能说明：执行 DMA operation `kernel_gen.operation.dma.fill` 的公开 Python 入口，表达对现有 `Memory` 的整块标量初始化意图。
- 注意事项：`target` 必须是公开 `Memory`；`value=True/False`、非有限 float（含 `inf/-inf/nan` float 对象）与任意非 `"inf"` / `"-inf"` 字符串必须在 helper 层拒绝；规范字符串 `"inf"` / `"-inf"` 只表达后续 MLIR 层面可物化的浮点无穷字面量。

### `kernel_gen.operation.dma.broadcast(target: Memory, source: Memory) -> None`

- api：`kernel_gen.operation.dma.broadcast(target: Memory, source: Memory) -> None`
- 参数：
  - `target`：目标 memory；类型 `Memory`；无默认值；不允许 None；作为显式广播物化写入位置。
  - `source`：源 memory；类型 `Memory`；无默认值；不允许 None；rank 必须小于等于 `target.rank`。
- 返回值：无返回值；调用成功表示 `source` 可按 broadcast 规则写入 `target`。
- 使用示例：

  ```python
    import kernel_gen.operation as operation

    operation.dma.broadcast(target=target, source=source)
    ```
- 功能说明：执行 DMA operation `kernel_gen.operation.dma.broadcast` 的公开 Python 入口，校验显式广播写回合同。
- 注意事项：`broadcast` 不属于 `kernel_gen.operation` 顶层稳定导出；调用方必须通过 `kernel_gen.operation.dma.broadcast` 或 `from kernel_gen.operation import dma` 访问。

### `kernel_gen.operation.free(value: Memory) -> None`

- api：`kernel_gen.operation.free(value: Memory) -> None`
- 参数：
  - `value`：输入值；类型 `Memory`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
- 返回值：无返回值；调用成功表示对应 AST、IR 或 runtime 动作已完成。
- 使用示例：

  ```python
    import kernel_gen.operation as operation

    result = operation.free(value=value)
    ```
- 功能说明：执行 DMA operation `kernel_gen.operation.free` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `kernel_gen.operation.copy(source: Memory, space: MemorySpace) -> Memory`

- api：`kernel_gen.operation.copy(source: Memory, space: MemorySpace) -> Memory`
- 参数：
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
  - `space`：内存空间；类型 `MemorySpace`；无默认值；传入时必须是公开 MemorySpace 或 MemorySpaceAttrAST。
- 返回值：`Memory`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    import kernel_gen.operation as operation

    result = operation.copy(source=source, space=space)
    ```
- 功能说明：执行 DMA operation `kernel_gen.operation.copy` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `kernel_gen.operation.load(source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None, space: MemorySpace | None = None) -> Memory`

- api：`kernel_gen.operation.load(source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None, space: MemorySpace | None = None) -> Memory`
- 参数：
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
  - `offsets`：偏移序列；类型 `ShapeInput`；无默认值；不允许 None；长度必须与 sizes 匹配。
  - `sizes`：大小序列；类型 `ShapeInput`；无默认值；不允许 None；长度必须与 offsets 匹配。
  - `strides`：步幅序列；类型 `ShapeInput | None`；默认值 `None`；传入时长度必须与 sizes 或 shape 匹配。
  - `space`：内存空间；类型 `MemorySpace | None`；默认值 `None`；传入时必须是公开 MemorySpace 或 MemorySpaceAttrAST。
- 返回值：`Memory`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    import kernel_gen.operation as operation

    result = operation.load(source=source, offsets=offsets, sizes=sizes, strides=strides, space=space)
    ```
- 功能说明：执行 DMA operation `kernel_gen.operation.load` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `kernel_gen.operation.store(target: Memory, source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None) -> None`

- api：`kernel_gen.operation.store(target: Memory, source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None) -> None`
- 参数：
  - `target`：目标内存或目标节点；类型 `Memory`；无默认值；不允许 None；作为写入、填充或回写位置。
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
  - `offsets`：偏移序列；类型 `ShapeInput`；无默认值；不允许 None；长度必须与 sizes 匹配。
  - `sizes`：大小序列；类型 `ShapeInput`；无默认值；不允许 None；长度必须与 offsets 匹配。
  - `strides`：步幅序列；类型 `ShapeInput | None`；默认值 `None`；传入时长度必须与 sizes 或 shape 匹配。
- 返回值：无返回值；调用成功表示对应 AST、IR 或 runtime 动作已完成。
- 使用示例：

  ```python
    import kernel_gen.operation as operation

    result = operation.store(target=target, source=source, offsets=offsets, sizes=sizes, strides=strides)
    ```
- 功能说明：执行 DMA operation `kernel_gen.operation.store` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `kernel_gen.operation.slice(source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None, space: MemorySpace | None = None) -> Memory`

- api：`kernel_gen.operation.slice(source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None, space: MemorySpace | None = None) -> Memory`
- 参数：
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
  - `offsets`：偏移序列；类型 `ShapeInput`；无默认值；不允许 None；长度必须与 sizes 匹配。
  - `sizes`：大小序列；类型 `ShapeInput`；无默认值；不允许 None；长度必须与 offsets 匹配。
  - `strides`：步幅序列；类型 `ShapeInput | None`；默认值 `None`；传入时长度必须与 sizes 或 shape 匹配。
  - `space`：内存空间；类型 `MemorySpace | None`；默认值 `None`；传入时必须是公开 MemorySpace 或 MemorySpaceAttrAST。
- 返回值：`Memory`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    import kernel_gen.operation as operation

    result = operation.slice(source=source, offsets=offsets, sizes=sizes, strides=strides, space=space)
    ```
- 功能说明：执行 DMA operation `kernel_gen.operation.slice` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `kernel_gen.operation.deslice(target: Memory, source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None) -> None`

- api：`kernel_gen.operation.deslice(target: Memory, source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None) -> None`
- 参数：
  - `target`：目标内存或目标节点；类型 `Memory`；无默认值；不允许 None；作为写入、填充或回写位置。
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
  - `offsets`：偏移序列；类型 `ShapeInput`；无默认值；不允许 None；长度必须与 sizes 匹配。
  - `sizes`：大小序列；类型 `ShapeInput`；无默认值；不允许 None；长度必须与 offsets 匹配。
  - `strides`：步幅序列；类型 `ShapeInput | None`；默认值 `None`；传入时长度必须与 sizes 或 shape 匹配。
- 返回值：无返回值；调用成功表示对应 AST、IR 或 runtime 动作已完成。
- 使用示例：

  ```python
    import kernel_gen.operation as operation

    result = operation.deslice(target=target, source=source, offsets=offsets, sizes=sizes, strides=strides)
    ```
- 功能说明：执行 DMA operation `kernel_gen.operation.deslice` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `kernel_gen.operation.view(source: Memory, offset: ShapeInput, size: ShapeInput, stride: ShapeInput) -> Memory`

- api：`kernel_gen.operation.view(source: Memory, offset: ShapeInput, size: ShapeInput, stride: ShapeInput) -> Memory`
- 参数：
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
  - `offset`：偏移序列；类型 `ShapeInput`；无默认值；不允许 None；每个偏移必须是公开 ShapeInput。
  - `size`：大小序列；类型 `ShapeInput`；无默认值；不允许 None；每个分量必须是公开 ShapeInput。
  - `stride`：步幅序列；类型 `ShapeInput`；无默认值；传入时长度必须与 shape 语义匹配。
- 返回值：`Memory`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    import kernel_gen.operation as operation

    result = operation.view(source=source, offset=offset, size=size, stride=stride)
    ```
- 功能说明：执行 DMA operation `kernel_gen.operation.view` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `kernel_gen.operation.reshape(source: Memory, shape: ShapeInput) -> Memory`

- api：`kernel_gen.operation.reshape(source: Memory, shape: ShapeInput) -> Memory`
- 参数：
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
  - `shape`：形状序列；类型 `ShapeInput`；无默认值；不允许 None；每个维度必须满足符号维度公开合同。
- 返回值：`Memory`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    import kernel_gen.operation as operation

    result = operation.reshape(source=source, shape=shape)
    ```
- 功能说明：执行 DMA operation `kernel_gen.operation.reshape` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `kernel_gen.operation.flatten(source: Memory) -> Memory`

- api：`kernel_gen.operation.flatten(source: Memory) -> Memory`
- 参数：
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
- 返回值：`Memory`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    import kernel_gen.operation as operation

    result = operation.flatten(source=source)
    ```
- 功能说明：执行 DMA operation `kernel_gen.operation.flatten` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

### `kernel_gen.operation.cast(source: Memory, dtype: NumericType, memoryspace: MemorySpace | None = None) -> Memory`

- api：`kernel_gen.operation.cast(source: Memory, dtype: NumericType, memoryspace: MemorySpace | None = None) -> Memory`
- 参数：
  - `source`：源码对象或 source 属性；类型 `Memory`；无默认值；不得写入不可序列化的公开状态。
  - `dtype`：数值类型；类型 `NumericType`；无默认值；不允许 None；必须是公开 NumericType 或公开类型属性。
  - `memoryspace`：目标内存空间；类型 `MemorySpace | None`；默认值 `None`；None 表示沿用源对象空间。
- 返回值：`Memory`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    import kernel_gen.operation as operation

    result = operation.cast(source=source, dtype=dtype, memoryspace=memoryspace)
    ```
- 功能说明：执行 DMA operation `kernel_gen.operation.cast` 的公开 Python 入口，返回或修改 `Memory` 对象。
- 注意事项：输入 `Memory`、shape、stride、offset、size、dtype 和 space 必须满足 `symbol_variable` 公开合同；返回值式 helper 不暴露 lowering 内部 op。

## 测试

- 测试文件：
  - `test/dsl/ast/test_package.py`
  - `test/operation/test_dma.py`
  - `test/operation/test_dma_alloc_lifecycle.py`
  - `test/operation/test_package.py`
- 执行命令：`pytest -q test/operation/test_dma.py test/operation/test_package.py test/dsl/ast/test_package.py`

### 测试目标

- 验证 `alloc/free` 的输入约束与返回口径。
- 验证 `fill` 的公开 helper 入口、字符串字面量白名单与“不返回新 Memory”的语义。
- 验证 `copy/cast` 的规格继承与目标空间/类型覆盖语义。
- 验证 `broadcast` 的 target/source dtype、space、rank 与尾维 broadcast 规则。
- 验证 `load/slice` 的返回 `shape/dtype/space/format` 语义与索引校验。
- 验证 `store/deslice` 的源块大小约束、dtype 校验与索引边界。
- 验证 `view` 的 `offset/size/stride` 子视图语义与返回 `Memory` 规格继承规则。
- 验证 `reshape/flatten` 的连续布局要求与结果形状规则。
- 验证 `kernel_gen.operation` 顶层继续稳定重导出 `alloc/free/copy/load/store/slice/deslice/view/reshape/flatten/cast`，且对象身份与 `kernel_gen.operation.dma` 一致。
- 验证 `fill` 与 `broadcast` 不会上提到 `kernel_gen.operation` 顶层，且 parser 只通过 `kernel_gen.operation.dma.fill` / `kernel_gen.operation.dma.broadcast` 的公开 helper 路径消费它们。
- 验证测试编号 `TC-OP-DMA-AF-001..007` 与 `TC-OP-DMA-001..034` 在文档和测试文件中一一对应。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-OP-DMA-AF-001 | 内存/DMA | `alloc` 基础分配 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`alloc` 基础分配”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-AF-007 | 内存/DMA | `alloc` 默认 space/stride | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`alloc` 默认 space/stride”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-AF-002 | 内存/DMA | `alloc` 显式 stride | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`alloc` 显式 stride”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-AF-003 | 边界/异常 | `alloc` 非法 shape/stride | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test/operation/test_dma.py`。 | “`alloc` 非法 shape/stride”场景按公开错误语义失败或被拒绝。 | `test/operation/test_dma.py` |
| TC-OP-DMA-AF-004 | 内存/DMA | `free` 基础释放 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`free` 基础释放”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-AF-005 | 内存/DMA | `free` 类型错误 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`free` 类型错误”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-AF-006 | 内存/DMA | `alloc` 类型错误 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`alloc` 类型错误”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-001 | 内存/DMA | `copy` 目标空间 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`copy` 目标空间”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-002 | 内存/DMA | `copy` 类型错误 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`copy` 类型错误”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-003 | 内存/DMA | `load` 结果空间 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`load` 结果空间”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-004 | 内存/DMA | `slice` 结果形状 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`slice` 结果形状”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-005 | 内存/DMA | `store` 大小校验 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`store` 大小校验”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-006 | 内存/DMA | `deslice` 大小校验 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`deslice` 大小校验”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-007 | 内存/DMA | 索引长度约束 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“索引长度约束”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-008 | 内存/DMA | stride 边界 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“stride 边界”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-009 | 内存/DMA | 类型错误 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“类型错误”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-010 | 内存/DMA | `copy` 规格继承 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`copy` 规格继承”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-011 | 内存/DMA | `cast` 基础转换 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`cast` 基础转换”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-012 | 边界/异常 | `cast` 非法 dtype | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test/operation/test_dma.py`。 | “`cast` 非法 dtype”场景按公开错误语义失败或被拒绝。 | `test/operation/test_dma.py` |
| TC-OP-DMA-013 | 内存/DMA | `cast` 数值类型转换 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma_alloc_lifecycle.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`cast` 数值类型转换”场景。 | `test/operation/test_dma_alloc_lifecycle.py` |
| TC-OP-DMA-014 | 内存/DMA | `view` 子视图基础语义 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`view` 子视图基础语义”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-015 | 内存/DMA | `view` 规格与 stride 组合 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`view` 规格与 stride 组合”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-016 | 内存/DMA | `view` 边界校验 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`view` 边界校验”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-017 | 内存/DMA | `flatten` 连续布局 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`flatten` 连续布局”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-018 | 内存/DMA | `flatten` 非连续布局 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`flatten` 非连续布局”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-019 | 内存/DMA | `reshape` 基础变换 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`reshape` 基础变换”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-020 | 内存/DMA | `reshape` 连续布局 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`reshape` 连续布局”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-021 | 边界/异常 | `reshape` 非法参数 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test/operation/test_dma.py`。 | “`reshape` 非法参数”场景按公开错误语义失败或被拒绝。 | `test/operation/test_dma.py` |
| TC-OP-DMA-022 | 内存/DMA | `cast` 空间覆盖 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`cast` 空间覆盖”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-023 | 内存/DMA | `load` 空间类型错误 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`load` 空间类型错误”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-024 | 内存/DMA | `load` sizes 正长度 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`load` sizes 正长度”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-025 | 边界/异常 | `store/deslice` dtype mismatch | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test/operation/test_dma.py`。 | “`store/deslice` dtype mismatch”场景按公开错误语义失败或被拒绝。 | `test/operation/test_dma.py` |
| TC-OP-DMA-026 | 内存/DMA | `store` 基础写回 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`store` 基础写回”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-027 | 内存/DMA | `cast` 支持转换 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`cast` 支持转换”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-028 | 边界/异常 | `view` 非法参数 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test/operation/test_dma.py`。 | “`view` 非法参数”场景按公开错误语义失败或被拒绝。 | `test/operation/test_dma.py` |
| TC-OP-DMA-029 | 内存/DMA | `fill` 基础初始化 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`fill` 基础初始化”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-030 | 内存/DMA | `fill` 字符串字面量白名单 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test/operation/test_dma.py`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`fill` 字符串字面量白名单”场景。 | `test/operation/test_dma.py` |
| TC-OP-DMA-031 | 公开入口 | `fill` 与 `broadcast` 顶层导出边界 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test/operation/test_package.py`。 | `fill` 与 `broadcast` 可从 `kernel_gen.operation.dma` 访问，但不在 `kernel_gen.operation` 顶层公开。 | `test/operation/test_package.py` |
| TC-OP-DMA-032 | 公开入口 | `fill` AST 公开 helper 路径 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test/dsl/ast/test_package.py`。 | 公开入口在“`fill` AST 公开 helper 路径”场景下可导入、构造、注册或按名称发现。 | `test/dsl/ast/test_package.py` |
| TC-OP-DMA-033 | 公开入口 | `fill` kernel 只读合同资产 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `expectation/kernel/flash_attention.py`, `expectation/kernel/matmul.py`。 | 公开入口在“`fill` kernel 只读合同资产”场景下可导入、构造、注册或按名称发现。 | `expectation/kernel/flash_attention.py`, `expectation/kernel/matmul.py` |
| TC-OP-DMA-034 | 内存/DMA | `broadcast` 显式写回 | 准备 target/source dtype、space 一致且尾维可 broadcast 的 Memory。 | 运行 `test/operation/test_dma.py`。 | helper 返回 `None`；非法 rank、dtype、space 或静态 shape 按公开错误语义失败。 | `test_dma_broadcast_accepts_public_memory_and_rejects_invalid_contracts` |
