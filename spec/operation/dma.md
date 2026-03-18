# dma.md

用于定义 `Memory` 的数据搬运与生命周期操作规范。该层独立于具体前端语法，可被普通 Python 代码、语义构造层或其他上层接口直接复用；其职责对应高层 `dma` API，而 [`spec/dialect/dma.md`](../../spec/dialect/dma.md) 负责描述其中可进入方言层的搬运语义如何表达。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/operation/dma.md`](../../spec/operation/dma.md)
- `关联 Dialect`：[`spec/dialect/dma.md`](../../spec/dialect/dma.md)
- `关联类型`：[`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)
- `关联形状`：[`spec/symbol_variable/symbol_shape.md`](../../spec/symbol_variable/symbol_shape.md)
- `建议 test`：[`test/operation/test_operation_dma.py`](../../test/operation/test_operation_dma.py)
- `建议实现`：[`python/operation/dma.py`](../../python/operation/dma.py)

## 设计目标

- 为 `Memory` 提供统一、稳定的数据搬运与生命周期语义入口。
- 明确 `alloc/free/copy/load/store/slice/deslice` 的输入约束、输出语义、空间规则与错误规则。
- 保留动态 `shape` 与搬运参数 `offsets/sizes/strides` 信息，使搬运结果及其下游映射仍可表达动态张量。
- 明确高层 `alloc/free` 与现有搬运 API、`dma dialect`、`nn dialect` memory type/space 复用之间的分层关系。
- 让搬运层可被 AST、DSL、方言 lowering 或普通 Python 代码直接复用，而不把搬运规则散落在多个模块中。

## 非目标

- 不负责真实 DMA 硬件调度、流水线编排、带宽估算或异步执行。
- 不负责 event、barrier、token、stream 等同步模型。
- 不负责逐元素算术、比较、广播、归约等计算语义。
- 不负责自动选择最优搬运空间、最优 tile 大小或最优 stride。
- 不负责定义底层 runtime allocator、显存池或物理地址分配策略。

## 术语

- `Memory`：带 `shape`、`stride`、`dtype`、`space` 等元信息的张量式内存描述对象。
- 分配：创建一个可参与后续 `dma/nn` 操作的 `Memory` 描述对象，定义其逻辑 `shape/dtype/space/stride`，但不定义底层物理分配实现。
- 释放：结束某个 `Memory` 描述对象在高层 API 语义中的可用期；释放本身不搬运数据。
- 整块搬运：源对象与目标对象在整体范围内的完整拷贝。
- 切片搬运：带 `offsets/sizes/strides` 的局部区域读取或回写。
- 结果块：由读取或切片操作返回的新 `Memory` 描述对象。
- 目标块：由写回或拷贝操作写入的目标 `Memory` 描述对象。

## 设计原则

- 搬运层只定义“什么可以搬、怎么搬、何时报错”，不绑定具体前端语法。
- `alloc/free` 只定义高层生命周期语义：`alloc` 产出可复用的 `Memory` 描述对象，`free` 结束该对象的高层可用期；二者不承担搬运语义。
- 搬运操作不改变元素值语义，只改变数据的逻辑位置、覆盖范围或所在空间。
- 对搬运操作而言，至少一侧操作数必须具有 `Memory` 语义；本文不定义纯标量与纯标量之间的搬运接口。
- 动态维度、动态步幅和动态索引必须在前端语义层保留，不得提前折叠为静态常量。
- 高层 `operation/dma` 和低层 `dialect/dma` 必须语义一一对应：高层定义“搬运意图”，方言层定义“IR 表示与 verifier”。
- `alloc/free` 与 `copy/load/store/slice/deslice` 必须共享同一套 `Memory` / `MemorySpace` 语义，以保证后续可无损映射到 `nn dialect` 的 `NnMemoryType` / `NnMemorySpaceAttr`。
- 该层必须提供独立的 API 实现文件 `python/operation/dma.py` 与对应测试 `test/operation/test_operation_dma.py`。

## 与 `dialect/dma` 的关系

