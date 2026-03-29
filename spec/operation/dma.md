# dma.md

## 功能简介

定义 `Memory` 的数据搬运、视图变换与生命周期操作规范，提供 `alloc/free/copy/cast/load/store/slice/deslice/view/reshape/flatten` 的输入约束、输出语义与错误边界。该层面对高层 API，负责描述搬运意图与视图范围；方言层语义由 [`spec/dialect/dma.md`](../../spec/dialect/dma.md) 定义。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/operation/dma.md`](../../spec/operation/dma.md)
- `功能实现`：[`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py)
- `test`：[`test/operation/test_operation_dma.py`](../../test/operation/test_operation_dma.py)

## 依赖

- [`spec/dialect/dma.md`](../../spec/dialect/dma.md)：方言层搬运语义映射。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：`Memory`、`MemorySpace`、`shape/stride/format` 语义。
- [`spec/symbol_variable/symbol_shape.md`](../../spec/symbol_variable/symbol_shape.md)：`SymbolShape` 与索引列表规范。
- [`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)：`NumericType` 定义。
- [`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py)：高层 API 实现。
- [`kernel_gen/symbol_variable/memory.py`](../../kernel_gen/symbol_variable/memory.py)：`Memory` 与 `MemorySpace` 实现。

## 目标

- 为 `Memory` 提供统一、稳定的搬运与视图操作语义入口。
- 明确 `alloc/free/copy/cast/load/store/slice/deslice/view/reshape/flatten` 的输入约束、输出语义与错误边界。
- 保留动态 `shape` 与 `offsets/sizes/strides` 的表达能力，支持后续 lowering 保留切片信息。

## 限制与边界

- 不负责真实 DMA 硬件调度、带宽估算、异步执行或同步原语（event/barrier/token/stream）。
- 不负责逐元素算术、比较、广播、归约等计算语义。
- 不负责隐式元素类型转换；元素表示变化必须通过显式 `cast` 描述。
- 不负责自动选择最优搬运空间、tile 大小或 stride。
- `alloc/free` 仅定义高层生命周期语义，不承担搬运语义。
- 搬运操作不改变元素值语义，只改变数据的逻辑位置、覆盖范围或所在空间。
- `view/reshape/flatten` 不做数据搬运，仅调整张量视图的 `shape/stride` 描述。
- `offsets/sizes/strides` 长度必须与相关 `Memory.rank` 一致；`sizes` 中静态维度必须为正。
- `offsets` 中静态值必须为非负整数；`sizes/strides` 中静态值必须为正整数；动态值使用符号整型表达。
- 对于可静态判定的场景，必须检查边界：`offset + (size - 1) * stride < dim`，越界时显式报错。
- `load/slice` 的 `strides` 仅作为访问步进参与校验，不会写入返回 `Memory.stride`。
- `load/slice/store/deslice` 允许非单位 `strides` 作为访问步进并执行边界校验；但当前 `dma dialect` 仅支持单位步长语义，进入方言层时任一维 `stride != 1` 必须显式报错，以避免生成无法验证的方言 op。
- `store/deslice` 的 `sizes` 必须与 `source.shape` 一致。
- `copy/cast` 仅改变 `Memory` 规格，不负责数据填充或变形。
- `view` 不提供 `space` 或 `memoryspec` 参数；返回值总是继承 `source` 的 `dtype/space/format/stride`。
- `view` 的 `stride` 参数只用于描述 subview 窗口步进与边界检查，不会覆盖返回值的 `Memory.stride`。
- `view` 在 operation 层不要求 `source.shape` 与 `size` 的 `numel` 相等，只要求窗口边界合法。
- operation 到 dialect 的映射边界：`view` 的 `offset/size/stride` 必须在调用点直接保留并传递给方言；仅依赖 `view` 返回的 `Memory` 无法恢复完整 subview 参数。

## 公开接口

### alloc(shape, dtype, space=MemorySpace.GM, stride=None)

功能说明：

- 分配新的 `Memory` 描述对象，定义逻辑 `shape/dtype/space/stride`。

参数说明：

- `shape: Sequence | SymbolShape`：维度序列或 `SymbolShape`，元素可为正整数、符号名或符号整型表达。
- `dtype: NumericType`：元素类型。
- `space: MemorySpace`：内存空间，默认 `MemorySpace.GM`。
- `stride: Sequence | SymbolShape | None`：可选步长序列；未传入时生成默认连续 stride。

