# dma.md

聚焦 `dma dialect` 的设计语义，说明该方言如何表达数据搬运、切片读取、切片回写与空间迁移。本文档只描述方言层的稳定接口、类型约束、verifier 规则与测试清单，不包含过程性迁移描述。`dma dialect` 不单独定义 memory type / memory space，而是沿用 `nn dialect` 中已经定义好的相关类型。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/dialect/dma.md`](../../spec/dialect/dma.md)
- `关联 Dialect`：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- `关联类型`：[`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)
- `关联形状`：[`spec/symbol_variable/symbol_shape.md`](../../spec/symbol_variable/symbol_shape.md)
- `建议测试`：[`test/dialect/test_dma_dialect.py`](../../test/dialect/test_dma_dialect.py)
- `建议实现`：[`python/dialect/dma.py`](../../python/dialect/dma.py)

## 范围与目标

- 为项目提供统一的“数据搬运”方言层表示。
- 让“整块拷贝”“切片读取”“切片回写”“跨空间搬运”在 IR 中有明确的 op 语义。
- 保留动态 `shape/stride/offset/size` 信息，使搬运操作可表达静态与动态场景。
- 为后续 lowering 到 `tensor.extract_slice`、`tensor.insert_slice`、`memref.copy`、DMA 指令或后端 runtime API 提供稳定中间层。

## 非目标

- 不负责真实 DMA 硬件调度、流水线编排或带宽建模。
- 不负责同步原语、事件、barrier、async token 的完整设计。
- 不负责广播、逐元素算术、比较等张量计算语义。
- 不负责自动求解 offsets/sizes/strides，也不负责自动推导最优搬运策略。

## 设计背景

- 当前项目已有 `Memory` 类型与 `MemorySpace` 概念，可表达张量形状、步幅、元素类型与空间。
- `cpp_gen` 中 `operation/dma` 公开了 `slice/deslice` 一类搬运语义，并在底层映射到 `tensor.extract_slice` / `tensor.insert_slice`。
- 该参考说明“切片读取”和“切片回写”是数据搬运的核心子问题，但本方言不直接绑定某个底层标准方言 op，而是在方言层先保留更稳定的搬运语义。

## 核心组成

`dma dialect` 建议由以下公开构件组成：

- 复用 `nn dialect` 中的：
  - `NnMemorySpaceAttr`
  - `NnMemoryType`
- 数据搬运 op：
  - `dma.copy`
  - `dma.load`
  - `dma.store`
  - `dma.slice`
  - `dma.deslice`

当前不纳入 `dma dialect` 范围的高层 API：

- `operation/dma.alloc`
- `operation/dma.free`

## 类型复用约束

- `dma dialect` 不单独维护一套 memory type 与 memory space。
- 所有 `dma` op 的 operand / result 类型统一复用 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 中定义的：
  - `NnMemorySpaceAttr`
  - `NnMemoryType`
- 因此：
  - `space` 的合法取值、parse/print 与 verifier 规则以 `nn dialect` 为准。
  - `shape/stride/element_type/space` 四元组的结构语义以 `nn dialect` 为准。
- `dma dialect` 只在此基础上增加“搬运”这一类操作语义，不重复定义类型系统。
- 因此高层 `operation/dma.alloc` 产出的 `Memory`，若后续进入 IR，也必须继续复用 `NnMemoryType` / `NnMemorySpaceAttr`，而不是要求 `dma dialect` 重新定义一套分配专用类型。

## 与 `operation/dma` 的分层关系

- `spec/operation/dma.md` 负责高层 `alloc/free/copy/load/store/slice/deslice` API 语义。
- `dma dialect` 当前只承载“搬运”相关 IR 语义，即 `copy/load/store/slice/deslice`。
- `alloc/free` 当前作为高层生命周期语义存在，不要求已有同名 `dma` op；若未来需要进入 IR，仍必须遵守本文件的类型复用约束，并与 `nn dialect` 的 memory type / memory space 口径保持一致。

## 搬运语义原则

- `dma dialect` 只表达“数据从哪里来、到哪里去、搬运哪一块、结果是什么”。
- 搬运操作不改变元素值语义，只改变数据所在的逻辑位置、切片范围或空间。
- `shape/stride/offset/size` 是搬运语义的一部分，不能在前端阶段丢失。
- 同一个 op 不应同时承担计算和搬运语义；例如 `dma.copy` 不做逐元素算术。

## Op 共性约束

### 类型共性

- 参与搬运的 `source` 与 `target/result` 必须是 `NnMemoryType`。
- `element_type` 必须一致，不允许隐式类型转换。
- `shape/stride` 的 rank 必须与相关 index 列表长度一致。

### 索引参数共性