- `spec/operation/dma.md` 定义高层 API 语义，例如 `alloc`、`free`、`copy`、`load`、`store`、`slice`、`deslice`。
- `spec/dialect/dma.md` 定义其中搬运语义在 IR 中的 op 表示、类型约束和 verifier 规则。
- 两层的关系应与 [`spec/operation/nn.md`](../../spec/operation/nn.md) 和 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 保持一致：
  - `operation` 层面向用户与 DSL 语义
  - `dialect` 层面向 IR 表示与 verifier
- `operation/dma` 使用 `Memory` 作为输入输出语义对象；`dialect/dma` 在 IR 中复用 `nn dialect` 的 `NnMemoryType` / `NnMemorySpaceAttr`。
- 当前 `alloc/free` 先定义为高层生命周期 API，不要求已存在同名 `dma dialect` op；若后续需要进入 IR，仍必须复用 `nn dialect` 的 memory type / space 体系，而不是在 `dma dialect` 中另起一套类型系统。

## 支持的操作

### `alloc(shape, dtype, space=..., stride=None)`

功能说明：

- 表示分配一个新的 `Memory` 描述对象，供后续 `copy/load/store/slice/deslice` 或 `nn` 运算复用。
- 该 API 只定义逻辑 `shape/dtype/space/stride` 语义，不定义底层 allocator、物理地址或初始化策略。

示例：

```python
buf = alloc(shape=["M", "N"], dtype=NumericType.Float32, space=MemorySpace.SM, stride=[1, 1])
```

语义：

- 返回新的 `Memory` 结果对象。
- `buf.shape == ["M", "N"]`
- `buf.dtype == NumericType.Float32`
- `buf.space == MemorySpace.SM`
- `buf.stride == [1, 1]`；若 `stride is None`，则返回对象的 `Memory.stride` 由 `Memory` 默认规则决定
- `alloc` 不隐含数据搬运、初始化填充或跨空间拷贝

### `free(value)`

功能说明：

- 表示结束某个 `Memory` 描述对象的高层生命周期。
- 该 API 只定义“释放意图”，不要求立即绑定具体 runtime deallocation 行为。

示例：

```python
buf = alloc(shape=[32, 32], dtype=NumericType.Float32, space=MemorySpace.LM)
free(buf)
```

语义：

- `value` 必须为 `Memory`
- 成功释放建议返回 `None`
- `free` 本身不返回新的 `Memory`，也不表达任何搬运、写回或内容变换
- 已释放对象不应继续作为后续 `copy/load/store/slice/deslice/nn` API 的合法输入；若实现支持 use-after-free 检查，必须稳定报错

### `copy(source, target)`

功能说明：

- 表示整块拷贝，将 `source` 的全部内容搬运到 `target`。

示例：

```python
src = Memory(["M", "N"], NumericType.Float32)
dst = Memory(["M", "N"], NumericType.Float32)

copy(src, dst)
```

语义：

- `source.shape == target.shape`
- `source.dtype == target.dtype`
- `source.stride == target.stride`；当前 `copy` 只定义同布局整块搬运，不定义布局转换 copy
- `source.space` 与 `target.space` 可以相同，也可以不同

### `load(source, offsets, sizes, strides=None, space=...)`

功能说明：

- 表示从较大 `source` 中读取一块数据，并生成新的结果块。
- 常用于从 `global` 搬到 `shared/local` 的读搬运。

示例：

```python
src = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.GM)
tile = load(src, offsets=[0, 0], sizes=[32, 32], strides=[1, 1], space=MemorySpace.SM)
```

语义：

- `tile.shape == sizes`
- `tile.dtype == source.dtype`
- `tile.space == space`
- `strides` 表示切片步进，不等于 `Memory.stride`
- `tile.stride` 仅表示结果块的布局步幅；当前 API 不要求把切片 `strides` 写入返回 `Memory.stride`
- 若 `strides is None`，当前实现可按全 1 解释或补为全 1
- `offsets/sizes/strides` 由调用方保留，并在后续 lowering 或下游调用时继续传递

