# dma.md

## 功能简介

用于定义 `dma dialect` 的稳定方言语义，描述 `dma.alloc`、`dma.fill`、`dma.free`、`dma.copy`、`dma.load`、`dma.store`、`dma.slice`、`dma.deslice`、`dma.subview`、`dma.view`、`dma.reshape`、`dma.cast` 以及作为 lowering 目标面的 `dma.broadcast`、`dma.transpose`，用于表示内存对象之间的数据搬运、标量物化与布局转换，包括整块搬运、切片读取、切片回写、跨空间迁移、标量写入临时 memory、显式广播物化、显式转置物化、一维 byte backing 切分、视图变换与显式数据转换，并支持动态 shape 的表达。该方言不单独定义 memory type / memory space，而是统一复用 `nn dialect` 中的 `NnMemoryType` 与 `NnMemorySpaceAttr`。

## API 列表

- `class Dma(Dialect)`
- `class DmaAllocOp(dynamic_shape: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaFillOp(target: SSAValue | Operation, value: SSAValue | Operation)`
- `class DmaFreeOp(source: SSAValue | Operation)`
- `class DmaCopyOp(target: SSAValue | Operation, source: SSAValue | Operation)`
- `class DmaBroadcastOp(target: SSAValue | Operation, source: SSAValue | Operation)`
- `class DmaTransposeOp(target: SSAValue | Operation, source: SSAValue | Operation, perm: Sequence[int] | ArrayAttr)`
- `class DmaLoadOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`
- `class DmaStoreOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`
- `class DmaSliceOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`
- `class DmaDesliceOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaSubviewOp(source: SSAValue | Operation, offset: SSAValue | Operation, size: SSAValue | Operation, stride: SSAValue | Operation, result_type: NnMemoryType)`
- `class DmaViewOp(source: SSAValue | Operation, offsets: Sequence[SSAValue], shape: Sequence[SSAValue], stride: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaReshapeOp(source: SSAValue | Operation, shape: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaCastOp(target: SSAValue | Operation, source: SSAValue | Operation)`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dialect/dma.md`](../../spec/dialect/dma.md)
- `test`：[`test/dialect/test_dma.py`](../../test/dialect/test_dma.py)
- `功能实现`：[`kernel_gen/dialect/dma.py`](../../kernel_gen/dialect/dma.py)

## 依赖

- [`kernel_gen/dialect/dma.py`](../../kernel_gen/dialect/dma.py)：`dma dialect` 的方言实现入口。
- [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)：提供 `NnMemoryType` 与 `NnMemorySpaceAttr`。
- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：定义被 `dma dialect` 复用的 memory type / memory space 语义。
- [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)：定义 `!symbol.int<"expr">` 标量值语义，供 `dma` 标量输入统一复用。
- [`spec/operation/dma.md`](../../spec/operation/dma.md)：定义高层 `alloc/free/copy/load/store/slice/deslice/view/reshape/flatten/cast` API 的分层语义。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：说明高层 `Memory` 概念与 `shape/stride/dtype/space` 元信息来源。

## 目标

- 为项目提供统一的数据搬运、布局转换与显式数据转换方言层表示。
- 让整块拷贝、切片读取、切片回写、跨空间搬运与显式数据转换在 IR 中有明确 op 语义。
- 为 `const(i32)` / `!symbol.int<"expr">` 到临时 memory 的真实物化提供稳定方言层原语，避免只生成空 `dma.alloc` 占位。
- 为 `nn.broadcast/transpose` 与 mixed compare 桥接提供稳定 lowering 目标面：`dma.broadcast` / `dma.transpose`。
- 保留 `shape/stride/offsets/sizes/strides` 等搬运元信息，覆盖静态与动态场景，并统一将这些运行期标量输入建模为 `!symbol.int<"expr">` SSA value；其中 `offsets` 允许使用 `!symbol.iter<"expr">` 表达迭代变量来源。
- 为后续 lowering 到 `tensor.extract_slice`、`tensor.insert_slice`、`memref.copy`、后端 DMA 指令或 runtime API 提供稳定中间层。
- 参考 `memref.subview` / `memref.reinterpret_cast` 的设计习惯，将动态布局信息建模为显式 SSA 标量操作数，而不是仅放在 attribute 中；当前项目统一使用 `!symbol.int<"expr">` 承载这些整数标量输入。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- `dma dialect` 不单独维护 memory type / memory space，所有相关 operand / result 类型统一复用 `NnMemoryType` 与 `NnMemorySpaceAttr`。
- 本文件只定义方言层的数据搬运、布局转换与显式数据转换语义，不负责真实 DMA 设备调度、流水线编排、带宽建模、同步原语、事件、barrier 或 async token 设计。
- 本文件不负责逐元素算术、比较、归约、matmul 等张量计算语义，也不负责自动求解 `offsets/sizes/strides` 或自动推导最优搬运策略；但它提供与“数据物化/布局变换”一致的两类稳定原语：
  - `dma.broadcast`：把 scalar 或较低 rank memory 按广播规则物化写入目标 memory（用于显式广播与 mixed compare 桥接）
  - `dma.transpose`：把 source 按 perm 置换物化写入目标 memory（作为 `nn.transpose` 的 lowering 目标）
- 当前方言范围包含 `dma.alloc`、`dma.fill`、`dma.free`、`dma.copy`、`dma.broadcast`、`dma.transpose`、`dma.load`、`dma.store`、`dma.slice`、`dma.deslice`、`dma.subview`、`dma.view`、`dma.reshape`、`dma.cast`。
- 除 `dma.cast` 与 `dma.fill` 外，其他搬运 op 不改变元素值语义，只改变数据所在的逻辑位置、切片范围、布局表达或空间；同一个 op 不应同时承担计算和搬运语义。
- 本文件中的“转换”包含三类：布局、切片视图或空间层面的转换，通过 `dma.cast` 表达的显式元素类型转换，以及通过 `dma.fill` 表达的标量到 memory 物化；不包括 memory-memory 广播、归约或通用数值计算。

### 分层约束

- `spec/operation/dma.md` 负责高层 API 语义；`dma dialect` 负责对应 IR 语义。
- 若高层 `Memory` 进入 IR，仍必须落到 `NnMemoryType` / `NnMemorySpaceAttr`，不得在 `dma dialect` 内再定义一套分配专用类型。
- `operation/dma` 的 `view/reshape/flatten` 分别映射到 `dma.view` 与 `dma.reshape`；`flatten` 作为 `reshape` 的一维特例，不在方言层新增独立 op。

### 通用约束

- 所有参与搬运或转换的 `source`、`target`、`result` 必须是 `!nn.memory<...>`。
- `dma.alloc` 仅产生结果内存，结果类型必须为 `!nn.memory<...>`。
- `dma.fill` 仅把单个整数标量真实写入目标内存，不分配新内存，也不返回新的 memory result。
- `dma.free` 仅接受待释放的内存 operand，不产生结果。
- `dma.view/reshape` 必须保证 `result.space` 与 `source.space` 一致；`result.element_type` 必须与 `source.element_type` 一致（仅当 `source` 是一维 `i8` byte pool 时允许不同 element_type，且允许 `source` 与 `result` 的 rank 不一致）。
- 对 `dma.copy/load/store/slice/deslice`，相关 `element_type` 必须一致，不允许隐式类型转换。
- 对 `dma.cast`，只允许 `element_type` 发生显式变化；`shape/stride/space` 必须保持一致。
- `shape/stride` 的 rank 必须与相关 `offsets/sizes/strides` 列表长度一致。
- `offsets` 允许使用 `!symbol.int<"expr">` 或 `!symbol.iter<"expr">`；`sizes`、`strides`、动态 `shape`、动态 `stride` 必须建模为显式 `!symbol.int<"expr">` SSA 操作数列表；不得只靠 `StringAttr("?")`、`ArrayAttr` 或其他 attribute 独立表达运行期值。
- index-like 标量 operand 中，`offsets` 允许 `!symbol.int<"expr">` 或 `!symbol.iter<"expr">`；其余仍仅接受 `!symbol.int<"expr">` SSA value。禁止直接使用 Python `int/float` 或 builtin 数值类型替代，静态常量必须先 materialize 为 `!symbol.int<"expr">`。
- `dma.fill.value` 不属于 index-like 布局 operand。当前公开口径仅接受 builtin `i32` 或 `!symbol.int<"expr">` 两类整数标量，并要求 `target.element_type == i32`；`f16/f32` 或更宽整数的 scalar materialize 不在本轮范围内。
- `!nn.memory<...>` 类型仍负责承载 rank、元素类型、内存空间以及可静态判定的布局信息；凡是运行期才确定的布局值，必须由 op operand 传入。
- 若实现保留静态维度或静态 stride 在类型中，assembly 中的静态值也应允许通过 `!symbol.int<"1">` 这类 symbol 常量值、或等价 materialize 后的 `!symbol.int<"expr">` SSA value 显式传入 operand，保证“布局参数来源统一为 operand”。
- `dma.load/store/slice/deslice` 的 `offsets` 必须为 variadic `!symbol.int<"expr">` 或 `!symbol.iter<"expr">` operand；`sizes/strides` 仍为 variadic `!symbol.int<"expr">` operand。
- `dma.slice` 必须采用目标式 `dma.slice(target, source, offsets, sizes, strides)`：由 `target` 承载切片结果，op 本身不产生 result。
- `dma.slice` 的稳定搬运路径语义固定为 `source.space -> target.space`；逻辑字节数按 `sizes` 对应的元素数乘以 `element_type` 字节大小计算。
- `dma.view` 中与动态布局相关的 `offsets` 允许 `!symbol.int<"expr">` 或 `!symbol.iter<"expr">`，`shape/stride` 仍需 `!symbol.int<"expr">` operand 显式传入；不得仅依赖结果类型里的符号维度推断。
- `dma.subview` 只表达一维 `i8` backing memory 到一维 typed memory 的连续切分；`offset/size/stride` 必须各由一个 `!symbol.int<"expr">` SSA operand 提供，且 `offset >= 0`、`size >= 1`、`stride >= 1`。
- `dma.subview` 的 `source` 必须是一维 `i8` memory，`result` 必须是一维 contiguous memory，`source.space == result.space`，`size` 必须与 `result_type.shape` 完全一致。
- `dma.view` 的 `result_type.shape` 必须由 `shape` operand（DSL `view(..., size, ...)`）确定，`result_type.stride` 必须由 `stride` operand（DSL `view(..., stride)`）确定；二者都必须与对应 operand 一一对齐，不得只因“生成了 `dma.view` op”就视为合同对齐成功。
- 当 `dma.view` 结果直接参与 `func.return` 时，返回的 `!nn.memory<...>` 类型必须与同一份 `result_type` 完全一致；`test/dsl/ast/test_mlir_gen.py` 中的 `EXPECTED_MEMORY` 比对依赖这一边界。
- 静态可判定时 `dma.view` 的 `source/result` `numel` 必须一致；若 `source` 为一维 `i8` byte pool，则要求字节数一致且静态边界不越界。
- `dma.reshape` 仅接受动态 `shape` operand，且这些 operand 必须为 `!symbol.int<"expr">`；结果 `stride` 按 `shape` 的默认连续布局语义生成。
- `dma.alloc` 仅接受动态 `shape` operand，且这些 operand 必须为 `!symbol.int<"expr">`；允许两种形态：与结果 rank 等长的全量列表，或仅包含结果 `shape` 中符号维度的列表（按出现顺序）；`stride` 不作为输入，而是按默认连续布局语义生成。
- 对 mixed add 等需要 `scalar -> memory` 合法化的链路，当前唯一公开合法原语是 `dma.alloc + dma.fill(target, value)`：`dma.alloc` 负责生成 temporary memory，`dma.fill` 负责把 `const(i32)` / `!symbol.int<"expr">` 真实写入该 memory 的每个逻辑元素。仅生成空 `dma.alloc` 占位，或生成 `dma.fill` 后其 `target` 在下游 IR 中 `users=[]`，都不属于当前链路的通过口径。
- `strides` 当前每一维仍限制为单位步长语义，但该约束应体现在 operand 校验阶段，而不是要求使用 `IntAttr(1)` attribute。
- operation 层允许非单位 `strides` 作为切片步进，但本方言仅实现单位步长语义；因此含非单位 `strides` 的 `dma.load/store/slice/deslice` 必须在 lowering/verifier 阶段拒绝。原因：现有 lowering 目标与 verifier 规则仅覆盖单位步长切片。
- 若上层 pass 需要把窗口化 hierarchy 搬运收口到 `dma.slice/dma.deslice`，只能复用原窗口的 `offsets/sizes`；新插入的 hierarchy 路径 `strides` 必须继续物化为全 `1`，不得借此扩展本方言到非单位或符号 stride 语义。
- `sizes` 中每一维必须具有正整数语义，不允许负值；若 `!symbol.int<"expr">` 不能静态证明为正值，则至少要拒绝 `!symbol.int<"0">` 与可静态判定的负值。
- 若 op 带有目标空间 attribute，则其值必须与结果 type 或目标 type 的 `space` 一致。

#### 默认连续 stride 推导（符号维度）

- 当 `shape` 中包含 `StringAttr` 时，默认连续 stride 仍按从右到左的累计乘积推导；单个符号如 `N` 直接参与乘积，多维组合可形成 `M*N` 等字符串表达。
- `StringAttr` 维度可包含 `min(lhs, rhs)` 形式的整数符号最小值；默认连续 stride 与 contiguous verifier 必须按符号表达式等价关系判断，而不是只比较原始字符串。
- 若维度为 `StringAttr("?")` 或包含 `?` 的表达式，视为未知：该维度及其左侧更高维的默认 stride 统一退化为 `StringAttr("?")`，右侧维度仍按既有规则生成（末维为 `1`）。
- 该规则仅用于 `dma.alloc` / `dma.reshape` 的默认连续 stride 推导与 verifier 校验，不替代显式 `!symbol.int<"expr">` SSA operand 建模；`offsets` 允许 `!symbol.int<"expr">` 或 `!symbol.iter<"expr">`，`sizes/strides` 仍必须通过 `!symbol.int<"expr">` SSA operand 传入。

### operation API 映射

对照 [`spec/operation/dma.md`](../../spec/operation/dma.md)，operation 层 API 与 `dma dialect` op 的对应关系如下。operation 层 `Memory/shape/stride` 等信息在进入方言层时必须落到 `!nn.memory<...>` 与 `!symbol.int<"expr">` 形式。

| operation API | dialect op | 说明 |
| --- | --- | --- |
| `alloc(shape, dtype, space=MemorySpace.GM, stride=None)` | `dma.alloc` | 创建内存对象。 |
| `（无直接 DSL helper；pass 侧合法化原语）` | `dma.fill` | 将 `const(i32)` / `!symbol.int<"expr">` 真实写入 `target` 的每个逻辑元素；当前用于 mixed add 的 `scalar -> memory` 合法化。 |
| `free(value)` | `dma.free` | 释放内存对象。 |
| `copy(source, space)` | `dma.copy` | 跨空间搬运。 |
| `cast(source, dtype, memoryspace=None)` | `dma.cast` | 显式元素类型转换。 |
| `load(source, offsets, sizes, strides=None, space=None)` | `dma.load` | 切片读取。 |
| `store(target, source, offsets, sizes, strides=None)` | `dma.store` | 切片写回。 |
| `slice(source, offsets, sizes, strides=None, space=None)` | `dma.alloc + dma.slice(target, source, offsets, sizes, strides)` | 先分配 `target`，再执行目标式切片写入；表达式值绑定到 `dma.alloc` 的结果。 |
| `deslice(target, source, offsets, sizes, strides=None)` | `dma.deslice` | 切片写回（语义等价于 `store`）。 |
| `（无直接 DSL helper；pass 侧合法化原语）` | `dma.subview` | 从一维 `i8` backing memory 按目标 dtype 元素单位切出一维 contiguous typed memory，当前用于 `memory-pool` rewrite。 |
| `view(source, offset, size, stride)` | `dma.view` | 视图重解释，`offset/size/stride` 分别映射为 `dma.view` 的 `offsets/shape/stride` operand；`result_type.shape == size`、`result_type.stride == stride`，静态可判定时要求 `source/result` `numel` 一致；若该结果直接返回，则 `func.return` 类型必须与同一 `result_type` 一致。 |
| `reshape(source, shape)` | `dma.reshape` | 连续布局 reshape。 |
| `flatten(source)` | `dma.reshape` | 视为 `reshape` 到一维形状。 |

补充说明：

- `view` 的 `offset/size/stride` 在方言层分别对应 `dma.view` 的 `offsets/shape/stride` operand；`shape/stride` operand 与 `result_type.shape/stride` 必须一致。
- 对当前验收子集，`dma.view` 的 `result_type.shape` 必须来自 DSL `size`，`result_type.stride` 必须来自 DSL `stride`；不得只复用上层 `Memory` 既有元信息或仅以“成功生成 `dma.view` op”为通过条件。
- 若 `mlir_gen(...)` / `emit_mlir` 让 `dma.view` 结果直接流向 `func.return`，则 `func.return` 携带的 `!nn.memory<...>` 类型必须与 `dma.view.result_type` 完全一致；`EXPECTED_MEMORY` 比对即基于这份返回类型。
- `dma.fill` 当前没有直接 DSL helper；它是 dialect / pass 层公开原语。对 `nn.add(memory, const(i32) / symbol.int)` 这类 mixed add 路径，当前最小合法 lower 片段必须显式包含 `dma.alloc + dma.fill`，且被填充的 temporary memory 必须在后续 IR 中被实际消费。
- operation 层允许“静态可判定的缩小 subview”（`size` 的 `numel` 小于 `source.shape`），但当前 `dma.view` 在静态可判定时要求 `source/result` `numel` 一致；该场景不属于当前 `dma.view` 的可验证映射子集。
- `operation.slice(...)-> dma.alloc + dma.slice(target, source, offsets, sizes, strides)`：`dma.slice` 只负责把切片内容写入 `target`，不返回新的 memory result；operation 表达式返回值来自前置 `dma.alloc` 的 result。

### Parse/Print 与 Verifier 约束

- 任意被 `dma` op 引用的 `!nn.memory<...>` 与 `#nn.space<...>` 文本都必须支持 parse 后再 print 回稳定文本。
- 任意合法 `dma.copy/fill/load/store/slice/deslice/cast` 文本都必须支持 parse 后进入 verifier。
- assembly 缺失必要字段时，必须在 parse 阶段失败。
- `NnMemorySpaceAttr` 非法值、`NnMemoryType.shape` 与 `stride` rank 不一致等类型错误，必须按 `nn dialect` 规则报错。
- `dma.copy` 中 `source/target` 的 `shape/stride/element_type` 不一致必须报错。
- `dma.alloc` 的动态 `shape` operand 必须与结果 rank 等长，或仅覆盖结果 `shape` 中符号维度（按出现顺序）；任一 `shape` operand 不是 `!symbol.int<"expr">` 时必须报错；结果类型非法必须报错。
- `dma.fill` 中 `target` 不是 `!nn.memory<...>`、`target.element_type != i32`、或 `value` 既不是 builtin `i32` 也不是 `!symbol.int<"expr">` 时必须报错。
- `dma.free` 的 operand 不是 `!nn.memory<...>` 时必须报错。
- `dma.load/slice` 中 `offsets/sizes/strides` 长度与输入 rank 不一致必须报错；`sizes/strides` 不是 `!symbol.int<"expr">` 时必须报错；`offsets` 仅允许 `!symbol.int<"expr">` 或 `!symbol.iter<"expr">`。
- `dma.store/deslice` 中 `source.shape` 与切片目标大小不一致必须报错。
- `dma.view/reshape` 中 `source/result` 的 `space` 不一致必须报错；`element_type` 不一致仅在 `source` 为一维 `i8` byte pool 时允许；`source/result` rank 不一致仅在 byte pool 场景允许；可判定的 `numel` 不一致必须报错（byte pool 场景按字节数判断）。
- `dma.view` 的动态 `offsets/shape/stride` operand 数量与 rank 不一致必须报错；`shape/stride` 不是 `!symbol.int<"expr">` 时必须报错；`offsets` 仅允许 `!symbol.int<"expr">` 或 `!symbol.iter<"expr">`；`dma.reshape` 的动态 `shape` operand 数量与 rank 不一致必须报错，且其 operand 必须为 `!symbol.int<"expr">`。
- `dma.view` 的 `offsets` 必须为非负整数；当 `source.shape/offsets/shape/stride` 可静态判定时，必须进行边界校验并在越界时报错。
- `dma.view` 的 `result.stride` rank 与 `result.shape` 不一致必须报错；`dma.reshape` 的 `result.stride` 非连续行主序必须报错。
- `dma.subview` 的 `source` 非一维 `i8` memory、`result` 非一维 contiguous memory、`source/result` space 不一致、`offset/size/stride` 非单个 `!symbol.int<"expr">`、`size` 与结果 shape 不一致，或静态可判定 byte 边界越界时必须报错。
- `dma.reshape` 的连续行主序校验必须接受含 `min(lhs, rhs)` 的等价符号 stride 表达式；例如动态尾块 shape 中出现 `min(tile, extent - iter)` 时，不得仅因乘法因子打印顺序或 `min` 文本形式不同而拒绝。
- `dma.cast` 中 `source/result` 的 `shape/stride/space` 不一致必须报错。
- `strides` 当前仅允许单位步长语义；若当前实现限制 stride 为 1，则 `stride != 1` 的切片搬运必须显式报错，不得 silently 接受。
- `dma` 的布局/索引类标量输入以 `!symbol.int<"expr">` 为主，`offsets` 额外允许 `!symbol.iter<"expr">`；parse/print 不得再使用 builtin `index` 作为这些 operand 的公开文本语义。`dma.fill.value` 是当前唯一例外，公开口径允许 builtin `i32` 与 `!symbol.int<"expr">`。
## API详细说明

