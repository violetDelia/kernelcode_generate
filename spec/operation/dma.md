# dma.md

## 功能简介

定义 `Memory` 的数据搬运、视图变换、切片写回、显式数据转换与生命周期操作规范，提供 `alloc/free/copy/load/store/slice/deslice/view/reshape/flatten/cast` 的输入约束、输出语义与错误边界。该层面向高层 API，负责搬运意图表达；方言层语义由 [`spec/dialect/dma.md`](../../spec/dialect/dma.md) 定义。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/operation/dma.md`](../../spec/operation/dma.md)
- `功能实现`：[`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py)
- `test`：[`test/operation/test_operation_dma.py`](../../test/operation/test_operation_dma.py)

## 依赖

- [`spec/dialect/dma.md`](../../spec/dialect/dma.md)：方言层搬运语义映射。
- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：`NnMemoryType` / `NnMemorySpaceAttr` 口径来源。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：`Memory` 结构与 `shape/stride/dtype/space` 语义。
- [`spec/symbol_variable/symbol_shape.md`](../../spec/symbol_variable/symbol_shape.md)：`SymbolShape` / 索引列表语义。
- [`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)：`NumericType` 定义。
- [`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py)：高层 API 实现。
- [`kernel_gen/symbol_variable/memory.py`](../../kernel_gen/symbol_variable/memory.py)：`Memory` 与 `MemorySpace` 实现。

## 目标

- 为 `Memory` 提供统一、稳定的数据搬运与显式 dtype 转换语义入口。
- 明确 `alloc/free/copy/load/store/slice/deslice/view/reshape/flatten/cast` 的输入约束、输出语义、空间规则与错误边界。
- 保留动态 `shape` 与 `offsets/sizes/strides` 的表达能力，支持后续 lowering 保留切片信息。
- 明确高层 `operation/dma` 与 `dialect/dma` 的分层关系与映射口径。

## 限制与边界

- 不负责真实 DMA 硬件调度、带宽估算、异步执行或同步原语（event/barrier/token/stream）。
- 不负责逐元素算术、比较、广播、归约等计算语义。
- 不负责隐式元素类型转换；元素表示变化必须通过显式 `cast` 描述。
- 不负责自动选择最优搬运空间、tile 大小或 stride。
- `alloc/free` 仅定义高层生命周期语义，不承担搬运语义。
- 搬运操作不改变元素值语义，只改变数据的逻辑位置、覆盖范围或所在空间。
- `view/reshape/flatten` 不做数据搬运，仅调整张量视图的 `shape/stride` 描述。
- 至少一侧操作数必须是 `Memory`；不定义纯标量间搬运接口。
- `offsets/sizes/strides` 长度必须与相关 `Memory.rank` 一致，`sizes` 中静态长度必须为正。
- 当前阶段 `strides` 仅支持全 1；非 1 stride 必须显式报错。
- 形状、类型、空间或索引规则不满足时必须报错，不允许 silently 降级。
- `alloc/free` 不要求存在 `dma dialect` op，但结果必须可无损映射为 `NnMemoryType` / `NnMemorySpaceAttr`。
- `copy/load/store/slice/deslice/cast` 映射到 `dma.copy/load/store/slice/deslice/cast`。
- `view/reshape/flatten` 为高层视图语义，不映射为 `dma dialect` op。
- `offsets/sizes/strides` 属于操作参数，不内嵌在返回 `Memory` 中。

## 公开接口

### alloc(shape, dtype, space=MemorySpace.GM, stride=None)

功能说明：

- 分配新的 `Memory` 描述对象，定义逻辑 `shape/dtype/space/stride`。

参数说明：

- `shape: Sequence | SymbolShape`：维度序列或 `SymbolShape`，用于定义结果 `Memory.shape`。
- `dtype: NumericType`：元素类型。
- `space: MemorySpace`：内存空间，默认 `MemorySpace.GM`。
- `stride: Sequence | SymbolShape | None`：可选步长序列。

使用示例：

```python
buf = alloc([32, 32], NumericType.Float32, space=MemorySpace.SM, stride=[1, 1])
```

注意事项：

- `shape/stride` 必须可被 `SymbolShape` 接受，且 rank 必须一致。
- `dtype` 必须为 `NumericType`，`space` 必须为 `MemorySpace`。