使用示例：

```python
buf = alloc([32, 32], NumericType.Float32, space=MemorySpace.SM, stride=[1, 1])
```

注意事项：

- `shape/stride` 必须可被 `SymbolShape` 规范化，且 rank 必须一致。
- `dtype` 必须为 `NumericType`，`space` 必须为 `MemorySpace`。
- 未提供 `stride` 时，按连续布局生成默认 stride。

非法输入：

- `shape/stride` 无法规范化或 rank 不一致时必须抛出 `ValueError`。
- `dtype` 非 `NumericType` 或 `space` 非 `MemorySpace` 时必须抛出 `TypeError`。

返回与限制：

- 返回新的 `Memory`，`format` 使用 `Memory` 默认格式。
- 不隐含数据搬运、初始化填充或跨空间拷贝。

### free(value)

功能说明：

- 结束某个 `Memory` 描述对象的高层生命周期。

参数说明：

- `value: Memory`：待释放对象。

使用示例：

```python
free(buf)
```

注意事项：

- 非 `Memory` 输入必须报 `TypeError`。

非法输入：

- `value` 不是 `Memory` 时必须抛出 `TypeError`。

返回与限制：

- 返回 `None`，不产生新的 `Memory`。

### copy(source, space)

功能说明：

- 返回新的 `Memory` 描述，保留 `source` 的规格，仅切换到目标空间。

参数说明：

- `source: Memory`：源内存。
- `space: MemorySpace`：目标内存空间。

使用示例：

```python
dst = copy(src, MemorySpace.SM)
```

注意事项：

- `source` 必须为 `Memory`，`space` 必须为 `MemorySpace`。
- 返回结果仅描述搬运意图，不执行实际数据拷贝。

非法输入：

- `source` 不是 `Memory` 或 `space` 不是 `MemorySpace` 时必须抛出 `TypeError`。

返回与限制：

- 返回新的 `Memory`，`shape/stride/dtype/format` 继承 `source`，`space` 由参数决定。

### cast(source, dtype, memoryspace=None)

功能说明：

- 显式转换 `source` 的元素类型，并返回新的 `Memory` 描述。

参数说明：

- `source: Memory`：源块。
- `dtype: NumericType`：目标元素类型。
- `memoryspace: MemorySpace | None`：可选目标空间；`None` 表示沿用 `source.space`。

使用示例：

```python
dst = cast(src, NumericType.Float16, memoryspace=MemorySpace.GM)
```

注意事项：

- `dtype` 必须为合法的 `NumericType`，`memoryspace` 若提供必须为 `MemorySpace`。
- 不支持的转换路径必须显式报错。

非法输入：

- `source` 不是 `Memory`、`dtype` 非 `NumericType` 或 `memoryspace` 非 `MemorySpace|None` 时必须抛出 `TypeError`。
- 不支持的转换路径必须抛出 `NotImplementedError`。

返回与限制：

- 返回新的 `Memory`，其 `shape/stride/format` 继承 `source`，`dtype` 与 `space` 按参数覆盖。

### load(source, offsets, sizes, strides=None, space=None)

功能说明：

- 从 `source` 读取切片块并返回新的结果块。

参数说明：

- `source: Memory`：源内存。
- `offsets: Sequence | SymbolShape`：索引列表或 `SymbolShape`。
- `sizes: Sequence | SymbolShape`：索引列表或 `SymbolShape`，作为返回块 `shape`。
- `strides: Sequence | SymbolShape | None`：可选步进序列；`None` 表示单位步进。
- `space: MemorySpace | None`：目标空间；`None` 表示沿用 `source.space`。

使用示例：

```python
tile = load(src, offsets=[0, 0], sizes=[32, 32], strides=[1, 1], space=MemorySpace.SM)
```

注意事项：

- `offsets/sizes/strides` 长度必须与 `source.rank` 一致。
- `sizes` 中静态维度必须为正。
- 对于可静态判定的场景，必须进行边界检查。
- 当 `offsets/sizes/strides` 含 `SymbolDim` 或 `?` 且无法静态判定越界时，允许通过并保留符号表达。

非法输入：

- `source` 不是 `Memory` 或 `space` 非 `MemorySpace|None` 时必须抛出 `TypeError`。
- `offsets/sizes/strides` 与 `source.rank` 不一致、`sizes` 含非正静态维度、或静态边界校验失败时必须抛出 `ValueError`。

返回与限制：