### `class Dma(Dialect)`

- api：`class Dma(Dialect)`
- 参数：无。
- 返回值：`Dma` dialect 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.dma import Dma

  dma = Dma
  assert dma.name == "dma"
  ```
- 功能说明：声明并导出 `dma dialect`，聚合本文件列出的公开 op。
- 注意事项：`Dma` 只承载 dialect 注册信息；memory type / memory space 继续复用 `nn dialect`。

### `class DmaAllocOp(dynamic_shape: Sequence[SSAValue], result_type: NnMemoryType)`

- api：`class DmaAllocOp(dynamic_shape: Sequence[SSAValue], result_type: NnMemoryType)`

- 功能说明：

- 表示显式的内存对象创建，仅生成结果 `!nn.memory<...>`。
- 不承担数据搬运或初始化语义。

- 参数：

- `dynamic_shape`：variadic `!symbol.int<"expr">` operand，按 rank 顺序提供运行期 shape。
- `result_type`：结果类型，必须为 `!nn.memory<...>`。

- 使用示例：

```python
op = DmaAllocOp(dynamic_shape, result_type)
```

- 注意事项：

- `result_type` 中的 `shape/stride/element_type/space` 必须完整且合法。
- 若结果布局含运行期 shape 信息，则对应符号维必须由 `dynamic_shape` operand 提供，静态维可省略；每个 operand 都必须是 `!symbol.int<"expr">`。
- `dynamic_shape` 支持两种形态：与结果 rank 等长的全量列表，或仅包含结果 `shape` 中符号维度的列表（按出现顺序）。
- 结果 `stride` 不作为输入，由 `result_type.shape` 与默认连续布局规则共同确定。
- 当前版本不额外定义 base offset；`dma.alloc` 只负责产生新的 memory 对象。

- 返回值：

- 返回新的 `!nn.memory<...>`；当前 op result 数量固定为 `1`。
- 仅表达“存在一个内存对象”的语义，不负责初始化或填充值。

### `class DmaFillOp(target: SSAValue | Operation, value: SSAValue | Operation)`

- api：`class DmaFillOp(target: SSAValue | Operation, value: SSAValue | Operation)`

- 功能说明：

- 表示将单个整数标量真实写入 `target` 的每个逻辑元素，完成 `scalar -> memory` 物化。
- 当前用于 mixed add 等链路把 `const(i32)` / `!symbol.int<"expr">` 合法化为可被下游 IR 消费的 temporary memory。

- 参数：

- `target`：被写入的目标内存，类型为 `!nn.memory<...>`。
- `value`：待物化的整数标量，当前仅接受 builtin `i32` 或 `!symbol.int<"expr">`。

- 使用示例：

```python
op = DmaFillOp(target, value)
```

- 注意事项：

- `target.element_type` 当前固定为 `i32`；更宽整数、`f16`、`f32` 等其他 scalar family 不在本轮公开范围内。
- 当 `value` 为 builtin `i32` 时，对应 `const(i32)` 物化路径；当 `value` 为 `!symbol.int<"expr">` 时，对应 `symbol.int` 物化路径；两者都必须以真实 SSA operand 进入 `dma.fill`，不得退化为 attribute 占位。
- 若上层 DSL `fill(...)` helper 接受字符串字面量并继续 lower 到当前链路，公开字符串只允许表示正无穷 / 负无穷的两种规范语义；当前文面固定为 `"inf"` 与 `"-inf"`，不得放宽到其他大小写、别名或任意字符串。该规则属于更高层 helper 边界，不能扩展 `dma.fill.value` 在本层仍只接受 builtin `i32` / `!symbol.int<"expr">` 的事实。
- `dma.fill` 必须把同一个标量值写入 `target` 的每个逻辑元素；它不是 `dma.alloc` 的语法糖，也不等价于“只创建 memory 但不写值”。
- `dma.fill` 只负责标量写入，不承担 memory-memory 广播、逐元素算术或 dtype promotion。
- verifier 只检查 `dma.fill` 的局部类型与接口合法性；“该 `target` 是否在下游 IR 中被实际消费”属于链路级验收边界。对 mixed add 当前最低通过口径，必须出现 `dma.alloc + dma.fill + downstream use(target)` 的完整片段，`users=[]` 的 dead temporary memory 不能计为通过。

- 返回值：

- 返回类型为无返回值；当前 op result 数量固定为 `0`。
- 当前只收为 `i32 | !symbol.int<"expr"> -> !nn.memory<..., i32, ...>` 的最小公开子集；若后续需要浮点或更宽整数 materialize，必须新增独立 spec 收口。

### `class DmaFreeOp(source: SSAValue | Operation)`

- api：`class DmaFreeOp(source: SSAValue | Operation)`

- 功能说明：

- 表示显式释放内存对象，结束该 `!nn.memory<...>` 的生命周期。
- 仅表达释放语义，不负责数据搬运或数据清零。

- 参数：

- `source`：待释放的内存对象，类型为 `!nn.memory<...>`。

- 使用示例：

```python
op = DmaFreeOp(source)
```

- 注意事项：

- `source` 必须为 `!nn.memory<...>`；其他类型必须在 verifier 阶段报错。
- `dma.free` 不改变 `source` 的类型信息，也不返回新的内存对象。

- 返回值：

- 返回类型为无返回值；当前 op result 数量固定为 `0`。
- 语义上通过 side effect 表达释放行为，不产生新的 `!nn.memory<...>`。

### `class DmaCopyOp(target: SSAValue | Operation, source: SSAValue | Operation)`

- api：`class DmaCopyOp(target: SSAValue | Operation, source: SSAValue | Operation)`

- 功能说明：

- 表示整块拷贝，将 `source` 的全部内容搬运到 `target`。
- 用于表达不涉及切片的完整搬运。

- 参数：

- `target`：目标内存，类型为 `!nn.memory<...>`。
- `source`：源内存，类型为 `!nn.memory<...>`。

- 使用示例：

```python
op = DmaCopyOp(target, source)
```

- 注意事项：

- `source.shape`、`target.shape` 必须一致。
- `source.stride`、`target.stride` 必须一致。
- `source.element_type`、`target.element_type` 必须一致。
- `source.space` 与 `target.space` 可以相同，也可以不同；不同空间表示显式跨空间搬运。
- `lower-dma-memory-hierarchy` 的 `apply_op` 规则使用 `dma.alloc + dma.copy` 表达整块跨空间 staging；该场景不使用 `dma.slice / dma.deslice` 表示规则搬运。

- 返回值：

- 返回类型为无返回值；当前 op result 数量固定为 `0`。
- 语义上通过 side effect 表达对 `target` 的整块写入，不返回新的 `!nn.memory<...>`。

### `class DmaBroadcastOp(target: SSAValue | Operation, source: SSAValue | Operation)`

- api：`class DmaBroadcastOp(target: SSAValue | Operation, source: SSAValue | Operation)`

- 功能说明：

- 将 `source` 按广播规则物化写入 `target`，作为显式广播与 mixed compare 桥接的统一 lowering 目标面。
- `dma.broadcast` 不返回新的 memory；被写入的结果由 `target` 承载。

- 参数：

- `target`：写入目标内存，类型为 `!nn.memory<...>`。
- `source`：广播源，可为：
  - `!nn.memory<...>`（memory-to-memory 广播物化）
  - builtin 标量（如 `i32/f16/f32` 等）
  - `!symbol.int<"expr">`（整数标量）

- 使用示例：

```mlir
%rhs_b = dma.alloc value : !nn.memory<[M, N], i32, #nn.space<LM>>
%c7 = arith.constant 7 : i32
dma.broadcast(%rhs_b, %c7) : (!nn.memory<[M, N], i32, #nn.space<LM>>, i32) -> ()
```

- 注意事项：

- `target` 必须为 `!nn.memory<...>`，且 `target.shape/stride/space/element_type` 必须完整可校验。
- 当 `source` 为 `!nn.memory<...>` 时：
  - `source.element_type` 必须等于 `target.element_type`。
  - `source.space` 必须等于 `target.space`（跨空间广播不在本轮公开合同范围内）。
  - 广播规则固定为尾维对齐：对齐后任一维若两侧均为静态整数且既不相等也不包含 `1`，verifier 必须失败；否则视为兼容（不做数值求解）。
- 当 `source` 为标量时：
  - 标量类型必须与 `target.element_type` 一致；`!symbol.int<"expr">` 仅用于整数 element_type 的标量输入。
- 禁止 silent fallback：不允许把不兼容的广播或类型失配默认为“成功但不写入”，verifier 必须失败或在 pass 层显式报错。

- 返回值：

- 返回类型为无返回值；当前 op result 数量固定为 `0`。
- 语义上通过 side effect 表达对 `target` 的整块写入，不返回新的 `!nn.memory<...>`。

### `class DmaTransposeOp(target: SSAValue | Operation, source: SSAValue | Operation, perm: Sequence[int] | ArrayAttr)`

- api：`class DmaTransposeOp(target: SSAValue | Operation, source: SSAValue | Operation, perm: Sequence[int] | ArrayAttr)`

- 功能说明：

- 按 `perm` 对 `source` 做维度置换，并将结果物化写入 `target`。
- 作为 `nn.transpose` 的 lowering 目标面，禁止在 `kernel` 层保留 `transpose` 的隐式语义。

- 参数：

- `source`：转置输入内存，类型为 `!nn.memory<...>`。
- `target`：写入目标内存，类型为 `!nn.memory<...>`。
- `perm`：轴置换 attribute，必须为 `0..rank-1` 的排列。

- 使用示例：

```mlir
%out = dma.alloc value : !nn.memory<[N, M], f16, #nn.space<LM>>
dma.transpose(%src, %out) {perm = [1, 0]} : (!nn.memory<[M, N], f16, #nn.space<LM>>, !nn.memory<[N, M], f16, #nn.space<LM>>) -> ()
```

- 注意事项：

- `source/target` 必须为 `!nn.memory<...>`，且 `element_type/space` 必须一致。
- `perm` 必须为合法排列且长度等于 `source.rank`；存在重复索引或越界时 verifier 必须失败。
- `target.shape` 必须与按 `perm` 重排的 `source.shape` 机械一致；当相关维度为静态整数或可直接比较的符号时必须执行一致性校验，不做数值求解。
- `target.stride` 必须是 `target.shape` 的默认连续 stride；`dma.transpose` 是物化搬运，不表达非连续视图。
- 禁止 silent fallback：perm 非排列、rank 不一致、shape 不一致时不得退化为 “copy/view”，必须显式失败。

- 返回值：

- 返回类型为无返回值；当前 op result 数量固定为 `0`。
- 语义上通过 side effect 表达对 `target` 的写入，不返回新的 `!nn.memory<...>`。

### `class DmaLoadOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`

- api：`class DmaLoadOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`

- 功能说明：

- 表示从较大 `source` 中读取一块数据，并生成新的结果块。
- 常用于从 `global` 搬到 `shared` 或 `local` 的读搬运。

- 参数：

- `source`：源内存，类型为 `!nn.memory<...>`。
- `offsets`：variadic `!symbol.int<"expr">` 或 `!symbol.iter<"expr">` operand，长度必须与 `source.rank` 一致；每一维表示对应维度的起始索引。
- `sizes`：variadic `!symbol.int<"expr">` operand，长度必须与 `source.rank` 一致；每一维表示对应维度的切片大小。
- `strides`：variadic `!symbol.int<"expr">` operand，长度必须与 `source.rank` 一致；每一维表示对应维度的切片步长，当前每一维必须具有单位步长语义。
- `space`：结果空间，使用 `NnMemorySpaceAttr` 表示。
- `result_type`：结果类型，必须为 `!nn.memory<...>`。

- 使用示例：

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

- 注意事项：

- `result.shape` 由 `sizes` 决定。
- `result.space` 必须与 op `space` 一致。
- `result.element_type` 必须与 `source.element_type` 一致。
- `offsets/sizes/strides` 必须全部通过 operand 提供；若是静态常量，也应先 materialize 为 `!symbol.int<"1">` 这类 symbol 常量值或等价的 `!symbol.int<"expr">` SSA value 后传入；`offsets` 允许使用 `!symbol.iter<"expr">`。

- 返回值：

- 返回新的 `!nn.memory<...>` 结果块。
- 当前支持 SSA 动态 `!symbol.int<"expr">` 标量输入；`offsets` 也允许 `!symbol.iter<"expr">`；但仍不支持非单位 stride 语义。

### `class DmaStoreOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`

- api：`class DmaStoreOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`

- 功能说明：

- 表示把 `source` 块写回 `target` 的某个区域。
- 常用于从 `shared` 或 `local` 写回 `global`。

- 参数：

- `target`：被更新的目标内存，类型为 `!nn.memory<...>`。
- `source`：待写回的源块，类型为 `!nn.memory<...>`。
- `offsets`：variadic `!symbol.int<"expr">` 或 `!symbol.iter<"expr">` operand；每一维表示 `target` 对应维度的写回起始索引，长度必须与 `target.rank` 一致。
- `sizes`：variadic `!symbol.int<"expr">` operand；每一维表示写回区域在 `target` 对应维度的大小，长度必须与 `target.rank` 一致。
- `strides`：variadic `!symbol.int<"expr">` operand；每一维表示 `target` 对应维度的写回步长，长度必须与 `target.rank` 一致，当前每一维必须具有单位步长语义。

- 使用示例：

```python
op = DmaStoreOp(target, source, offsets, sizes, strides)
```

- 注意事项：

- `source.shape` 必须与 `sizes` 对应的切片形状一致。
- `source.element_type` 必须与 `target.element_type` 一致。
- `offsets/sizes/strides` 长度必须与 `target.rank` 一致；`offsets` 允许 `!symbol.int<"expr">` 或 `!symbol.iter<"expr">`，`sizes/strides` 仍必须是 `!symbol.int<"expr">`。
- `offsets/sizes/strides` 必须全部通过 operand 提供，其中 `offsets` 允许 `!symbol.iter<"expr">`，`sizes/strides` 仍为 `!symbol.int<"expr">`。

- 返回值：

- 返回类型为无返回值；当前 op result 数量固定为 `0`。
- 语义上通过 side effect 表达对 `target` 指定切片区域的写回，不返回新的 `!nn.memory<...>`。

### `class DmaSliceOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`

- api：`class DmaSliceOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`

- 功能说明：

- 表示把 `source` 指定切片区域写入预先分配的 `target`，语义上是“目标式切片搬运”。
- 该 op 不分配新内存，也不返回结果值；切片结果由 `target` 承载。

- 参数：

- `target`：切片写入目标内存，类型为 `!nn.memory<...>`。
- `source`：源内存，类型为 `!nn.memory<...>`。
- `offsets`：variadic `!symbol.int<"expr">` 或 `!symbol.iter<"expr">` operand；每一维表示对应维度的起始索引，长度必须与 `source.rank` 一致。
- `sizes`：variadic `!symbol.int<"expr">` operand；每一维表示对应维度的切片大小，长度必须与 `source.rank` 一致。
- `strides`：variadic `!symbol.int<"expr">` operand；每一维表示对应维度的切片步长，长度必须与 `source.rank` 一致，当前每一维必须具有单位步长语义。

- 使用示例：

```python
op = DmaSliceOp(target, source, offsets, sizes, strides)
```

- 注意事项：

- `target.shape` 必须与 `sizes` 描述的切片形状一致。
- `target.element_type` 必须与 `source.element_type` 一致。
- 当前阶段必须限制 `strides` 为全 1；出现其他值时 verifier 必须报错。
- 若某个 lowering pass 用 `dma.slice` 表达整块 hierarchy 搬运，必须把整块路径编码为 full-window 特例：`offsets=0`、`sizes=source.shape`、`strides=1`；若输入来自 `dma.view`，仅允许继承该窗口的 `offsets/sizes`，不得继承非单位 `stride`。
- `offsets/sizes/strides` 必须全部通过 operand 提供，其中 `offsets` 允许 `!symbol.iter<"expr">`，`sizes/strides` 仍为 `!symbol.int<"expr">`。
- `target` 与 `source` 必须是同 rank 且兼容布局的 `!nn.memory<...>`；该约束用于保证切片写入合法。
- `dma.slice` 不负责返回新内存，若上层 API 需要切片表达式返回值，必须通过 `dma.alloc` 先构造 `target` 并返回该 `target`。

- 返回值：

- 返回类型为无返回值；当前 op result 数量固定为 `0`。
- 可 lowering 到“对子视图目标执行 copy/insert”的等价目标形式。

### `class DmaDesliceOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue], result_type: NnMemoryType)`

- api：`class DmaDesliceOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue], result_type: NnMemoryType)`

- 功能说明：

- 表示把一个切片块写回到较大 `target` 的指定区域，语义上接近切片回写。
- 它与 `dma.store` 一样负责目标区域更新，但更强调按切片语义回写。

- 参数：

- `source`：待回写的切片块，类型为 `!nn.memory<...>`。
- `target`：被更新的较大目标内存，类型为 `!nn.memory<...>`。
- `offsets`：variadic `!symbol.int<"expr">` 或 `!symbol.iter<"expr">` operand；每一维表示 `target` 对应维度的回写起始索引，长度必须与 `target.rank` 一致。
- `sizes`：variadic `!symbol.int<"expr">` operand；每一维表示回写区域在 `target` 对应维度的大小，长度必须与 `target.rank` 一致。
- `strides`：variadic `!symbol.int<"expr">` operand；每一维表示 `target` 对应维度的回写步长，长度必须与 `target.rank` 一致，当前每一维必须具有单位步长语义。
- `result_type`：结果类型，必须为 `!nn.memory<...>`，且必须与 `target` 类型一致。

- 使用示例：

```python
op = DmaDesliceOp(target, source, offsets, sizes, strides, result_type)
```

- 注意事项：

- `source.shape` 必须与 `sizes` 对应的切片形状一致。
- `source.element_type` 必须与 `target.element_type` 一致。
- 当前阶段必须限制 `strides` 为全 1；出现其他值时 verifier 必须报错。
- 若某个 lowering pass 用 `dma.deslice` 表达整块 hierarchy 写回，必须把整块路径编码为 full-window 特例：`offsets=0`、`sizes=target.shape`、`strides=1`；若写回目标来自 `dma.view`，仅允许继承该窗口的 `offsets/sizes`，回写 `strides` 仍必须保持单位步长。
- `offsets/sizes/strides` 必须全部通过 operand 提供，其中 `offsets` 允许 `!symbol.iter<"expr">`，`sizes/strides` 仍为 `!symbol.int<"expr">`。

- 返回值：

- 返回类型为 `!nn.memory<...>`；当前 op result 数量固定为 `1`。
- 返回值语义为“回写完成后的目标内存”，其类型必须与 `target` 完全一致。
- 可 lowering 到 `tensor.insert_slice`、`memref.copy` 或等价目标。

### `class DmaSubviewOp(source: SSAValue | Operation, offset: SSAValue | Operation, size: SSAValue | Operation, stride: SSAValue | Operation, result_type: NnMemoryType)`

- api：`class DmaSubviewOp(source: SSAValue | Operation, offset: SSAValue | Operation, size: SSAValue | Operation, stride: SSAValue | Operation, result_type: NnMemoryType)`

- 功能说明：

- 从一维 `i8` backing memory 中按目标 dtype 元素单位切出一维 typed memory。
- 当前公开用途是 `memory-pool` pass 的 rewrite 目标面，配合 `dma.reshape` 恢复原 alloc type。

- 参数：

- `source`：源 backing memory；类型必须为一维 `!nn.memory<[N], [1], i8, #nn.space<...>>`。
- `offset`：单个 `!symbol.int<"expr">` operand；按 `result_type.element_type` 的元素单位表达；必须非负。
- `size`：单个 `!symbol.int<"expr">` operand；按 `result_type.element_type` 的元素数量表达；必须与 `result_type.shape` 一致。
- `stride`：单个 `!symbol.int<"expr">` operand；按 `result_type.element_type` 的元素单位表达；当前合法路径使用 `1`，静态负值或 0 必须被拒绝。
- `result_type`：一维 contiguous typed memory；类型必须为 `NnMemoryType`。