返回与限制：

- 返回新的 `Memory`。
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

返回与限制：

- 返回 `None`，不产生新的 `Memory`。

### copy(source, target)

功能说明：

- 整块拷贝，将 `source` 的全部内容搬运到 `target`。

参数说明：

- `source: Memory`：源内存。
- `target: Memory`：目标内存。

使用示例：

```python
copy(src, dst)
```

注意事项：

- `source.dtype == target.dtype`。
- `source.shape == target.shape`。
- `source.stride` 与 `target.stride` 必须一致，当前不支持布局转换拷贝。

返回与限制：

- 返回 `None`。

### load(source, offsets, sizes, strides=None, space=None)

功能说明：

- 从 `source` 读取切片块并返回新的结果块。

参数说明：

- `source: Memory`：源内存。
- `offsets: Sequence | SymbolShape`：索引列表或 `SymbolShape`。
- `sizes: Sequence | SymbolShape`：索引列表或 `SymbolShape`，作为返回块 `shape`。
- `strides: Sequence | SymbolShape | None`：可选步长序列；当前仅支持全 1。
- `space: MemorySpace | None`：目标空间；`None` 表示沿用 `source.space`。

使用示例：

```python
tile = load(src, offsets=[0, 0], sizes=[32, 32], strides=[1, 1], space=MemorySpace.SM)
```

注意事项：

- `offsets/sizes/strides` 长度必须与 `source.rank` 一致。
- `sizes` 中静态维度必须为正。
- `strides` 仅允许全 1，非 1 必须报错。

返回与限制：

- 返回新的 `Memory`，其 `shape == sizes`，`dtype` 继承 `source.dtype`。
- 返回结果的 `stride` 不承载切片 `strides`，由 `Memory` 默认规则决定。

### store(source, target, offsets, sizes, strides=None)

功能说明：

- 将 `source` 块写回 `target` 的指定区域。

参数说明：

- `source: Memory`：源块。
- `target: Memory`：目标内存。
- `offsets: Sequence | SymbolShape`：索引列表或 `SymbolShape`。
- `sizes: Sequence | SymbolShape`：索引列表或 `SymbolShape`，必须与 `source.shape` 一致。
- `strides: Sequence | SymbolShape | None`：可选步长序列；当前仅支持全 1。

使用示例：

```python
store(tile, dst, offsets=[0, 0], sizes=[32, 32])
```

注意事项：

- `source.dtype == target.dtype`。
- `offsets/sizes/strides` 长度必须与 `target.rank` 一致。
- `source.shape` 必须与 `sizes` 一致。
- `strides` 仅允许全 1，非 1 必须报错。

返回与限制：

- 返回 `None`。

### slice(source, offsets, sizes, strides=None, space=None)

功能说明：

- 从 `source` 抽取切片块；语义等价于 `load`，强调“切片”语义。

参数说明：

- `source: Memory`：源内存。
- `offsets: Sequence | SymbolShape`：索引列表或 `SymbolShape`。
- `sizes: Sequence | SymbolShape`：索引列表或 `SymbolShape`。
- `strides: Sequence | SymbolShape | None`：可选步长序列；当前仅支持全 1。
- `space: MemorySpace | None`：目标空间；`None` 表示沿用 `source.space`。

使用示例：

```python
sub = slice(src, offsets=[0, 16], sizes=[32, 32], space=MemorySpace.LM)
```

注意事项：

- 校验规则与 `load` 一致。

返回与限制：

- 返回新的 `Memory`；内部复用 `load` 的实现路径。

### deslice(source, target, offsets, sizes, strides=None)

功能说明：

- 将切片块写回 `target` 的指定区域；语义等价于 `store`，强调“局部区域更新”。

参数说明：

- `source: Memory`：源块。
- `target: Memory`：目标内存。
- `offsets: Sequence | SymbolShape`：索引列表或 `SymbolShape`。
- `sizes: Sequence | SymbolShape`：索引列表或 `SymbolShape`，必须与 `source.shape` 一致。
- `strides: Sequence | SymbolShape | None`：可选步长序列；当前仅支持全 1。

使用示例：

```python
deslice(sub, dst, offsets=[0, 16], sizes=[32, 32])
```