- `offsets`、`sizes`、`strides` 应表示为长度与 rank 一致的索引列表。
- `offsets/sizes` 当前仅支持 attribute 索引表达（`IntAttr`/`StringAttr`），暂不支持 SSA 动态 index。
- `strides` 当前每一维必须是 `IntAttr(1)`，暂不支持 `StringAttr` 或 SSA 动态 index。
- `sizes` 中每一维必须是正整数语义，不允许负值。

### 空间共性

- 搬运 op 必须显式体现数据搬入或搬出的空间语义。
- 若 op 带有目标空间 attribute，则其值必须与结果 type 或目标 type 的 `space` 一致。

## Op 定义

### `dma.copy`

功能说明：

- 表示整块拷贝，将 `source` 的全部内容搬运到 `target`。
- 用于表达不涉及切片的完整搬运。

输入：

- `source: !nn.memory<...>`
- `target: !nn.memory<...>`

输出：

- 建议无显式结果，由 side effect 语义描述对 `target` 的写入。
- 若实现偏向函数式 IR，也可返回更新后的 `target`，但需在实现与测试中保持一致。

约束：

- `source.shape == target.shape`
- `source.stride == target.stride`
- `source.element_type == target.element_type`
- `source.space` 与 `target.space` 可以相同，也可以不同；若不同，则表示显式跨空间搬运。

使用示例：

```python
op = DmaCopyOp(source, target)
```

### `dma.load`

功能说明：

- 表示从较大 `source` 中读取一块数据，并生成新的结果块。
- 常用于从 `global` 搬到 `shared/local` 的读搬运。

输入：

- `source: !nn.memory<...>`
- `offsets`
- `sizes`
- `strides`
- `space` 使用 `NnMemorySpaceAttr`，表示结果空间

输出：

- `result: !nn.memory<...>`

约束：

- `result.shape` 由 `sizes` 决定
- `result.space == op.space`
- `result.element_type == source.element_type`
- `offsets/sizes/strides` 长度与 `source.rank` 一致

使用示例：

```python
op = DmaLoadOp(source, offsets, sizes, strides, result_type, NnMemorySpaceAttr.from_name("shared"))
```

### `dma.store`

功能说明：

- 表示把 `source` 块写回 `target` 的某个区域。
- 常用于从 `shared/local` 写回 `global`。

输入：

- `source: !nn.memory<...>`
- `target: !nn.memory<...>`
- `offsets`
- `sizes`
- `strides`

输出：

- 建议无显式结果，由 side effect 语义描述对 `target` 的写入。
- 若实现选择函数式更新，则应返回更新后的 `target`，并与 `dma.copy`/`dma.deslice` 保持一致口径。

约束：

- `source.shape` 必须与 `sizes` 对应的切片形状一致
- `source.element_type == target.element_type`
- `offsets/sizes/strides` 长度与 `target.rank` 一致

使用示例：

```python
op = DmaStoreOp(source, target, offsets, sizes, strides)
```

### `dma.slice`

功能说明：

- 表示从 `source` 中抽取一个切片块，语义上接近“切片读取”。
- 它是 `dma.load` 的更明确切片版本，强调源区域裁剪而不是整块空间搬运。

输入：

- `source: !nn.memory<...>`
- `offsets`
- `sizes`
- `strides`
- `space` 使用 `NnMemorySpaceAttr`，表示切片结果所在空间

输出：

- `result: !nn.memory<...>`

约束：

- `result.shape` 由 `sizes` 决定
- 当前阶段必须限制 `strides` 为全 1；若出现其他值，verifier 必须报错
- `result.element_type == source.element_type`

使用示例：

```python
op = DmaSliceOp(source, offsets, sizes, strides, result_type, NnMemorySpaceAttr.from_name("local"))
```

### `dma.deslice`

功能说明：

- 表示把一个切片块写回到较大 `target` 的指定区域，语义上接近“切片回写”。
- 它是 `dma.store` 的切片版本，强调目标区域更新。

输入：

- `source: !nn.memory<...>`
- `target: !nn.memory<...>`
- `offsets`
- `sizes`
- `strides`

输出：

- 建议返回更新后的 `target`，因为该 op 的语义是“回写后得到新的目标张量状态”。

约束：

- `source.shape` 必须与 `sizes` 对应的切片形状一致
- `source.element_type == target.element_type`
- 当前阶段必须限制 `strides` 为全 1；若出现其他值，verifier 必须报错

使用示例：

```python
op = DmaDesliceOp(source, target, offsets, sizes, strides, result_type)
```

## Parse/Print 约束

- 任意被 `dma` op 引用的 `!nn.memory<...>` 文本都必须支持 parse 后再 print 回稳定文本。
- 任意被 `dma` op 引用的 `#nn.space<...>` 文本都必须支持 parse 后再 print 回稳定文本。
- 任意合法 `dma.copy/load/store/slice/deslice` 文本都必须支持 parse 后进入 verifier。
- 文本 assembly 缺失必要字段时，必须在 parse 阶段失败。