- 使用示例：

```python
op = DmaSubviewOp(source, offset, size, stride, result_type)
```

- 注意事项：

- `source.space` 必须与 `result_type.space` 一致。
- `source.element_type` 必须是 `i8`；`result_type.element_type` 可以是公开支持的 typed memory dtype。
- `result_type.shape` 必须是一维；`result_type.stride` 必须是一维连续 `[1]`。
- 静态可判定时，`(offset + (size - 1) * stride + 1) * sizeof(result_dtype)` 不得超过 source byte length。
- `dma.subview` 不替代通用多维 `dma.view`；它只表达 byte backing memory 的一维 typed 切分。

- 返回值：

- 返回一维 typed `!nn.memory<...>`；当前 op result 数量固定为 `1`。

### `class DmaViewOp(source: SSAValue | Operation, offsets: Sequence[SSAValue], shape: Sequence[SSAValue], stride: Sequence[SSAValue], result_type: NnMemoryType)`

- api：`class DmaViewOp(source: SSAValue | Operation, offsets: Sequence[SSAValue], shape: Sequence[SSAValue], stride: Sequence[SSAValue], result_type: NnMemoryType)`

- 功能说明：

- 表示对 `source` 的视图变换，仅调整 `shape/stride` 元信息。
- 用于表达不发生搬运的数据视图重解释。