注意事项：

- 校验规则与 `store` 一致。

返回与限制：

- 返回 `None`；内部复用 `store` 的实现路径。

### view(source, shape, stride=None)

功能说明：

- 返回 `source` 的视图变换结果，仅调整 `shape/stride` 元信息。
- 不做数据搬运，不改变 `dtype/space/format`。

参数说明：

- `source: Memory`：源内存。
- `shape: Sequence | SymbolShape`：目标视图形状。
- `stride: Sequence | SymbolShape | None`：目标视图步幅；`None` 表示按连续行主序生成。

使用示例：

```python
src = Memory([2, 3, 4], NumericType.Float32)
dst = view(src, shape=[6, 4])
```

注意事项：

- `shape` 必须可被 `SymbolShape` 规范化。
- 若 `stride is None`，要求 `source` 为连续布局；默认 `stride` 按连续行主序生成。
- 若显式提供 `stride`，其长度必须与 `shape` 的 rank 一致。
- 若可判定，`shape` 的元素总数必须与 `source.shape` 一致；无法判定时由调用方保证。

返回与限制：

- 返回新的 `Memory`，其 `dtype/space/format` 继承 `source`。
- 返回的 `shape/stride` 由 `shape/stride` 或默认规则决定。

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
- 若可判定，`shape` 的元素总数必须与 `source.shape` 一致；无法判定时由调用方保证。

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

返回与限制：

- 返回新的 `Memory`，其 `shape` 为一维，`stride` 为 `[1]`。
- 返回结果的 `dtype/space/format` 继承 `source`。

### cast(source, dtype)

功能说明：

- 将 `source` 的元素表示显式转换为目标 `dtype`，并返回新的结果块。

参数说明：

- `source: Memory`：源块。
- `dtype: NumericType`：目标元素类型。

使用示例：

```python
src = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.SM, stride=[1, 1])
dst = cast(src, NumericType.Float16)
```

注意事项：

- `dtype` 必须为合法的元素类型。
- 当前仅支持同类数值类型间的显式转换。
- 不支持的转换路径必须显式报错。

返回与限制：

- 返回新的 `Memory`，其 `shape/stride/space` 继承 `source`。
- `dtype == source.dtype` 时允许作为显式 no-op cast。

## 测试

- 测试文件：[`test/operation/test_operation_dma.py`](../../test/operation/test_operation_dma.py)
- 执行命令：`pytest -q test/operation/test_operation_dma.py`

### 测试目标

- 验证 `alloc/free` 的输入约束与返回口径。
- 验证 `copy` 的形状/stride/dtype 约束。
- 验证 `load/slice` 的返回 `shape/dtype/space` 语义与索引校验。
- 验证 `store/deslice` 的源块大小约束与索引校验。
- 验证 `view` 的形状/步幅约束与连续布局要求。
- 验证 `reshape` 的形状约束与连续布局要求。
- 验证 `flatten` 的连续布局要求与结果形状。
- 验证 `cast` 的 `dtype` 变更与错误分支。
- 验证 stride 限制与类型错误分支。

### 功能与用例清单

