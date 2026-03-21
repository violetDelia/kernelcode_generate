# dma.md

## 功能简介

用于定义 `dma dialect` 的稳定方言语义，描述 `dma.copy`、`dma.load`、`dma.store`、`dma.slice`、`dma.deslice`、`dma.cast` 如何表示内存对象之间的数据搬运与布局转换，包括整块搬运、切片读取、切片回写、跨空间迁移与显式数据转换。该方言不单独定义 memory type / memory space，而是统一复用 `nn dialect` 中的 `NnMemoryType` 与 `NnMemorySpaceAttr`。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/dialect/dma.md`](../../spec/dialect/dma.md)
- `test`：[`test/dialect/test_dma_dialect.py`](../../test/dialect/test_dma_dialect.py)
- `功能实现`：[`kernel_gen/dialect/dma.py`](../../kernel_gen/dialect/dma.py)

## 依赖

- [`kernel_gen/dialect/dma.py`](../../kernel_gen/dialect/dma.py)：`dma dialect` 的方言实现入口。
- [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)：提供 `NnMemoryType` 与 `NnMemorySpaceAttr`。
- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：定义被 `dma dialect` 复用的 memory type / memory space 语义。
- [`spec/operation/dma.md`](../../spec/operation/dma.md)：定义高层 `alloc/free/copy/load/store/slice/deslice/cast` API 的分层语义。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：说明高层 `Memory` 概念与 `shape/stride/dtype/space` 元信息来源。

## 目标

- 为项目提供统一的数据搬运、布局转换与显式数据转换方言层表示。
- 让整块拷贝、切片读取、切片回写、跨空间搬运与显式数据转换在 IR 中有明确 op 语义。
- 保留 `shape/stride/offsets/sizes/strides` 等搬运元信息，覆盖静态与动态场景。
- 为后续 lowering 到 `tensor.extract_slice`、`tensor.insert_slice`、`memref.copy`、后端 DMA 指令或 runtime API 提供稳定中间层。

## 限制与边界

- `dma dialect` 不单独维护 memory type / memory space，所有相关 operand / result 类型统一复用 `NnMemoryType` 与 `NnMemorySpaceAttr`。
- 本文件只定义方言层的数据搬运、布局转换与显式数据转换语义，不负责真实 DMA 硬件调度、流水线编排、带宽建模、同步原语、事件、barrier 或 async token 设计。
- 本文件不负责广播、逐元素算术、比较等张量计算语义，也不负责自动求解 `offsets/sizes/strides` 或自动推导最优搬运策略。
- 当前方言范围仅包含 `dma.copy`、`dma.load`、`dma.store`、`dma.slice`、`dma.deslice`、`dma.cast`；`operation/dma.alloc` 与 `operation/dma.free` 不属于本方言公开 op。
- 除 `dma.cast` 外，其他搬运 op 不改变元素值语义，只改变数据所在的逻辑位置、切片范围、布局表达或空间；同一个 op 不应同时承担计算和搬运语义。
- 本文件中的“转换”包含两类：布局、切片视图或空间层面的转换，以及通过 `dma.cast` 表达的显式元素类型转换；不包括广播、归约或通用数值计算。

### 分层约束

- `spec/operation/dma.md` 负责高层 API 语义；`dma dialect` 负责对应 IR 语义。
- 若高层 `Memory` 进入 IR，仍必须落到 `NnMemoryType` / `NnMemorySpaceAttr`，不得在 `dma dialect` 内再定义一套分配专用类型。

### 通用约束

- 所有参与搬运或转换的 `source`、`target`、`result` 必须是 `!nn.memory<...>`。
- 对 `dma.copy/load/store/slice/deslice`，相关 `element_type` 必须一致，不允许隐式类型转换。
- 对 `dma.cast`，只允许 `element_type` 发生显式变化；`shape/stride/space` 必须保持一致。
- `shape/stride` 的 rank 必须与相关 `offsets/sizes/strides` 列表长度一致。
- `offsets`、`sizes`、`strides` 应表示为长度与 rank 一致的索引列表。
- `offsets/sizes` 当前仅支持 attribute 索引表达，即 `IntAttr` 或 `StringAttr`；暂不支持 SSA 动态 index。
- `strides` 当前每一维必须是 `IntAttr(1)`，暂不支持 `StringAttr` 或 SSA 动态 index。
- `sizes` 中每一维必须具有正整数语义，不允许负值。
- 若 op 带有目标空间 attribute，则其值必须与结果 type 或目标 type 的 `space` 一致。

### Parse/Print 与 Verifier 约束

- 任意被 `dma` op 引用的 `!nn.memory<...>` 与 `#nn.space<...>` 文本都必须支持 parse 后再 print 回稳定文本。
- 任意合法 `dma.copy/load/store/slice/deslice/cast` 文本都必须支持 parse 后进入 verifier。
- assembly 缺失必要字段时，必须在 parse 阶段失败。
- `NnMemorySpaceAttr` 非法值、`NnMemoryType.shape` 与 `stride` rank 不一致等类型错误，必须按 `nn dialect` 规则报错。
- `dma.copy` 中 `source/target` 的 `shape/stride/element_type` 不一致必须报错。
- `dma.load/slice` 中 `offsets/sizes/strides` 长度与输入 rank 不一致必须报错。
- `dma.store/deslice` 中 `source.shape` 与切片目标大小不一致必须报错。
- `dma.cast` 中 `source/result` 的 `shape/stride/space` 不一致必须报错。
- `strides` 仅允许 `IntAttr(1)`；若当前实现限制 stride 为 1，则 `stride != 1` 的切片搬运必须显式报错，不得 silently 接受。