## Verifier 约束

- `NnMemorySpaceAttr` 的非法值必须按 `nn dialect` 规则报错。
- `NnMemoryType.shape` 与 `stride` rank 不一致必须按 `nn dialect` 规则报错。
- `dma.copy` 中 `source/target` 的 `shape/stride/element_type` 不一致必须报错。
- `dma.load/slice` 中 `offsets/sizes/strides` 长度与输入 rank 不一致必须报错。
- `dma.store/deslice` 中 `source.shape` 与切片目标大小不一致必须报错。
- `offsets/sizes` 出现 SSA 动态 index 必须报错，仅允许 `IntAttr`/`StringAttr`。
- `strides` 仅允许 `IntAttr(1)`，否则必须报错。
- 若当前实现限制 stride 为 1，则 `stride != 1` 的切片搬运必须显式报错，而不是 silently 接受。
- 若 op attribute `space` 与结果 type `space` 不一致，必须报错。

## Lowering 关系

- `dma.slice` 可 lowering 到 `tensor.extract_slice`、`memref.subview` 或等价目标。
- `dma.deslice` 可 lowering 到 `tensor.insert_slice`、`memref.copy` 或等价目标。
- `dma.copy` 可 lowering 到 `memref.copy`、runtime DMA copy API 或目标后端拷贝指令。
- `dma.load/store` 可作为更抽象的前端搬运语义，后续根据目标平台再收敛到底层 op。

## 测试

- 建议测试文件：[`test/dialect/test_dma_dialect.py`](../../test/dialect/test_dma_dialect.py)
- 建议执行命令：`pytest -q test/dialect/test_dma_dialect.py`

### 测试目标

- 验证 `dma` op 复用 `NnMemorySpaceAttr` / `NnMemoryType` 时，与 `nn dialect` 的类型规则保持一致。
- 验证 `dma.copy` 的整块搬运约束。
- 验证 `dma.load/slice` 的结果形状、目标空间与索引长度约束。
- 验证 `dma.store/deslice` 的源块与目标切片大小匹配约束。
- 验证当前阶段对 stride 的限制会在 verifier 阶段明确报错。

### 测试清单

| 用例 ID | 测试点 | 说明 | 建议测试 |
| --- | --- | --- | --- |
| TC-DMA-001 | 类型复用约束 | `dma` op 仅接受 `NnMemoryType` 作为 memory 类型 | `test_dma_requires_nn_memory_type` |
| TC-DMA-002 | `dma.copy` 合法通过 | `source/target` 完全匹配时 verifier 通过 | `test_dma_copy_verify_success` |
| TC-DMA-003 | `dma.copy` 形状不匹配 | 整块搬运的 `shape` mismatch 报错 | `test_dma_copy_shape_mismatch` |
| TC-DMA-004 | `dma.load` 结果空间约束 | `result.space` 必须与 op `space` 一致 | `test_dma_load_result_space_mismatch` |
| TC-DMA-005 | `dma.slice` 索引长度约束 | `offsets/sizes/strides` 长度与 rank 不一致时报错 | `test_dma_slice_rank_mismatch` |
| TC-DMA-006 | `dma.slice` stride 限制 | 当前阶段 `stride != 1` 明确报错 | `test_dma_slice_non_unit_stride_rejected` |
| TC-DMA-007 | `dma.store` 块大小约束 | `source.shape` 与写回切片大小不一致时报错 | `test_dma_store_size_mismatch` |
| TC-DMA-008 | `dma.deslice` 合法通过 | 切片回写在合法输入下通过 verifier | `test_dma_deslice_verify_success` |
| TC-DMA-009 | 类型 verifier 透传 | 非法 `space` / rank mismatch 由 `nn dialect` 类型规则报错 | `test_dma_nn_memory_type_verifier_passthrough` |
| TC-DMA-010 | 索引 StringAttr 合法路径 | `offsets/sizes` 使用 `StringAttr` 时 verifier 通过，`strides` 仍为 `IntAttr(1)` | `test_dma_index_string_attr_valid` |

## 测试标准

- `pytest -q test/dialect/test_dma_dialect.py` 返回码必须为 `0`。
- `dma.copy/load/store/slice/deslice` 的 verifier 分支必须分别有正向或反向测试覆盖。
- 若实现新增 async、event、barrier 或多维 stride 语义，必须补充 op 定义与测试清单。

## 兼容性细节

- 当前文档优先覆盖“数据搬运”这一稳定语义，而不是绑定某个硬件 DMA 引擎。
- 当前版本明确复用 `nn dialect` 的 memory type / memory space 体系，避免在 `dma dialect` 中重复维护一套类型系统。
- 若 `dma.load/store` 最终被证明只是 `slice/deslice` 的别名，也应在实现中保持 verifier 与 parse/print 口径一致，并在本 spec 中明确别名关系。
