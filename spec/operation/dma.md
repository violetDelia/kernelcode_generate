# dma.md

用于定义 `Memory` 的数据搬运操作规范。该层独立于具体前端语法，可被普通 Python 代码、语义构造层或其他上层接口直接复用；其职责对应高层搬运 API，而 [`spec/dialect/dma.md`](../../spec/dialect/dma.md) 负责描述这些语义在方言层如何表达。

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

- 为 `Memory` 提供统一、稳定的数据搬运语义入口。
- 明确搬运类操作的输入约束、输出语义、空间规则与错误规则。
- 保留动态 `shape` 与搬运参数 `offsets/sizes/strides` 信息，使搬运结果及其下游映射仍可表达动态张量。
- 让搬运层可被 AST、DSL、方言 lowering 或普通 Python 代码直接复用，而不把搬运规则散落在多个模块中。

## 非目标

- 不负责真实 DMA 硬件调度、流水线编排、带宽估算或异步执行。
- 不负责 event、barrier、token、stream 等同步模型。
- 不负责逐元素算术、比较、广播、归约等计算语义。
- 不负责自动选择最优搬运空间、最优 tile 大小或最优 stride。

## 术语

- `Memory`：带 `shape`、`stride`、`dtype`、`space` 等元信息的张量式内存描述对象。
- 整块搬运：源对象与目标对象在整体范围内的完整拷贝。
- 切片搬运：带 `offsets/sizes/strides` 的局部区域读取或回写。
- 结果块：由读取或切片操作返回的新 `Memory` 描述对象。
- 目标块：由写回或拷贝操作写入的目标 `Memory` 描述对象。

## 设计原则

- 搬运层只定义“什么可以搬、怎么搬、何时报错”，不绑定具体前端语法。
- 搬运操作不改变元素值语义，只改变数据的逻辑位置、覆盖范围或所在空间。
- 对搬运操作而言，至少一侧操作数必须具有 `Memory` 语义；本文不定义纯标量与纯标量之间的搬运接口。
- 动态维度、动态步幅和动态索引必须在前端语义层保留，不得提前折叠为静态常量。
- 高层 `operation/dma` 和低层 `dialect/dma` 必须语义一一对应：高层定义“搬运意图”，方言层定义“IR 表示与 verifier”。
- 该层必须提供独立的 API 实现文件 `python/operation/dma.py` 与对应测试 `test/operation/test_operation_dma.py`。

## 与 `dialect/dma` 的关系

- `spec/operation/dma.md` 定义高层 API 语义，例如 `copy`、`load`、`store`、`slice`、`deslice`。
- `spec/dialect/dma.md` 定义这些语义在 IR 中的 op 表示、类型约束和 verifier 规则。
- 两层的关系应与 [`spec/operation/nn.md`](../../spec/operation/nn.md) 和 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 保持一致：
  - `operation` 层面向用户与 DSL 语义
  - `dialect` 层面向 IR 表示与 verifier
- `operation/dma` 使用 `Memory` 作为输入输出语义对象；`dialect/dma` 在 IR 中复用 `nn dialect` 的 `NnMemoryType` / `NnMemorySpaceAttr`。

## 支持的操作

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
- `source.stride == target.stride`
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

### Memory 与 Memory

- `copy`、`store`、`deslice` 至少需要 `source` 与 `target` 两个 `Memory` 对象。
- `source.dtype` 与 `target.dtype` 必须一致。
- `copy` 要求 `source.shape == target.shape`。
- `copy` 建议要求 `source.stride == target.stride`；若后续允许布局转换，必须在 spec 中额外说明。

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

- 传入非 `Memory` 的源或目标对象：抛 `TypeError`。
- `dtype` 不一致：抛 `TypeError`。
- `copy` 的 `shape` 不一致：抛 `ValueError`。
- `offsets/sizes/strides` 长度与 rank 不一致：抛 `ValueError`。
- `sizes` 含非法长度：抛 `ValueError`。
- 当前实现不支持的 stride：抛 `NotImplementedError` 或 `ValueError`，但必须在实现中统一。
- 任何未实现的搬运能力必须显式报错，不允许 silently 降级。

## 与 `dialect/dma` 的映射

- `copy(source, target)` -> `dma.copy`
- `load(source, offsets, sizes, strides, space)` -> `dma.load`
- `store(source, target, offsets, sizes, strides)` -> `dma.store`
- `slice(source, offsets, sizes, strides, space)` -> `dma.slice`
- `deslice(source, target, offsets, sizes, strides)` -> `dma.deslice`

补充约束：

- `operation/dma` 侧的 `Memory` 输入输出必须可无损映射到 `dialect/dma` 所需的 `NnMemoryType`。
- `space` 语义必须与 `dialect/dma` 和 `nn dialect` 中的 `NnMemorySpaceAttr` 对齐。
- `operation/dma` 中的切片 `offsets/sizes/strides` 属于操作参数；下游映射到 `dialect/dma` 时，必须由调用方显式保留并传给 `dma.load/store/slice/deslice`，不能从返回 `Memory.stride` 反推。

## 测试

- 建议测试文件：[`test/operation/test_operation_dma.py`](../../test/operation/test_operation_dma.py)
- 建议执行命令：`pytest -q test/operation/test_operation_dma.py`

### 测试目标

- 验证 `copy` 的整块搬运约束。
- 验证 `load/slice` 的结果 `shape/dtype/space` 语义。
- 验证 `store/deslice` 的源块与目标区域大小约束。
- 验证索引长度、stride 限制与类型错误分支。
- 验证高层搬运 API 与 `dialect/dma` 映射语义保持一致。

### 测试清单

| 用例 ID | 测试点 | 说明 | 建议测试 |
| --- | --- | --- | --- |
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
- 当前版本要求其下游 `dialect/dma` 复用 `nn dialect` 的 `NnMemoryType` / `NnMemorySpaceAttr`。
- 当前版本中，`Memory.stride` 与切片 `strides` 明确分离：前者是布局步幅，后者是搬运/切片步进。
- 若未来 `load/store` 最终只是 `slice/deslice` 的别名，也应在实现中保持接口、报错与映射口径一致，并在本 spec 中明确别名关系。