- 参数：

- `source`：源内存，类型为 `!nn.memory<...>`。
- `offsets`：variadic `!symbol.int<"expr">` 或 `!symbol.iter<"expr">` operand，按 rank 顺序提供子视图起始偏移。
- `shape`：variadic `!symbol.int<"expr">` operand，按 rank 顺序提供结果视图的 shape。
- `stride`：variadic `!symbol.int<"expr">` operand，按 rank 顺序提供结果视图的 stride。
- `result_type`：结果类型，必须为 `!nn.memory<...>`。

- 使用示例：

```python
op = DmaViewOp(source, offsets, shape, stride, result_type)
```

- 注意事项：

- `result.space` 必须与 `source.space` 一致。
- `result.element_type` 必须与 `source.element_type` 一致；若 `source` 为一维 `i8` byte pool，则允许 `result.element_type` 不同。
- 若 `source.shape` 与 `result.shape` 的元素总数可判定不一致，必须报错；byte pool 场景需满足字节数一致。
- `dma.view` 不要求 `source` 为连续布局，但 `result.stride` 必须与 `result.shape` rank 一致。
- `offsets/shape/stride` operand 数量必须与结果 rank 一致；`offsets` 允许 `!symbol.int<"expr">` 或 `!symbol.iter<"expr">`，`shape/stride` 仍必须是 `!symbol.int<"expr">`。
- `shape` operand 必须与 `result_type.shape` 对齐，`stride` operand 必须与 `result_type.stride` 对齐。
- 对 DSL `view(source, offset, size, stride)` lowering，`result_type.shape` 必须来自 `size`，`result_type.stride` 必须来自 `stride`；不得回退为复用 `source.shape/source.stride` 或其他既有 `Memory` 元信息。
- `offsets` 必须为非负整数；若可静态判定为负值，必须报错。
- 若 `source.shape`、`offsets`、`shape`、`stride` 都可静态判定，则必须执行边界校验：`offset + (size - 1) * stride` 不得超出对应维度的 `source.shape`；byte pool 场景按字节数校验。
- 动态视图信息通过 operand 传入；结果类型中的动态维度只用于描述结果布局的动态性，不替代运行期值来源。
- 合同验收场景下不能只检查“生成了 `dma.view`”；若该结果直接作为函数返回值，则 `func.return` 与函数输出类型必须与 `dma.view.result_type` 完全一致，才能与 `EXPECTED_MEMORY` 比对对齐。