- 返回新的 `Memory`，其 `shape == sizes`，`dtype/format` 继承 `source`。
- 返回结果 `stride` 按连续布局生成，与 `strides` 无关。

### slice(source, offsets, sizes, strides=None, space=None)

功能说明：

- 从 `source` 抽取切片块；语义等价于 `load`，强调“切片”语义。

参数说明：

- `source: Memory`：源内存。
- `offsets: Sequence | SymbolShape`：索引列表或 `SymbolShape`。
- `sizes: Sequence | SymbolShape`：索引列表或 `SymbolShape`。
- `strides: Sequence | SymbolShape | None`：可选步进序列；`None` 表示单位步进。
- `space: MemorySpace | None`：目标空间；`None` 表示沿用 `source.space`。

使用示例：

```python
sub = slice(src, offsets=[0, 16], sizes=[8, 8], strides=[1, 1], space=MemorySpace.LM)
```

注意事项：

- 校验规则与 `load` 一致。

非法输入：

- `source` 不是 `Memory` 时必须抛出 `TypeError`。
- 其余 rank/边界/`sizes` 约束与 `load` 相同，违反时必须抛出 `ValueError`。

返回与限制：

- 返回新的 `Memory`；内部复用 `load` 的语义。

### store(source, target, offsets, sizes, strides=None)

功能说明：

- 将 `source` 块写回 `target` 的指定区域。

参数说明：

- `source: Memory`：源块。
- `target: Memory`：目标内存。
- `offsets: Sequence | SymbolShape`：索引列表或 `SymbolShape`。
- `sizes: Sequence | SymbolShape`：索引列表或 `SymbolShape`，必须与 `source.shape` 一致。
- `strides: Sequence | SymbolShape | None`：可选步进序列；`None` 表示单位步进。

使用示例：

```python
store(tile, dst, offsets=[0, 0], sizes=[32, 32], strides=[1, 1])
```

注意事项：

- `source.dtype == target.dtype`。
- `offsets/sizes/strides` 长度必须与 `target.rank` 一致。
- `source.shape` 必须与 `sizes` 一致。
- 对于可静态判定的场景，必须进行边界检查。

非法输入：

- `source` 或 `target` 不是 `Memory` 时必须抛出 `TypeError`。
- `source.dtype != target.dtype` 时必须抛出 `TypeError`。
- `sizes` 与 `source.shape` 不一致、或静态边界校验失败时必须抛出 `ValueError`。

返回与限制：

- 返回 `None`。

### deslice(source, target, offsets, sizes, strides=None)

功能说明：

- 将切片块写回 `target` 的指定区域；语义等价于 `store`，强调“局部区域更新”。

参数说明：

- `source: Memory`：源块。
- `target: Memory`：目标内存。
- `offsets: Sequence | SymbolShape`：索引列表或 `SymbolShape`。
- `sizes: Sequence | SymbolShape`：索引列表或 `SymbolShape`，必须与 `source.shape` 一致。
- `strides: Sequence | SymbolShape | None`：可选步进序列；`None` 表示单位步进。

使用示例：

```python
deslice(sub, dst, offsets=[0, 16], sizes=[32, 32], strides=[1, 1])
```

注意事项：

- 校验规则与 `store` 一致。

非法输入：

- `source` 或 `target` 不是 `Memory` 时必须抛出 `TypeError`。
- `source.dtype != target.dtype` 时必须抛出 `TypeError`。
- 其余大小/边界约束与 `store` 相同，违反时必须抛出 `ValueError`。

返回与限制：

- 返回 `None`。

### view(source, offset, size, stride)

功能说明：

- 返回 `source` 的子视图结果，仅描述从 `source` 上切出的逻辑窗口。
- `offset/size/stride` 用于保留 subview lowering 所需的范围信息；该操作本身不做数据搬运。

参数说明：

- `source: Memory`：源内存。
- `offset: Sequence | SymbolShape`：子视图起始偏移，长度必须与 `source.rank` 一致。
- `size: Sequence | SymbolShape`：子视图逻辑大小，返回结果的 `shape` 固定等于该参数。
- `stride: Sequence | SymbolShape`：子视图步进，长度必须与 `source.rank` 一致。

使用示例：

```python
src = Memory(["M", "K"], NumericType.Float32)
sub = view(src, offset=["M_t", "K_t"], size=[2, 2], stride=["stride", 1])
```

注意事项：