## 公开接口

### 方言公开构件

功能说明：

- `dma dialect` 的公开构件由两部分组成：
  - 复用 `nn dialect` 的 `NnMemoryType` 与 `NnMemorySpaceAttr`
  - 提供 `dma.copy`、`dma.load`、`dma.store`、`dma.slice`、`dma.deslice`、`dma.cast` 六个公开 op

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.dialect.dma import DmaCastOp, DmaCopyOp, DmaDesliceOp, DmaLoadOp, DmaSliceOp, DmaStoreOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr
```

注意事项：

- `dma dialect` 不提供 `alloc/free` 生命周期 op。
- memory type / memory space 必须始终沿用 `nn dialect` 口径。

返回与限制：

- 对外暴露五个搬运 op、一个显式数据转换 op，以及对 `nn dialect` memory 类型体系的复用约束。

### `dma.copy`

功能说明：

- 表示整块拷贝，将 `source` 的全部内容搬运到 `target`。
- 用于表达不涉及切片的完整搬运。

参数说明：

- `source`：源内存，类型为 `!nn.memory<...>`。
- `target`：目标内存，类型为 `!nn.memory<...>`。

使用示例：

```python
op = DmaCopyOp(source, target)
```

注意事项：

- `source.shape`、`target.shape` 必须一致。
- `source.stride`、`target.stride` 必须一致。
- `source.element_type`、`target.element_type` 必须一致。
- `source.space` 与 `target.space` 可以相同，也可以不同；不同空间表示显式跨空间搬运。

返回与限制：

- 返回类型为无返回值；当前 op result 数量固定为 `0`。
- 语义上通过 side effect 表达对 `target` 的整块写入，不返回新的 `!nn.memory<...>`。

### `dma.load`

功能说明：

- 表示从较大 `source` 中读取一块数据，并生成新的结果块。
- 常用于从 `global` 搬到 `shared` 或 `local` 的读搬运。

参数说明：

- `source`：源内存，类型为 `!nn.memory<...>`。
- `offsets`：切片起始索引列表，类型为 `ArrayAttr[IntAttr|StringAttr]`，长度必须与 `source.rank` 一致；每一维表示对应维度的起始索引。
- `sizes`：切片大小列表，类型为 `ArrayAttr[IntAttr|StringAttr]`，长度必须与 `source.rank` 一致；每一维表示对应维度的切片大小。
- `strides`：切片步长列表，类型为 `ArrayAttr[IntAttr]`，长度必须与 `source.rank` 一致；每一维表示对应维度的切片步长，当前每一维必须为 `IntAttr(1)`。
- `space`：结果空间，使用 `NnMemorySpaceAttr` 表示。
- `result_type`：结果类型，必须为 `!nn.memory<...>`。

使用示例：

```python
op = DmaLoadOp(
    source,
    offsets,
    sizes,
    strides,
    result_type,
    NnMemorySpaceAttr.from_name("shared"),
)
```

注意事项：

- `result.shape` 由 `sizes` 决定。
- `result.space` 必须与 op `space` 一致。
- `result.element_type` 必须与 `source.element_type` 一致。

返回与限制：

- 返回新的 `!nn.memory<...>` 结果块。
- 当前不支持 SSA 动态 index，也不支持非 1 stride。

### `dma.store`

功能说明：

- 表示把 `source` 块写回 `target` 的某个区域。
- 常用于从 `shared` 或 `local` 写回 `global`。

参数说明：

- `source`：待写回的源块，类型为 `!nn.memory<...>`。
- `target`：被更新的目标内存，类型为 `!nn.memory<...>`。
- `offsets`：目标切片起始索引列表，类型为 `ArrayAttr[IntAttr|StringAttr]`；每一维表示 `target` 对应维度的写回起始索引，长度必须与 `target.rank` 一致。
- `sizes`：目标切片大小列表，类型为 `ArrayAttr[IntAttr|StringAttr]`；每一维表示写回区域在 `target` 对应维度的大小，长度必须与 `target.rank` 一致。
- `strides`：目标切片步长列表，类型为 `ArrayAttr[IntAttr]`；每一维表示 `target` 对应维度的写回步长，长度必须与 `target.rank` 一致，当前每一维必须为 `IntAttr(1)`。

使用示例：

```python
op = DmaStoreOp(source, target, offsets, sizes, strides)
```

注意事项：

- `source.shape` 必须与 `sizes` 对应的切片形状一致。
- `source.element_type` 必须与 `target.element_type` 一致。
- `offsets/sizes/strides` 长度必须与 `target.rank` 一致。

返回与限制：

- 返回类型为无返回值；当前 op result 数量固定为 `0`。
- 语义上通过 side effect 表达对 `target` 指定切片区域的写回，不返回新的 `!nn.memory<...>`。

### `dma.slice`

功能说明：

- 表示从 `source` 中抽取一个切片块，语义上接近切片读取。
- 它与 `dma.load` 一样返回新结果块，但更强调源区域裁剪而非整块空间搬运。

参数说明：

- `source`：源内存，类型为 `!nn.memory<...>`。
- `offsets`：切片起始索引列表，类型为 `ArrayAttr[IntAttr|StringAttr]`；每一维表示对应维度的起始索引，长度必须与 `source.rank` 一致。
- `sizes`：切片大小列表，类型为 `ArrayAttr[IntAttr|StringAttr]`；每一维表示对应维度的切片大小，长度必须与 `source.rank` 一致。
- `strides`：切片步长列表，类型为 `ArrayAttr[IntAttr]`；每一维表示对应维度的切片步长，长度必须与 `source.rank` 一致，当前每一维必须为 `IntAttr(1)`。
- `space`：切片结果所在空间，使用 `NnMemorySpaceAttr` 表示。
- `result_type`：结果类型，必须为 `!nn.memory<...>`。

使用示例：

```python
op = DmaSliceOp(
    source,
    offsets,
    sizes,
    strides,
    result_type,
    NnMemorySpaceAttr.from_name("local"),
)
```

注意事项：

- `result.shape` 由 `sizes` 决定。
- `result.element_type` 必须与 `source.element_type` 一致。
- 当前阶段必须限制 `strides` 为全 1；出现其他值时 verifier 必须报错。

返回与限制：

- 返回新的 `!nn.memory<...>` 切片结果。
- 可 lowering 到 `tensor.extract_slice`、`memref.subview` 或等价目标。

### `dma.deslice`

功能说明：

- 表示把一个切片块写回到较大 `target` 的指定区域，语义上接近切片回写。
- 它与 `dma.store` 一样负责目标区域更新，但更强调按切片语义回写。

参数说明：

- `source`：待回写的切片块，类型为 `!nn.memory<...>`。
- `target`：被更新的较大目标内存，类型为 `!nn.memory<...>`。
- `offsets`：目标区域起始索引列表，类型为 `ArrayAttr[IntAttr|StringAttr]`；每一维表示 `target` 对应维度的回写起始索引，长度必须与 `target.rank` 一致。
- `sizes`：目标区域大小列表，类型为 `ArrayAttr[IntAttr|StringAttr]`；每一维表示回写区域在 `target` 对应维度的大小，长度必须与 `target.rank` 一致。
- `strides`：目标区域步长列表，类型为 `ArrayAttr[IntAttr]`；每一维表示 `target` 对应维度的回写步长，长度必须与 `target.rank` 一致，当前每一维必须为 `IntAttr(1)`。
- `result_type`：结果类型，必须为 `!nn.memory<...>`，且必须与 `target` 类型一致。

使用示例：

```python
op = DmaDesliceOp(source, target, offsets, sizes, strides, result_type)
```

注意事项：

- `source.shape` 必须与 `sizes` 对应的切片形状一致。
- `source.element_type` 必须与 `target.element_type` 一致。
- 当前阶段必须限制 `strides` 为全 1；出现其他值时 verifier 必须报错。

返回与限制：

- 返回类型为 `!nn.memory<...>`；当前 op result 数量固定为 `1`。
- 返回值语义为“回写完成后的目标内存”，其类型必须与 `target` 完全一致。
- 可 lowering 到 `tensor.insert_slice`、`memref.copy` 或等价目标。

### `dma.cast`

功能说明：

- 表示把 `source` 的元素表示显式转换为目标元素类型，并返回新的结果块。
- 该 op 只负责数据表示转换，不负责切片、搬运调度或逐元素算术。

参数说明：

- `source`：待转换的源内存，类型为 `!nn.memory<...>`。
- `result_type`：结果类型，必须为 `!nn.memory<...>`。

使用示例：

```python
op = DmaCastOp(source, result_type)
```

注意事项：

- `result.shape` 必须与 `source.shape` 一致。
- `result.stride` 必须与 `source.stride` 一致。
- `result.space` 必须与 `source.space` 一致。
- `result.element_type` 表示目标元素类型，可以与 `source.element_type` 不同。
- 若 `result.element_type` 与 `source.element_type` 相同，该 op 语义上允许作为显式 no-op cast，但实现可在后续阶段进行消解。

返回与限制：

- 返回新的 `!nn.memory<...>` 结果块；当前 op result 数量固定为 `1`。
- 当前 op 只定义显式元素类型转换，不定义量化参数、缩放因子、舍入模式或饱和策略；如需这些能力，必须由后续 spec 单独扩展。

## 测试

- 测试文件：[`test/dialect/test_dma_dialect.py`](../../test/dialect/test_dma_dialect.py)
- 执行命令：`pytest -q test/dialect/test_dma_dialect.py`

### 测试目标

- 验证 `dma` op 复用 `NnMemorySpaceAttr` / `NnMemoryType` 时，与 `nn dialect` 的类型规则保持一致。
- 验证 `dma.copy` 的整块搬运约束。
- 验证 `dma.load/slice` 的结果形状、目标空间与索引长度约束。
- 验证 `dma.store/deslice` 的源块与目标切片大小匹配约束。
- 验证 `dma.cast` 只允许改变元素类型，且保持 `shape/stride/space` 不变。
- 验证当前阶段对 stride 的限制会在 verifier 阶段明确报错。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DMA-001 | 类型复用 | `dma` op 类型边界 | 已提供 `NnMemoryType` 与非 `NnMemoryType` 候选类型 | 构造 `dma` op | 仅 `NnMemoryType` 合法 | `test_dma_requires_nn_memory_type` |
| TC-DMA-002 | 整块拷贝 | `dma.copy` 合法路径 | `source/target` 的 `shape/stride/element_type` 完全一致 | 构造并校验 `dma.copy` | verifier 通过 | `test_dma_copy_verify_success` |
| TC-DMA-003 | 整块拷贝 | `dma.copy` 形状不匹配 | `source.shape != target.shape` | 构造并校验 `dma.copy` | verifier 报错 | `test_dma_copy_shape_mismatch` |
| TC-DMA-004 | 切片读取 | `dma.load` 结果空间约束 | `result.space` 与 op `space` 不一致 | 构造并校验 `dma.load` | verifier 报错 | `test_dma_load_result_space_mismatch` |
| TC-DMA-005 | 切片读取 | `dma.slice` 索引长度约束 | `offsets/sizes/strides` 长度与 rank 不一致 | 构造并校验 `dma.slice` | verifier 报错 | `test_dma_slice_rank_mismatch` |
| TC-DMA-006 | 切片读取 | `dma.slice` stride 限制 | `strides` 包含非 `IntAttr(1)` | 构造并校验 `dma.slice` | verifier 报错 | `test_dma_slice_non_unit_stride_rejected` |
| TC-DMA-007 | 切片回写 | `dma.store` 块大小约束 | `source.shape` 与目标切片大小不一致 | 构造并校验 `dma.store` | verifier 报错 | `test_dma_store_size_mismatch` |
| TC-DMA-008 | 切片回写 | `dma.deslice` 合法路径 | `source.shape` 与目标切片大小一致 | 构造并校验 `dma.deslice` | verifier 通过 | `test_dma_deslice_verify_success` |
| TC-DMA-009 | 类型校验 | `nn dialect` verifier 透传 | `space` 非法或 `shape/stride` rank 不一致 | 构造引用非法 `!nn.memory<...>` 的 `dma` op | 按 `nn dialect` 规则报错 | `test_dma_nn_memory_type_verifier_passthrough` |
| TC-DMA-010 | 索引表达 | `StringAttr` 合法路径 | `offsets/sizes` 使用 `StringAttr`，`strides` 为 `IntAttr(1)` | 构造并校验切片类 op | verifier 通过 | `test_dma_index_string_attr_valid` |
| TC-DMA-011 | 数据转换 | `dma.cast` 合法路径 | `source/result` 的 `shape/stride/space` 一致，仅元素类型不同 | 构造并校验 `dma.cast` | verifier 通过 | `test_dma_cast_verify_success` |
| TC-DMA-012 | 数据转换 | `dma.cast` 结果约束 | `source/result` 的 `shape` 或 `stride` 或 `space` 不一致 | 构造并校验 `dma.cast` | verifier 报错 | `test_dma_cast_layout_or_space_mismatch` |