| 用例 ID | 测试点 | 说明 | 建议测试 |
| --- | --- | --- | --- |
| TC-OP-DMA-AF-001 | `alloc` 基础分配 | 返回带指定 `shape/dtype/space` 的 `Memory` | `test_alloc_returns_memory` |
| TC-OP-DMA-AF-002 | `alloc` 显式 stride | 显式 `stride` 被正确保留到返回 `Memory` | `test_alloc_preserves_explicit_stride` |
| TC-OP-DMA-AF-003 | `alloc` 非法 shape/stride | 非法 `shape` 或 rank/stride 不一致时报错 | `test_alloc_invalid_shape_or_stride` |
| TC-OP-DMA-AF-004 | `free` 基础释放 | `free` 接受 `Memory` 并返回 `None` | `test_free_returns_none` |
| TC-OP-DMA-AF-005 | `free` 类型错误 | 非 `Memory` 输入触发 `TypeError` | `test_free_type_error` |
| TC-OP-DMA-AF-006 | `alloc` 类型错误 | `dtype/space` 类型不合法触发错误 | `test_alloc_invalid_dtype_or_space` |
| TC-OP-DMA-001 | `copy` 合法通过 | `source/target` 完全匹配时搬运语义成立 | `test_copy_success` |
| TC-OP-DMA-002 | `copy` 形状不匹配 | 整块搬运 `shape` mismatch 报错 | `test_copy_shape_mismatch` |
| TC-OP-DMA-010 | `copy` stride 不匹配 | 整块搬运 `stride` mismatch 报错 | `test_copy_stride_mismatch` |
| TC-OP-DMA-003 | `load` 结果空间 | `load` 返回结果块并切换到目标空间 | `test_load_result_space` |
| TC-OP-DMA-004 | `slice` 结果形状 | `slice` 返回块的 `shape` 等于 `sizes` | `test_slice_result_shape` |
| TC-OP-DMA-005 | `store` 大小校验 | `source.shape` 与写回大小不一致时报错 | `test_store_size_mismatch` |
| TC-OP-DMA-006 | `deslice` 大小校验 | `source.shape` 与回写区域大小不一致时报错 | `test_deslice_size_mismatch` |
| TC-OP-DMA-007 | 索引长度约束 | `offsets/sizes/strides` 长度与 rank 不一致时报错 | `test_dma_index_rank_mismatch` |
| TC-OP-DMA-008 | stride 限制 | 当前阶段非 1 stride 明确报错 | `test_dma_non_unit_stride_rejected` |
| TC-OP-DMA-009 | 类型错误 | 非 `Memory` 输入触发 `TypeError` | `test_dma_type_error` |
| TC-OP-DMA-011 | `cast` 基础转换 | `cast` 返回相同 `shape/stride/space`、新 `dtype` 的 `Memory` | `test_cast_changes_dtype` |
| TC-OP-DMA-012 | `cast` 非法 dtype | 非法目标 `dtype` 触发稳定报错 | `test_cast_invalid_dtype` |
| TC-OP-DMA-013 | `cast` 不支持的转换 | 当前实现不支持的转换路径显式报错 | `test_cast_unsupported_conversion` |
| TC-OP-DMA-014 | `view` 基础视图 | `view` 返回新 `Memory` 且 `dtype/space/format` 继承 | `test_view_returns_memory` |
| TC-OP-DMA-015 | `view` 默认步幅 | 未显式步幅且源为连续布局时生成默认步幅 | `test_view_default_stride_contiguous` |
| TC-OP-DMA-016 | `view` 非法参数 | 非法 `shape/stride` 或 rank 不一致报错 | `test_view_invalid_shape_or_stride` |
| TC-OP-DMA-017 | `flatten` 连续布局 | 连续布局下 `flatten` 返回一维 `shape` 与 `stride=[1]` | `test_flatten_contiguous` |
| TC-OP-DMA-018 | `flatten` 非连续布局 | 非连续布局触发错误 | `test_flatten_non_contiguous_rejected` |
| TC-OP-DMA-019 | `reshape` 基础变换 | `reshape` 返回新 `Memory` 且 `dtype/space/format` 继承 | `test_reshape_returns_memory` |
| TC-OP-DMA-020 | `reshape` 连续布局 | 连续布局下 `reshape` 生成默认步幅 | `test_reshape_default_stride_contiguous` |
| TC-OP-DMA-021 | `reshape` 非法参数 | 非法 `shape` 或非连续布局触发错误 | `test_reshape_invalid_shape_or_stride` |
| TC-OP-DMA-022 | `copy` dtype mismatch | `source/target` dtype 不一致触发错误 | `test_copy_dtype_mismatch` |
| TC-OP-DMA-023 | `load` 空间类型错误 | `space` 类型不合法触发 `TypeError` | `test_load_invalid_space_type` |
| TC-OP-DMA-024 | `load` sizes 正长度 | `sizes` 包含非正维度触发错误 | `test_dma_invalid_sizes` |
| TC-OP-DMA-025 | `store` dtype mismatch | `source/target` dtype 不一致触发错误 | `test_store_dtype_mismatch` |
| TC-OP-DMA-026 | `store` 基础写回 | 合法写回返回 `None` | `test_store_success` |
| TC-OP-DMA-027 | `cast` 支持转换 | 支持同 dtype 与整数类型间转换 | `test_cast_supported_conversions` |