- `offset/size/stride` 都必须可被 `SymbolShape` 规范化，且长度必须与 `source.rank` 一致。
- `size` 中静态维度必须为正。
- `stride` 仅用于描述子视图访问步进，不等同于返回 `Memory` 的连续布局步幅。
- `view` 仅做窗口合法性检查，不要求 `source.shape` 与 `size` 的 `numel` 在 operation 层相等。
- 对于可静态判定的场景，必须进行边界检查。
- 当 `offset/size/stride` 含 `SymbolDim` 或 `?` 且无法静态判定越界时，允许通过并保留符号表达。

非法输入：

- `source` 不是 `Memory` 时必须抛出 `TypeError`。
- `offset/size/stride` 长度与 rank 不一致、`offset` 含负值、`size/stride` 含非正静态值或静态边界校验失败时必须抛出 `ValueError`。

返回与限制：

- 返回新的 `Memory`，其 `shape == size`，`dtype/space/format/stride` 继承 `source`。

### reshape(source, shape)

功能说明：

- 返回 `source` 的形状重塑结果，仅调整 `shape/stride` 元信息。
- 等价于对连续布局的 `source` 进行视图重塑。

参数说明：

- `source: Memory`：源内存。
- `shape: Sequence | SymbolShape`：目标形状。

使用示例：

```python
src = Memory([2, 3, 4], NumericType.Float32)
dst = reshape(src, shape=[6, 4])
```

注意事项：

- `shape` 必须可被 `SymbolShape` 规范化。
- `source` 必须是连续布局；非连续布局必须显式报错。
- 若可判定，`shape` 的元素总数必须与 `source.shape` 一致。

非法输入：

- `source` 不是 `Memory` 时必须抛出 `TypeError`。
- `shape` 无法规范化、`source` 非连续布局或静态元素总数不一致时必须抛出 `ValueError`。

返回与限制：

- 返回新的 `Memory`，其 `dtype/space/format` 继承 `source`。
- 返回的 `stride` 按连续行主序生成。

### flatten(source)

功能说明：

- 将 `source` 展平成一维视图，返回新的 `Memory`。
- 语义等价于把 `source` 视为连续内存并生成 `shape=[prod(shape)]` 的视图。

参数说明：

- `source: Memory`：源内存。

使用示例：

```python
src = Memory([2, 3, 4], NumericType.Float32)
dst = flatten(src)
```

注意事项：

- `source` 必须是连续布局；非连续布局必须显式报错。
- 展平后的 `shape` 为所有维度长度的乘积；符号维度使用无空格 `*` 表达式。

非法输入：

- `source` 不是 `Memory` 时必须抛出 `TypeError`。
- `source` 非连续布局时必须抛出 `ValueError`。

返回与限制：

- 返回新的 `Memory`，其 `shape` 为一维，`stride` 为 `[1]`。
- 返回结果的 `dtype/space/format` 继承 `source`。

## 测试

- 测试文件：[`test/operation/test_operation_dma.py`](../../test/operation/test_operation_dma.py)
- 执行命令：`pytest -q test/operation/test_operation_dma.py`

### 测试目标

- 验证 `alloc/free` 的输入约束与返回口径。
- 验证 `copy/cast` 的规格继承与目标空间/类型覆盖语义。
- 验证 `load/slice` 的返回 `shape/dtype/space/format` 语义与索引校验。
- 验证 `store/deslice` 的源块大小约束、dtype 校验与索引边界。
- 验证 `view` 的 `offset/size/stride` 子视图语义与返回 `Memory` 规格继承规则。
- 验证 `reshape/flatten` 的连续布局要求与结果形状规则。
- 验证测试编号 `TC-OP-DMA-AF-001..007` 与 `TC-OP-DMA-001..028` 在文档和测试文件中一一对应。

### 功能与用例清单