### `store(source, target, offsets, sizes, strides=None)`

功能说明：

- 表示把 `source` 块写回 `target` 的某个区域。

示例：

```python
tile = Memory([32, 32], NumericType.Float32, space=MemorySpace.SM)
dst = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.GM)

store(tile, dst, offsets=[0, 0], sizes=[32, 32], strides=[1, 1])
```

语义：

- `source.shape` 必须与写回切片的大小一致
- `source.dtype == target.dtype`
- 写回后目标对象的整体类型语义保持不变

### `slice(source, offsets, sizes, strides=None, space=...)`

功能说明：

- 表示从 `source` 中抽取一个切片块。
- 它是 `load` 的更明确切片版本，强调“源区域裁剪”语义。

示例：

```python
src = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.GM)
sub = slice(src, offsets=[0, 16], sizes=[32, 32], strides=[1, 1], space=MemorySpace.LM)
```

语义：

- `sub.shape == sizes`
- `sub.dtype == source.dtype`
- `sub.space == space`
- `strides` 表示切片步进，不等于 `Memory.stride`
- `sub.stride` 仅表示结果块的布局步幅；当前 API 不要求把切片 `strides` 写入返回 `Memory.stride`
- `offsets/sizes/strides` 由调用方保留，并在后续 lowering 或下游调用时继续传递

### `deslice(source, target, offsets, sizes, strides=None)`

功能说明：

- 表示把一个切片块写回到较大 `target` 的指定区域。
- 它是 `store` 的切片版本，强调“局部区域更新”语义。

示例：

```python
sub = Memory([32, 32], NumericType.Float32, space=MemorySpace.LM)
dst = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.GM)

deslice(sub, dst, offsets=[0, 16], sizes=[32, 32], strides=[1, 1])
```

语义：

- `source.shape` 必须与切片区域大小一致
- `source.dtype == target.dtype`
- 返回语义可为 `None` 或更新后的目标对象，但必须在实现与测试中保持一致

## 输入约束

### 生命周期 API

- `alloc` 的 `shape` 必须是可被 `Memory` / `SymbolShape` 语义接受的维度序列。
- `alloc` 的 `dtype` 必须是合法的元素类型。
- `alloc` 的 `space` 必须是合法的 `MemorySpace`；若未显式传入，则沿用 `Memory` 默认空间口径。
- `alloc` 的 `stride` 若显式传入，必须与 `shape` rank 一致，并满足 `Memory` 对布局步幅的基础约束。
- `free` 只接受 `Memory` 对象。

### Memory 与 Memory

- `copy`、`store`、`deslice` 至少需要 `source` 与 `target` 两个 `Memory` 对象。
- `source.dtype` 与 `target.dtype` 必须一致。
- `copy` 要求 `source.shape == target.shape`。
- `copy` 要求 `source.stride == target.stride`；当前版本不允许通过 `copy` 隐式完成布局转换。

### Memory 与索引列表

- `load`、`store`、`slice`、`deslice` 接收 `offsets/sizes/strides`。
- `offsets/sizes/strides` 应为可被 `SymbolShape` / `SymbolList` 语义接受的索引列表。
- 列表长度必须与相关 `Memory.rank` 一致。
- `sizes` 中每一维必须表示正长度。

### stride 规则

- `offsets/sizes/strides` 中的 `strides` 表示切片步进，不表示 `Memory` 的布局步幅。
- `Memory.stride` 只承载 `Memory` 自身的布局步幅；当前 `load/slice` API 返回的 `Memory.stride` 不承载切片 step。
- 若当前阶段实现不支持任意切片步进，则应统一要求 `strides` 为全 1。
- 若传入非 1 stride，必须抛出明确错误，而不是 silently 接受。

## 输出语义

### `alloc`

- 返回新的 `Memory` 结果对象。
- 返回对象必须可直接作为 `copy/load/store/slice/deslice` 的源或目标，也必须可无损映射到 `nn dialect` 的 `NnMemoryType`。
- `shape/dtype/space/stride` 由输入参数或 `Memory` 默认规则确定。
- `alloc` 不返回额外 token、event、handle 或 runtime pointer 语义对象。