- 返回值：

- 返回新的 `!nn.memory<...>` 结果块；当前 op result 数量固定为 `1`。
- 仅表示视图变换，不改变数据内容。

### `class DmaReshapeOp(source: SSAValue | Operation, shape: Sequence[SSAValue], result_type: NnMemoryType)`

- api：`class DmaReshapeOp(source: SSAValue | Operation, shape: Sequence[SSAValue], result_type: NnMemoryType)`

- 功能说明：

- 表示对 `source` 进行形状重排的视图变换，要求连续布局语义成立。
- 与 `dma.view` 的区别在于：`dma.reshape` 需要由 `result.shape` 重新推导连续行主序 stride。

- 参数：

- `source`：源内存，类型为 `!nn.memory<...>`。
- `shape`：variadic `!symbol.int<"expr">` operand，按 rank 顺序提供结果视图的 shape。
- `result_type`：结果类型，必须为 `!nn.memory<...>`。

- 使用示例：

```python
op = DmaReshapeOp(source, shape, result_type)
```

- 注意事项：

- `result.element_type` 必须与 `source.element_type` 一致。
- `result.space` 必须与 `source.space` 一致。
- `source` 必须可视为连续布局；`result.stride` 必须满足 `result.shape` 的连续行主序校验规则。
- `shape` operand 数量必须与结果 rank 一致，且每个 operand 都必须是 `!symbol.int<"expr">`。
- `result.stride` 不作为输入，而是由 `shape` 和默认连续布局规则推导。
- 含 `min(lhs, rhs)` 的动态尾块维度必须按符号等价关系参与连续布局判断；`min` 表达式的无关空白和乘法因子顺序不得改变 verifier 结论。
- 若 `source.shape` 与 `result.shape` 的元素总数可判定不一致，必须报错。