| 用例 ID | 测试点 | 说明 | 建议测试 | 测试文件 |
| --- | --- | --- | --- | --- |
| TC-OP-DMA-AF-001 | `alloc` 基础分配 | 返回带指定 `shape/dtype/space` 的 `Memory` | `test_alloc_returns_memory` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-AF-007 | `alloc` 默认 space/stride | 未提供 `space` 时默认 `MemorySpace.GM`，未提供 `stride` 时按连续布局生成默认 stride | `test_alloc_default_stride_for_symbolic_shape` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-AF-002 | `alloc` 显式 stride | 显式 `stride` 被正确保留到返回 `Memory` | `test_alloc_preserves_explicit_stride` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-AF-003 | `alloc` 非法 shape/stride | 非法 `shape` 或 rank/stride 不一致时报错 | `test_alloc_invalid_shape_or_stride` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-AF-004 | `free` 基础释放 | `free` 接受 `Memory` 并返回 `None` | `test_free_returns_none` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-AF-005 | `free` 类型错误 | 非 `Memory` 输入触发 `TypeError` | `test_free_type_error` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-AF-006 | `alloc` 类型错误 | `dtype/space` 类型不合法触发错误 | `test_alloc_invalid_dtype_or_space` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-001 | `copy` 目标空间 | `copy` 返回新 `Memory`，仅 `space` 被覆盖 | `test_copy_success` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-002 | `copy` 类型错误 | `source` 或 `space` 类型非法时报错 | `test_copy_type_error` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-003 | `load` 结果空间 | `load` 返回结果块并切换到目标空间 | `test_load_result_space` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-004 | `slice` 结果形状 | `slice` 返回块的 `shape` 等于 `sizes` | `test_slice_result_shape` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-005 | `store` 大小校验 | `source.shape` 与写回大小不一致时报错 | `test_store_size_mismatch` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-006 | `deslice` 大小校验 | `source.shape` 与回写区域大小不一致时报错 | `test_deslice_size_mismatch` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-007 | 索引长度约束 | `offsets/sizes/strides` 长度与 rank 不一致时报错 | `test_dma_index_rank_mismatch` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-008 | stride 边界 | 非单位 stride 需进行边界校验 | `test_dma_non_unit_stride_checked` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-009 | 类型错误 | 非 `Memory` 输入触发 `TypeError` | `test_dma_type_error` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-010 | `copy` 规格继承 | `copy` 继承 `shape/stride/format` | `test_copy_preserves_spec` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-011 | `cast` 基础转换 | `cast` 返回相同 `shape/stride/space`、新 `dtype` 的 `Memory` | `test_cast_changes_dtype` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-012 | `cast` 非法 dtype | 非法目标 `dtype` 触发 `TypeError` | `test_cast_invalid_dtype` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-013 | `cast` 不支持的转换 | 不支持的转换路径显式报错 | `test_cast_unsupported_conversion` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-014 | `view` 子视图基础语义 | `view` 返回 `shape == size` 的 `Memory` | `test_view_subview_returns_memory` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-015 | `view` 规格继承 | `view` 返回 `dtype/space/format/stride` 继承 `source` | `test_view_inherits_source_memoryspec` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-016 | `view` 边界校验 | `view` 在静态场景下对 `offset + (size - 1) * stride` 执行边界检查 | `test_view_bounds_check` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-017 | `flatten` 连续布局 | 连续布局下 `flatten` 返回一维 `shape` 与 `stride=[1]` | `test_flatten_contiguous` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-018 | `flatten` 非连续布局 | 非连续布局触发错误 | `test_flatten_non_contiguous_rejected` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-019 | `reshape` 基础变换 | `reshape` 返回新 `Memory` 且 `dtype/space/format` 继承 | `test_reshape_returns_memory` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-020 | `reshape` 连续布局 | 连续布局下 `reshape` 生成默认步幅 | `test_reshape_default_stride_contiguous` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-021 | `reshape` 非法参数 | 非法 `shape` 或非连续布局触发错误 | `test_reshape_invalid_shape_or_stride` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-022 | `cast` 空间覆盖 | `memoryspace` 覆盖结果 `space` | `test_cast_overrides_space` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-023 | `load` 空间类型错误 | `space` 类型不合法触发 `TypeError` | `test_load_invalid_space_type` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-024 | `load` sizes 正长度 | `sizes` 包含非正维度触发错误 | `test_dma_invalid_sizes` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-025 | `store/deslice` dtype mismatch | `source/target` dtype 不一致触发 `TypeError` | `test_store_dtype_mismatch` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-026 | `store` 基础写回 | 合法写回返回 `None` | `test_store_success` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-027 | `cast` 支持转换 | 支持同 dtype 或整数类型间转换 | `test_cast_supported_conversions` | `test/operation/test_operation_dma.py` |
| TC-OP-DMA-028 | `view` 非法参数 | `offset/size/stride` rank 不一致、负 offset 或非正 stride 显式报错 | `test_view_invalid_offset_size_stride` | `test/operation/test_operation_dma.py` |