### `free`

- 建议返回 `None`，表示 side-effect 风格的生命周期结束操作。
- 若未来实现需要返回显式释放状态，也必须先补充 spec 与测试，不得在无文档说明时改变返回类型。

### `copy`

- 建议返回 `None`，表示 side-effect 风格的整块搬运。
- 若实现选择函数式风格返回更新后的 `target`，则必须在测试和下游方言映射中保持一致。

### `load` / `slice`

- 返回新的 `Memory` 结果块。
- `shape` 由 `sizes` 决定。
- `dtype` 继承 `source.dtype`。
- `space` 为显式传入的目标空间。
- 返回结果的 `Memory.stride` 只表示布局步幅，不表示本次切片的 `strides`。
- 当前 API 只返回 `Memory`；`offsets/sizes/strides` 不内嵌在结果对象中，必须由调用方继续保留。

### `store` / `deslice`

- 建议返回 `None` 或更新后的目标对象。
- 返回风格必须在两者之间保持一致，不允许一个返回 `None`、另一个返回 `Memory` 而没有文档说明。

## 错误规则

- `alloc` 的 `shape` 非法或 rank/stride 不一致：抛 `ValueError`。
- `alloc` 的 `dtype` 非法：抛 `TypeError`。
- `alloc` 的 `space` 非法：抛 `ValueError` 或 `TypeError`，但实现中必须统一。
- `free` 传入非 `Memory`：抛 `TypeError`。
- 若实现显式跟踪生命周期，则对已释放对象重复 `free` 或 use-after-free 必须稳定报错；错误类型需在实现与测试中统一。
- 传入非 `Memory` 的源或目标对象：抛 `TypeError`。
- `dtype` 不一致：抛 `TypeError`。
- `copy` 的 `shape` 不一致：抛 `ValueError`。
- `offsets/sizes/strides` 长度与 rank 不一致：抛 `ValueError`。
- `sizes` 含非法长度：抛 `ValueError`。
- 当前实现不支持的 stride：抛 `NotImplementedError` 或 `ValueError`，但必须在实现中统一。
- 任何未实现的搬运能力必须显式报错，不允许 silently 降级。

## 与 `dialect/dma` 的映射

- `alloc(shape, dtype, space, stride)` -> 当前不要求存在直接 `dma dialect` op；lowering 可映射到运行时分配、外部 buffer 绑定或其他非 `dma` 方言载体，但结果 `Memory` 必须可无损映射为 `NnMemoryType`
- `free(value)` -> 当前不要求存在直接 `dma dialect` op；lowering 可映射到运行时释放或函数边界资源管理，但不得改变 `Memory` 的逻辑类型语义
- `copy(source, target)` -> `dma.copy`
- `load(source, offsets, sizes, strides, space)` -> `dma.load`
- `store(source, target, offsets, sizes, strides)` -> `dma.store`
- `slice(source, offsets, sizes, strides, space)` -> `dma.slice`
- `deslice(source, target, offsets, sizes, strides)` -> `dma.deslice`

补充约束：

- `alloc/free` 与搬运 API 共享同一套 `MemorySpace` 口径；例如 `alloc(..., space=MemorySpace.SM)` 产出的对象，进入 IR 时必须复用 `nn dialect` 的对应 `NnMemorySpaceAttr`。
- `operation/dma` 侧的 `Memory` 输入输出必须可无损映射到 `dialect/dma` 所需的 `NnMemoryType`。
- `space` 语义必须与 `dialect/dma` 和 `nn dialect` 中的 `NnMemorySpaceAttr` 对齐。
- `operation/dma` 中的切片 `offsets/sizes/strides` 属于操作参数；下游映射到 `dialect/dma` 时，必须由调用方显式保留并传给 `dma.load/store/slice/deslice`，不能从返回 `Memory.stride` 反推。

## 测试

- 建议测试文件：[`test/operation/test_operation_dma.py`](../../test/operation/test_operation_dma.py)
- 建议执行命令：`pytest -q test/operation/test_operation_dma.py`