- 返回值：

- 返回新的 `!nn.memory<...>` 结果块；当前 op result 数量固定为 `1`。
- 仅表示视图变换，不改变数据内容。

### `class DmaCastOp(target: SSAValue | Operation, source: SSAValue | Operation)`

- api：`class DmaCastOp(target: SSAValue | Operation, source: SSAValue | Operation)`

- 功能说明：

- 表示把 `source` 的元素表示显式转换为目标元素类型，并返回新的结果块。
- 该 op 只负责数据表示转换，不负责切片、搬运调度或逐元素算术。

- 参数：

- `source`：待转换的源内存，类型为 `!nn.memory<...>`。
- `result_type`：结果类型，必须为 `!nn.memory<...>`。

- 使用示例：

```python
op = DmaCastOp(source, result_type)
```

- 注意事项：

- `result.shape` 必须与 `source.shape` 一致。
- `result.stride` 必须与 `source.stride` 一致。
- `result.space` 必须与 `source.space` 一致。
- `result.element_type` 表示目标元素类型，可以与 `source.element_type` 不同。
- 若 `result.element_type` 与 `source.element_type` 相同，该 op 语义上允许作为显式 no-op cast，但实现可在后续阶段进行消解。

- 返回值：

- 返回新的 `!nn.memory<...>` 结果块；当前 op result 数量固定为 `1`。
- 当前 op 只定义显式元素类型转换，不定义量化参数、缩放因子、舍入模式或饱和策略；如需这些能力，必须由后续 spec 单独扩展。

## 测试

- 测试文件：[`test/dialect/test_dma.py`](../../test/dialect/test_dma.py)
- 执行命令：`pytest -q test/dialect/test_dma.py`

### 测试目标

- 验证 `dma` op 复用 `NnMemorySpaceAttr` / `NnMemoryType` 时，与 `nn dialect` 的类型规则保持一致。
- 验证 `dma.copy` 的整块搬运约束。
- 验证 `dma.load/slice` 的结果形状、目标空间与标量输入长度约束，并覆盖动态 `!symbol.int<"expr">` operand 表达；`offsets` 允许 `!symbol.iter<"expr">`。
- 验证 `dma.store/deslice` 的源块与目标切片大小匹配约束。
- 验证 `dma.alloc` 结果类型约束与结果数量。
- 验证 `dma.fill` 能将 `const(i32)` / `!symbol.int<"expr">` 真实写入 `i32 memory`，并锁定它不是“空 `dma.alloc` 占位”的替代说法。
- 验证 `dma.free` 的内存类型约束与无返回值语义。
- 验证 `dma.view/reshape` 的元素类型/空间一致性与形状约束，其中 `dma.view` 覆盖动态 `offsets`（允许 `!symbol.iter<"expr">`）、`shape/stride`（`!symbol.int<"expr">`）operand 与边界校验，`dma.reshape` 覆盖动态 `shape` 的 `!symbol.int<"expr">` operand。
- 验证 `dma.subview` 的一维 `i8` backing memory、一维 typed result、元素单位 `offset/size/stride`、space 一致性、size 对齐与静态 byte bounds 边界。
- 验证 `dma.view` 在 DSL helper / 合同链路中不仅要生成 op，还要求返回 `Memory` 类型与 `dma.view.result_type` 一致；当直接 `func.return` 时，`EXPECTED_MEMORY` 比对必须成功。
- 验证默认连续 stride 在符号维度（如 `N` / `M*N` / `min(tile, extent - iter)` / `?`）下的推导、等价判断与退化规则已覆盖。
- 验证 `dma.cast` 只允许改变元素类型，且保持 `shape/stride/space` 不变。
- 验证当前阶段对 stride 的限制会在 verifier 阶段明确报错。
- 验证 `dma` 的布局/索引类标量输入以 `!symbol.int<"expr">` 为主，`offsets` 允许 `!symbol.iter<"expr">`，并拒绝 builtin `index`、浮点或其他非 symbol 标量类型；同时验证 `dma.fill.value` 只允许 builtin `i32` 与 `!symbol.int<"expr">` 这两个当前公开例外（包含拒绝未定义的其他 scalar family）。
- 验证 mixed add 使用 `scalar -> memory` 原语时，被填充的 temporary memory 必须在下游 IR 中有真实 use；`dma.alloc` alone 或 `dma.alloc + dma.fill` 但无消费都不构成通过口径。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DMA-001 | 边界/异常 | `dma` op 类型边界 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dma_requires_nn_memory_type`。 | “`dma` op 类型边界”场景按公开错误语义失败或被拒绝。 | `test_dma_requires_nn_memory_type` |
| TC-DMA-002 | 内存/DMA | `dma.copy` 合法路径 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_copy_verify_success`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`dma.copy` 合法路径”场景。 | `test_dma_copy_verify_success` |
| TC-DMA-003 | 边界/异常 | `dma.copy` 形状不匹配 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dma_copy_shape_mismatch`。 | “`dma.copy` 形状不匹配”场景按公开错误语义失败或被拒绝。 | `test_dma_copy_shape_mismatch` |
| TC-DMA-004 | 边界/异常 | `dma.load` 结果空间约束 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dma_load_result_space_mismatch`。 | “`dma.load` 结果空间约束”场景按公开错误语义失败或被拒绝。 | `test_dma_load_result_space_mismatch` |
| TC-DMA-005 | 边界/异常 | `dma.slice` 索引长度约束 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dma_slice_rank_mismatch`。 | “`dma.slice` 索引长度约束”场景按公开错误语义失败或被拒绝。 | `test_dma_slice_rank_mismatch` |
| TC-DMA-006 | 边界/异常 | `dma.slice` stride 限制 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dma_slice_non_unit_stride_rejected`。 | “`dma.slice` stride 限制”场景按公开错误语义失败或被拒绝。 | `test_dma_slice_non_unit_stride_rejected` |
| TC-DMA-007 | 边界/异常 | `dma.store` 块大小约束 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dma_store_size_mismatch`。 | “`dma.store` 块大小约束”场景按公开错误语义失败或被拒绝。 | `test_dma_store_size_mismatch` |
| TC-DMA-008 | 内存/DMA | `dma.deslice` 合法路径 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_deslice_verify_success`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`dma.deslice` 合法路径”场景。 | `test_dma_deslice_verify_success` |
| TC-DMA-009 | pass 改写 | `nn dialect` verifier 透传 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_dma_nn_memory_type_verifier_passthrough`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`nn dialect` verifier 透传”场景。 | `test_dma_nn_memory_type_verifier_passthrough` |
| TC-DMA-010 | 内存/DMA | 动态 offsets/sizes/strides | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_dynamic_symbol_int_operands_valid`。 | 内存类型、布局、搬运结果或 verifier 行为体现“动态 offsets/sizes/strides”场景。 | `test_dma_dynamic_symbol_int_operands_valid` |
| TC-DMA-058 | 内存/DMA | `dma.load` offsets 接受 `symbol.iter` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_load_accepts_symbol_iter_offset`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`dma.load` offsets 接受 `symbol.iter`”场景。 | `test_dma_load_accepts_symbol_iter_offset` |
| TC-DMA-011 | 内存/DMA | `dma.cast` 合法路径 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_cast_verify_success`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`dma.cast` 合法路径”场景。 | `test_dma_cast_verify_success` |
| TC-DMA-012 | 边界/异常 | `dma.cast` 结果约束 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dma_cast_layout_or_space_mismatch`。 | “`dma.cast` 结果约束”场景按公开错误语义失败或被拒绝。 | `test_dma_cast_layout_or_space_mismatch` |
| TC-DMA-013 | 内存/DMA | `dma.alloc` 合法路径 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_alloc_verify_success`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`dma.alloc` 合法路径”场景。 | `test_dma_alloc_verify_success` |
| TC-DMA-014 | 边界/异常 | `dma.view` 约束 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dma_view_type_or_space_mismatch`。 | “`dma.view` 约束”场景按公开错误语义失败或被拒绝。 | `test_dma_view_type_or_space_mismatch` |
| TC-DMA-015 | 边界/异常 | `dma.view` numel 一致性 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dma_view_numel_mismatch`。 | “`dma.view` numel 一致性”场景按公开错误语义失败或被拒绝。 | `test_dma_view_numel_mismatch` |
| TC-DMA-016 | 边界/异常 | `dma.reshape` 连续约束 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dma_reshape_requires_contiguous`。 | “`dma.reshape` 连续约束”场景按公开错误语义失败或被拒绝。 | `test_dma_reshape_requires_contiguous` |
| TC-DMA-017 | 内存/DMA | `dma.reshape` 动态形状连续 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_reshape_allows_dynamic_symbol_int_shape_operands`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`dma.reshape` 动态形状连续”场景。 | `test_dma_reshape_allows_dynamic_symbol_int_shape_operands` |
| TC-DMA-018 | 边界/异常 | `dma.reshape` 元素总数不一致 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dma_reshape_numel_mismatch`。 | “`dma.reshape` 元素总数不一致”场景按公开错误语义失败或被拒绝。 | `test_dma_reshape_numel_mismatch` |
| TC-DMA-018A | 内存/DMA | `dma.reshape` 接受 `min(...)` 符号连续 stride | 准备含 `min(tile, extent - iter)` shape/stride 的 `DmaReshapeOp`。 | 运行 `test_dma_reshape_accepts_min_symbolic_contiguous_source_stride`。 | verifier 接受等价连续 stride，不因 `min` 表达式文本形式失败。 | `test_dma_reshape_accepts_min_symbolic_contiguous_source_stride` |
| TC-DMA-019 | 内存/DMA | `dma.view` 动态布局输入 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_view_dynamic_symbol_int_layout_operands_valid`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`dma.view` 动态布局输入”场景。 | `test_dma_view_dynamic_symbol_int_layout_operands_valid` |
| TC-DMA-019A | 边界/异常 | `dma.view` offsets 边界 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dma_view_rejects_invalid_offsets_or_bounds`。 | “`dma.view` offsets 边界”场景按公开错误语义失败或被拒绝。 | `test_dma_view_rejects_invalid_offsets_or_bounds` |
| TC-DMA-019B | 内存/DMA | `dma.view` 显式 stride 布局 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_view_accepts_matching_numel_subset_with_explicit_stride`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`dma.view` 显式 stride 布局”场景。 | `test_dma_view_accepts_matching_numel_subset_with_explicit_stride` |
| TC-DMA-019D | 内存/DMA | `dma.view` byte pool typed view | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_view_byte_pool_typed_view`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`dma.view` byte pool typed view”场景。 | `test_dma_view_byte_pool_typed_view` |
| TC-DMA-019E | 内存/DMA | `dma.subview` byte backing typed result | 准备一维 `i8` backing memory、`!symbol.int` offset/size/stride 与一维 typed result。 | 运行 `test_dma_subview_byte_pool_typed_result_valid`。 | `dma.subview` verifier 接受合法 typed subview。 | `test_dma_subview_byte_pool_typed_result_valid` |
| TC-DMA-019F | 边界/异常 | `dma.subview` 公开 verifier 边界 | 准备非 i8 source、二维 result、space mismatch、size mismatch 与 byte bounds 越界输入。 | 运行 `test_dma_subview_rejects_invalid_contract_edges`。 | `dma.subview` 按公开错误语义拒绝非法输入。 | `test_dma_subview_rejects_invalid_contract_edges` |
| TC-DMA-019C | 执行结果 | `dma.view` 合同返回类型对齐 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 [`test/dsl/ast/test_mlir_gen.py`](../../test/dsl/ast/test_mlir_gen.py)。 | 命令返回码、输出、执行结果或状态变更体现“`dma.view` 合同返回类型对齐”场景。 | [`test/dsl/ast/test_mlir_gen.py`](../../test/dsl/ast/test_mlir_gen.py) |
| TC-DMA-020 | 内存/DMA | `dma.alloc` 动态形状输入 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_alloc_dynamic_symbol_int_shape_operands_valid`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`dma.alloc` 动态形状输入”场景。 | `test_dma_alloc_dynamic_symbol_int_shape_operands_valid` |
| TC-DMA-021 | 解析/打印 | 动态 shape round-trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_dma_dynamic_symbol_int_parse_print_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_dma_dynamic_symbol_int_parse_print_round_trip` |
| TC-DMA-022 | 边界/异常 | 非法标量类型拒绝 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dma_rejects_non_symbol_int_scalar_operands`。 | “非法标量类型拒绝”场景按公开错误语义失败或被拒绝。 | `test_dma_rejects_non_symbol_int_scalar_operands` |
| TC-DMA-023 | 边界/异常 | `dma.free` 释放内存 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dma_free_requires_nn_memory_type`。 | “`dma.free` 释放内存”场景按公开错误语义失败或被拒绝。 | `test_dma_free_requires_nn_memory_type` |
| TC-DMA-024 | 内存/DMA | `dma.fill` 物化 `const(i32)` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 构造并校验 `dma.fill` | 内存类型、布局、搬运结果或 verifier 行为体现“`dma.fill` 物化 `const(i32)`”场景。 | test/dialect/test_dma.py::test_dma_fill_accepts_builtin_i32_scalar_operand |
| TC-DMA-025 | 内存/DMA | `dma.fill` 物化 `symbol.int` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 构造并校验 `dma.fill` | 内存类型、布局、搬运结果或 verifier 行为体现“`dma.fill` 物化 `symbol.int`”场景。 | test/dialect/test_dma.py::test_dma_fill_accepts_symbol_int_scalar_operand |
| TC-DMA-026 | 内存/DMA | `dma.fill` 类型边界 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 构造并校验 `dma.fill` | 内存类型、布局、搬运结果或 verifier 行为体现“`dma.fill` 类型边界”场景。 | test/dialect/test_dma.py::test_dma_fill_rejects_non_i32_target_or_unsupported_scalar |
| TC-DMA-027 | 内存/DMA | mixed add 临时 memory 真实消费 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 检查 lower 后 IR | 内存类型、布局、搬运结果或 verifier 行为体现“mixed add 临时 memory 真实消费”场景。 | test/passes/lowering/nn_lowering/test_element_binary_add.py::test_lower_add_mixed_scalar_uses_dma_fill |
| TC-DMA-059 | 边界/异常 | `dma.alloc/broadcast/transpose/view` 公开 verifier 边界矩阵 | 准备公开 op 构造入口、动态 shape、broadcast 源/目标类型、transpose perm/target 与 byte-pool view 类型组合。 | 运行 `test_dma_public_verifier_boundary_matrix`。 | 动态 shape、broadcast rank/type/space、transpose perm/layout/type/space、transfer rank、byte-pool view element size 与动态边界按公开错误语义通过或稳定拒绝。 | `test_dma_public_verifier_boundary_matrix` |