### 测试目标

- 验证 `alloc` 返回的 `Memory` 结果可复用现有 `Memory` / `space` 语义。
- 验证 `free` 只接受 `Memory`，且返回口径稳定。
- 验证 `copy` 的整块搬运约束。
- 验证 `load/slice` 的结果 `shape/dtype/space` 语义。
- 验证 `store/deslice` 的源块与目标区域大小约束。
- 验证索引长度、stride 限制与类型错误分支。
- 验证高层搬运 API 与 `dialect/dma` 映射语义保持一致。

### 测试清单

| 用例 ID | 测试点 | 说明 | 建议测试 |
| --- | --- | --- | --- |
| TC-OP-DMA-AF-001 | `alloc` 基础分配 | 返回带指定 `shape/dtype/space` 的 `Memory` | `test_alloc_returns_memory` |
| TC-OP-DMA-AF-002 | `alloc` 显式 stride | 显式 `stride` 被正确保留到返回 `Memory` | `test_alloc_preserves_explicit_stride` |
| TC-OP-DMA-AF-003 | `alloc` 非法 shape/stride | 非法 `shape` 或 rank/stride 不一致时报错 | `test_alloc_invalid_shape_or_stride` |
| TC-OP-DMA-AF-004 | `free` 基础释放 | `free` 接受 `Memory` 并返回 `None` | `test_free_returns_none` |
| TC-OP-DMA-AF-005 | `free` 类型错误 | 非 `Memory` 输入触发 `TypeError` | `test_free_type_error` |
| TC-OP-DMA-001 | `copy` 合法通过 | `source/target` 完全匹配时搬运语义成立 | `test_copy_success` |
| TC-OP-DMA-002 | `copy` 形状不匹配 | 整块搬运 `shape` mismatch 报错 | `test_copy_shape_mismatch` |
| TC-OP-DMA-003 | `load` 结果空间 | `load` 返回结果块并切换到目标空间 | `test_load_result_space` |
| TC-OP-DMA-004 | `slice` 结果形状 | `slice` 返回块的 `shape` 等于 `sizes` | `test_slice_result_shape` |
| TC-OP-DMA-005 | `store` 大小校验 | `source.shape` 与写回大小不一致时报错 | `test_store_size_mismatch` |
| TC-OP-DMA-006 | `deslice` 大小校验 | `source.shape` 与回写区域大小不一致时报错 | `test_deslice_size_mismatch` |
| TC-OP-DMA-007 | 索引长度约束 | `offsets/sizes/strides` 长度与 rank 不一致时报错 | `test_dma_index_rank_mismatch` |
| TC-OP-DMA-008 | stride 限制 | 当前阶段非 1 stride 明确报错 | `test_dma_non_unit_stride_rejected` |
| TC-OP-DMA-009 | 类型错误 | 非 `Memory` 输入触发 `TypeError` | `test_dma_type_error` |

## 测试标准

- `pytest -q test/operation/test_operation_dma.py` 返回码必须为 `0`。
- `copy/load/store/slice/deslice` 的正向与关键反向路径必须被覆盖。
- 若新增 async、event、barrier 或多维 stride 支持，必须同步更新本文件与测试清单。

## 兼容性细节

- 当前文档优先覆盖“高层搬运 API”这一稳定语义，而不是绑定某个硬件 DMA 引擎。
- 当前版本新增 `alloc/free` 作为高层生命周期语义；它们与搬运 API 共用同一套 `Memory` / `MemorySpace` 口径，但不自动扩张为新的 `dma` 方言 op。
- 当前版本要求其下游 `dialect/dma` 复用 `nn dialect` 的 `NnMemoryType` / `NnMemorySpaceAttr`。
- 当前版本中，`Memory.stride` 与切片 `strides` 明确分离：前者是布局步幅，后者是搬运/切片步进。
- 若未来 `load/store` 最终只是 `slice/deslice` 的别名，也应在实现中保持接口、报错与映射口径一致，并在本 spec 中明确别名关系。
