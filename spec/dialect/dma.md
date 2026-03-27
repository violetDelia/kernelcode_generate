# dma.md

## 功能简介

用于定义 `dma dialect` 的稳定方言语义，描述 `dma.alloc`、`dma.free`、`dma.copy`、`dma.load`、`dma.store`、`dma.slice`、`dma.deslice`、`dma.view`、`dma.reshape`、`dma.cast` 如何表示内存对象之间的数据搬运与布局转换，包括整块搬运、切片读取、切片回写、跨空间迁移、视图变换与显式数据转换，并支持动态 shape 的表达。该方言不单独定义 memory type / memory space，而是统一复用 `nn dialect` 中的 `NnMemoryType` 与 `NnMemorySpaceAttr`。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/dialect/dma.md`](../../spec/dialect/dma.md)
- `test`：[`test/dialect/test_dma_dialect.py`](../../test/dialect/test_dma_dialect.py)
- `功能实现`：[`kernel_gen/dialect/dma.py`](../../kernel_gen/dialect/dma.py)

## 依赖

- [`kernel_gen/dialect/dma.py`](../../kernel_gen/dialect/dma.py)：`dma dialect` 的方言实现入口。
- [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)：提供 `NnMemoryType` 与 `NnMemorySpaceAttr`。
- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：定义被 `dma dialect` 复用的 memory type / memory space 语义。
- [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)：定义 `!symbol.int<"expr">` 标量值语义，供 `dma` 标量输入统一复用。
- [`spec/operation/dma.md`](../../spec/operation/dma.md)：定义高层 `alloc/free/copy/load/store/slice/deslice/cast` API 的分层语义。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：说明高层 `Memory` 概念与 `shape/stride/dtype/space` 元信息来源。

## 目标

- 为项目提供统一的数据搬运、布局转换与显式数据转换方言层表示。
- 让整块拷贝、切片读取、切片回写、跨空间搬运与显式数据转换在 IR 中有明确 op 语义。
- 保留 `shape/stride/offsets/sizes/strides` 等搬运元信息，覆盖静态与动态场景，并统一将这些运行期标量输入建模为 `!symbol.int<"expr">` SSA value。
- 为后续 lowering 到 `tensor.extract_slice`、`tensor.insert_slice`、`memref.copy`、后端 DMA 指令或 runtime API 提供稳定中间层。
- 参考 `memref.subview` / `memref.reinterpret_cast` 的设计习惯，将动态布局信息建模为显式 SSA 标量操作数，而不是仅放在 attribute 中；当前项目统一使用 `!symbol.int<"expr">` 承载这些整数标量输入。

## 限制与边界

- `dma dialect` 不单独维护 memory type / memory space，所有相关 operand / result 类型统一复用 `NnMemoryType` 与 `NnMemorySpaceAttr`。
- 本文件只定义方言层的数据搬运、布局转换与显式数据转换语义，不负责真实 DMA 硬件调度、流水线编排、带宽建模、同步原语、事件、barrier 或 async token 设计。
- 本文件不负责广播、逐元素算术、比较等张量计算语义，也不负责自动求解 `offsets/sizes/strides` 或自动推导最优搬运策略。
- 当前方言范围包含 `dma.alloc`、`dma.free`、`dma.copy`、`dma.load`、`dma.store`、`dma.slice`、`dma.deslice`、`dma.view`、`dma.reshape`、`dma.cast`。
- 除 `dma.cast` 外，其他搬运 op 不改变元素值语义，只改变数据所在的逻辑位置、切片范围、布局表达或空间；同一个 op 不应同时承担计算和搬运语义。
- 本文件中的“转换”包含两类：布局、切片视图或空间层面的转换，以及通过 `dma.cast` 表达的显式元素类型转换；不包括广播、归约或通用数值计算。

### 分层约束

- `spec/operation/dma.md` 负责高层 API 语义；`dma dialect` 负责对应 IR 语义。
- 若高层 `Memory` 进入 IR，仍必须落到 `NnMemoryType` / `NnMemorySpaceAttr`，不得在 `dma dialect` 内再定义一套分配专用类型。
- `dma.view`、`dma.reshape` 属于方言层视图/布局变换 op，不属于 `operation/dma` 的高层 API。

### 通用约束

- 所有参与搬运或转换的 `source`、`target`、`result` 必须是 `!nn.memory<...>`。
- `dma.alloc` 仅产生结果内存，结果类型必须为 `!nn.memory<...>`。
- `dma.free` 仅接受待释放的内存 operand，不产生结果。
- `dma.view/reshape` 必须保证 `result.element_type` 与 `source.element_type` 一致，`result.space` 与 `source.space` 一致。
- 对 `dma.copy/load/store/slice/deslice`，相关 `element_type` 必须一致，不允许隐式类型转换。
- 对 `dma.cast`，只允许 `element_type` 发生显式变化；`shape/stride/space` 必须保持一致。
- `shape/stride` 的 rank 必须与相关 `offsets/sizes/strides` 列表长度一致。
- `offsets`、`sizes`、`strides`、动态 `shape`、动态 `stride` 必须建模为显式 `!symbol.int<"expr">` SSA 操作数列表；不得只靠 `StringAttr("?")`、`ArrayAttr` 或其他 attribute 独立表达运行期值。
- 所有 index-like 标量 operand 仅接受 `!symbol.int<"expr">` SSA value；禁止直接使用 Python `int/float` 或 builtin 数值类型替代，静态常量必须先 materialize 为 `!symbol.int<"expr">`。
- `!nn.memory<...>` 类型仍负责承载 rank、元素类型、内存空间以及可静态判定的布局信息；凡是运行期才确定的布局值，必须由 op operand 传入。
- 若实现保留静态维度或静态 stride 在类型中，assembly 中的静态值也应允许通过 `!symbol.int<"1">` 这类 symbol 常量值、或等价 materialize 后的 `!symbol.int<"expr">` SSA value 显式传入 operand，保证“布局参数来源统一为 operand”。
- `dma.load/store/slice/deslice` 的 `offsets/sizes/strides` 必须为 variadic `!symbol.int<"expr">` operand。
- `dma.view` 中与动态布局相关的 `shape/stride` 元信息必须通过 `!symbol.int<"expr">` operand 显式传入；不得仅依赖结果类型里的符号维度推断。
- `dma.reshape` 仅接受动态 `shape` operand，且这些 operand 必须为 `!symbol.int<"expr">`；结果 `stride` 按 `shape` 的默认连续布局语义生成。
- `dma.alloc` 仅接受动态 `shape` operand，且这些 operand 必须为 `!symbol.int<"expr">`；`stride` 不作为输入，而是按默认连续布局语义生成。
- `strides` 当前每一维仍限制为单位步长语义，但该约束应体现在 operand 校验阶段，而不是要求使用 `IntAttr(1)` attribute。
- `sizes` 中每一维必须具有正整数语义，不允许负值；若 `!symbol.int<"expr">` 不能静态证明为正值，则至少要拒绝 `!symbol.int<"0">` 与可静态判定的负值。
- 若 op 带有目标空间 attribute，则其值必须与结果 type 或目标 type 的 `space` 一致。

#### 默认连续 stride 推导（符号维度）

- 当 `shape` 中包含 `StringAttr` 时，默认连续 stride 仍按从右到左的累计乘积推导；单个符号如 `N` 直接参与乘积，多维组合可形成 `M*N` 等字符串表达。
- 若维度为 `StringAttr("?")` 或包含 `?` 的表达式，视为未知：该维度及其左侧更高维的默认 stride 统一退化为 `StringAttr("?")`，右侧维度仍按既有规则生成（末维为 `1`）。
- 该规则仅用于 `dma.alloc` / `dma.reshape` 的默认连续 stride 推导与 verifier 校验，不替代显式 `!symbol.int<"expr">` SSA operand 建模；`offsets/sizes/strides` 仍必须通过 `!symbol.int<"expr">` SSA operand 传入。

### Parse/Print 与 Verifier 约束

- 任意被 `dma` op 引用的 `!nn.memory<...>` 与 `#nn.space<...>` 文本都必须支持 parse 后再 print 回稳定文本。
- 任意合法 `dma.copy/load/store/slice/deslice/cast` 文本都必须支持 parse 后进入 verifier。
- assembly 缺失必要字段时，必须在 parse 阶段失败。
- `NnMemorySpaceAttr` 非法值、`NnMemoryType.shape` 与 `stride` rank 不一致等类型错误，必须按 `nn dialect` 规则报错。
- `dma.copy` 中 `source/target` 的 `shape/stride/element_type` 不一致必须报错。
- `dma.alloc` 的动态 `shape` operand 与结果 rank 不匹配时必须报错；任一 `shape` operand 不是 `!symbol.int<"expr">` 时必须报错；结果类型非法必须报错。
- `dma.free` 的 operand 不是 `!nn.memory<...>` 时必须报错。
- `dma.load/slice` 中 `offsets/sizes/strides` 长度与输入 rank 不一致必须报错；任一相关 operand 不是 `!symbol.int<"expr">` 时必须报错。
- `dma.store/deslice` 中 `source.shape` 与切片目标大小不一致必须报错。
- `dma.view/reshape` 中 `source/result` 的 `element_type/space` 不一致必须报错；可判定的 `numel` 不一致必须报错。
- `dma.view` 的动态 `shape/stride` operand 数量与 rank 不一致必须报错；任一相关 operand 不是 `!symbol.int<"expr">` 时必须报错；`dma.reshape` 的动态 `shape` operand 数量与 rank 不一致必须报错，且其 operand 必须为 `!symbol.int<"expr">`。
- `dma.view` 的 `result.stride` rank 与 `result.shape` 不一致必须报错；`dma.reshape` 的 `result.stride` 非连续行主序必须报错。
- `dma.cast` 中 `source/result` 的 `shape/stride/space` 不一致必须报错。
- `strides` 当前仅允许单位步长语义；若当前实现限制 stride 为 1，则 `stride != 1` 的切片搬运必须显式报错，不得 silently 接受。
- `dma` 标量输入当前统一为 `!symbol.int<"expr">`；parse/print 不得再使用 builtin `index` 作为这些 operand 的公开文本语义。

## 公开接口

### 方言公开构件

功能说明：

- `dma dialect` 的公开构件由两部分组成：
  - 复用 `nn dialect` 的 `NnMemoryType` 与 `NnMemorySpaceAttr`
  - 提供 `dma.alloc`、`dma.free`、`dma.copy`、`dma.load`、`dma.store`、`dma.slice`、`dma.deslice`、`dma.view`、`dma.reshape`、`dma.cast` 十个公开 op

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.dialect.dma import (
    DmaAllocOp,
    DmaCastOp,
    DmaCopyOp,
    DmaDesliceOp,
    DmaFreeOp,
    DmaLoadOp,
    DmaReshapeOp,
    DmaSliceOp,
    DmaStoreOp,
    DmaViewOp,
)
from kernel_gen.dialect.nn import NnMemorySpaceAttr
```

注意事项：

- `dma.free` 只负责释放指定的内存对象，不返回新 `!nn.memory<...>`。
- memory type / memory space 必须始终沿用 `nn dialect` 口径。
- 动态布局相关信息统一走 operand，不再把运行期 `offset/size/stride/shape` 只放在 attribute 中；但 `dma.alloc` 和 `dma.reshape` 的 `stride` 都由默认连续布局规则生成，不单独接收 operand。

返回与限制：

- 对外暴露 `dma` 相关 op（含 alloc/view/reshape）以及对 `nn dialect` memory 类型体系的复用约束。

### `dma.alloc`

功能说明：

- 表示显式的内存对象创建，仅生成结果 `!nn.memory<...>`。
- 不承担数据搬运或初始化语义。

参数说明：

- `dynamic_shape`：variadic `!symbol.int<"expr">` operand，按 rank 顺序提供运行期 shape。
- `result_type`：结果类型，必须为 `!nn.memory<...>`。

使用示例：

```python
op = DmaAllocOp(dynamic_shape, result_type)
```

注意事项：

- `result_type` 中的 `shape/stride/element_type/space` 必须完整且合法。
- 若结果布局含运行期 shape 信息，则对应值必须由 `dynamic_shape` operand 提供，且每个 operand 都必须是 `!symbol.int<"expr">`。
- `dynamic_shape` 的长度必须与结果 rank 一致。
- 结果 `stride` 不作为输入，由 `result_type.shape` 与默认连续布局规则共同确定。
- 当前版本不额外定义 base offset；`dma.alloc` 只负责产生新的 memory 对象。

返回与限制：

- 返回新的 `!nn.memory<...>`；当前 op result 数量固定为 `1`。
- 仅表达“存在一个内存对象”的语义，不负责初始化或填充值。

### `dma.free`

功能说明：

- 表示显式释放内存对象，结束该 `!nn.memory<...>` 的生命周期。
- 仅表达释放语义，不负责数据搬运或数据清零。

参数说明：

- `source`：待释放的内存对象，类型为 `!nn.memory<...>`。

使用示例：

```python
op = DmaFreeOp(source)
```

注意事项：

- `source` 必须为 `!nn.memory<...>`；其他类型必须在 verifier 阶段报错。
- `dma.free` 不改变 `source` 的类型信息，也不返回新的内存对象。

返回与限制：

- 返回类型为无返回值；当前 op result 数量固定为 `0`。
- 语义上通过 side effect 表达释放行为，不产生新的 `!nn.memory<...>`。

### `dma.reshape`

功能说明：

- 表示对 `source` 进行形状重排的视图变换，要求连续布局语义成立。
- 与 `dma.view` 的区别在于：`dma.reshape` 需要由 `result.shape` 重新推导连续行主序 stride。

参数说明：

- `source`：源内存，类型为 `!nn.memory<...>`。
- `shape`：variadic `!symbol.int<"expr">` operand，按 rank 顺序提供结果视图的 shape。
- `result_type`：结果类型，必须为 `!nn.memory<...>`。

使用示例：

```python
op = DmaReshapeOp(source, shape, result_type)
```

注意事项：

- `result.element_type` 必须与 `source.element_type` 一致。
- `result.space` 必须与 `source.space` 一致。
- `source` 必须可视为连续布局；`result.stride` 必须满足 `result.shape` 的连续行主序校验规则。
- `shape` operand 数量必须与结果 rank 一致，且每个 operand 都必须是 `!symbol.int<"expr">`。
- `result.stride` 不作为输入，而是由 `shape` 和默认连续布局规则推导。
- 若 `source.shape` 与 `result.shape` 的元素总数可判定不一致，必须报错。

返回与限制：

- 返回新的 `!nn.memory<...>` 结果块；当前 op result 数量固定为 `1`。
- 仅表示视图变换，不改变数据内容。

### `dma.view`

功能说明：

- 表示对 `source` 的视图变换，仅调整 `shape/stride` 元信息。
- 用于表达不发生搬运的数据视图重解释。

参数说明：

- `source`：源内存，类型为 `!nn.memory<...>`。
- `shape`：variadic `!symbol.int<"expr">` operand，按 rank 顺序提供结果视图的 shape。
- `stride`：variadic `!symbol.int<"expr">` operand，按 rank 顺序提供结果视图的 stride。
- `result_type`：结果类型，必须为 `!nn.memory<...>`。

使用示例：

```python
op = DmaViewOp(source, shape, stride, result_type)
```

注意事项：

- `result.element_type` 必须与 `source.element_type` 一致。
- `result.space` 必须与 `source.space` 一致。
- 若 `source.shape` 与 `result.shape` 的元素总数可判定不一致，必须报错。
- `dma.view` 不要求 `source` 为连续布局，但 `result.stride` 必须与 `result.shape` rank 一致。
- `shape` 与 `stride` operand 数量必须与结果 rank 一致，且每个 operand 都必须是 `!symbol.int<"expr">`。
- 动态视图信息通过 operand 传入；结果类型中的动态维度只用于描述结果布局的动态性，不替代运行期值来源。

返回与限制：

- 返回新的 `!nn.memory<...>` 结果块；当前 op result 数量固定为 `1`。
- 仅表示视图变换，不改变数据内容。

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
- `offsets`：variadic `!symbol.int<"expr">` operand，长度必须与 `source.rank` 一致；每一维表示对应维度的起始索引。
- `sizes`：variadic `!symbol.int<"expr">` operand，长度必须与 `source.rank` 一致；每一维表示对应维度的切片大小。
- `strides`：variadic `!symbol.int<"expr">` operand，长度必须与 `source.rank` 一致；每一维表示对应维度的切片步长，当前每一维必须具有单位步长语义。
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
- `offsets/sizes/strides` 必须全部通过 operand 提供；若是静态常量，也应先 materialize 为 `!symbol.int<"1">` 这类 symbol 常量值或等价的 `!symbol.int<"expr">` SSA value 后传入。

返回与限制：

- 返回新的 `!nn.memory<...>` 结果块。
- 当前支持 SSA 动态 `!symbol.int<"expr">` 标量输入；但仍不支持非单位 stride 语义。

### `dma.store`

功能说明：

- 表示把 `source` 块写回 `target` 的某个区域。
- 常用于从 `shared` 或 `local` 写回 `global`。

参数说明：

- `source`：待写回的源块，类型为 `!nn.memory<...>`。
- `target`：被更新的目标内存，类型为 `!nn.memory<...>`。
- `offsets`：variadic `!symbol.int<"expr">` operand；每一维表示 `target` 对应维度的写回起始索引，长度必须与 `target.rank` 一致。
- `sizes`：variadic `!symbol.int<"expr">` operand；每一维表示写回区域在 `target` 对应维度的大小，长度必须与 `target.rank` 一致。
- `strides`：variadic `!symbol.int<"expr">` operand；每一维表示 `target` 对应维度的写回步长，长度必须与 `target.rank` 一致，当前每一维必须具有单位步长语义。

使用示例：

```python
op = DmaStoreOp(source, target, offsets, sizes, strides)
```

注意事项：

- `source.shape` 必须与 `sizes` 对应的切片形状一致。
- `source.element_type` 必须与 `target.element_type` 一致。
- `offsets/sizes/strides` 长度必须与 `target.rank` 一致，且每个 operand 都必须是 `!symbol.int<"expr">`。
- `offsets/sizes/strides` 必须全部通过 operand 提供。

返回与限制：

- 返回类型为无返回值；当前 op result 数量固定为 `0`。
- 语义上通过 side effect 表达对 `target` 指定切片区域的写回，不返回新的 `!nn.memory<...>`。

### `dma.slice`

功能说明：

- 表示从 `source` 中抽取一个切片块，语义上接近切片读取。
- 它与 `dma.load` 一样返回新结果块，但更强调源区域裁剪而非整块空间搬运。

参数说明：

- `source`：源内存，类型为 `!nn.memory<...>`。
- `offsets`：variadic `!symbol.int<"expr">` operand；每一维表示对应维度的起始索引，长度必须与 `source.rank` 一致。
- `sizes`：variadic `!symbol.int<"expr">` operand；每一维表示对应维度的切片大小，长度必须与 `source.rank` 一致。
- `strides`：variadic `!symbol.int<"expr">` operand；每一维表示对应维度的切片步长，长度必须与 `source.rank` 一致，当前每一维必须具有单位步长语义。
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
- `offsets/sizes/strides` 必须全部通过 `!symbol.int<"expr">` operand 提供。

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
- `offsets`：variadic `!symbol.int<"expr">` operand；每一维表示 `target` 对应维度的回写起始索引，长度必须与 `target.rank` 一致。
- `sizes`：variadic `!symbol.int<"expr">` operand；每一维表示回写区域在 `target` 对应维度的大小，长度必须与 `target.rank` 一致。
- `strides`：variadic `!symbol.int<"expr">` operand；每一维表示 `target` 对应维度的回写步长，长度必须与 `target.rank` 一致，当前每一维必须具有单位步长语义。
- `result_type`：结果类型，必须为 `!nn.memory<...>`，且必须与 `target` 类型一致。

使用示例：

```python
op = DmaDesliceOp(source, target, offsets, sizes, strides, result_type)
```

注意事项：

- `source.shape` 必须与 `sizes` 对应的切片形状一致。
- `source.element_type` 必须与 `target.element_type` 一致。
- 当前阶段必须限制 `strides` 为全 1；出现其他值时 verifier 必须报错。
- `offsets/sizes/strides` 必须全部通过 `!symbol.int<"expr">` operand 提供。

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
- 验证 `dma.load/slice` 的结果形状、目标空间与标量输入长度约束，并覆盖动态 `!symbol.int<"expr">` operand 表达。
- 验证 `dma.store/deslice` 的源块与目标切片大小匹配约束。
- 验证 `dma.alloc` 结果类型约束与结果数量。
- 验证 `dma.free` 的内存类型约束与无返回值语义。
- 验证 `dma.view/reshape` 的元素类型/空间一致性与形状约束，其中 `dma.view` 覆盖动态 `shape/stride` 的 `!symbol.int<"expr">` operand，`dma.reshape` 覆盖动态 `shape` 的 `!symbol.int<"expr">` operand。
- 验证默认连续 stride 在符号维度（如 `N` / `M*N` / `?`）下的推导与退化规则已覆盖。
- 验证 `dma.cast` 只允许改变元素类型，且保持 `shape/stride/space` 不变。
- 验证当前阶段对 stride 的限制会在 verifier 阶段明确报错。
- 验证所有受影响的 dma 标量输入统一为 `!symbol.int<"expr">`，并拒绝 builtin `index`、浮点或其他非 symbol 标量类型（包含未 materialize 的 Python 数值输入）。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DMA-001 | 类型复用 | `dma` op 类型边界 | 已提供 `NnMemoryType` 与非 `NnMemoryType` 候选类型 | 构造 `dma` op | 仅 `NnMemoryType` 合法 | `test_dma_requires_nn_memory_type` |
| TC-DMA-002 | 整块拷贝 | `dma.copy` 合法路径 | `source/target` 的 `shape/stride/element_type` 完全一致 | 构造并校验 `dma.copy` | verifier 通过 | `test_dma_copy_verify_success` |
| TC-DMA-003 | 整块拷贝 | `dma.copy` 形状不匹配 | `source.shape != target.shape` | 构造并校验 `dma.copy` | verifier 报错 | `test_dma_copy_shape_mismatch` |
| TC-DMA-004 | 切片读取 | `dma.load` 结果空间约束 | `result.space` 与 op `space` 不一致 | 构造并校验 `dma.load` | verifier 报错 | `test_dma_load_result_space_mismatch` |
| TC-DMA-005 | 切片读取 | `dma.slice` 索引长度约束 | `offsets/sizes/strides` 长度与 rank 不一致 | 构造并校验 `dma.slice` | verifier 报错 | `test_dma_slice_rank_mismatch` |
| TC-DMA-006 | 切片读取 | `dma.slice` stride 限制 | `strides` operand 中包含非单位步长值 | 构造并校验 `dma.slice` | verifier 报错 | `test_dma_slice_non_unit_stride_rejected` |
| TC-DMA-007 | 切片回写 | `dma.store` 块大小约束 | `source.shape` 与目标切片大小不一致 | 构造并校验 `dma.store` | verifier 报错 | `test_dma_store_size_mismatch` |
| TC-DMA-008 | 切片回写 | `dma.deslice` 合法路径 | `source.shape` 与目标切片大小一致 | 构造并校验 `dma.deslice` | verifier 通过 | `test_dma_deslice_verify_success` |
| TC-DMA-009 | 类型校验 | `nn dialect` verifier 透传 | `space` 非法或 `shape/stride` rank 不一致 | 构造引用非法 `!nn.memory<...>` 的 `dma` op | 按 `nn dialect` 规则报错 | `test_dma_nn_memory_type_verifier_passthrough` |
| TC-DMA-010 | 标量输入 | 动态 offsets/sizes/strides | `offsets/sizes/strides` 由 SSA `!symbol.int<"expr">` operand 提供 | 构造并校验切片类 op | verifier 通过 | `test_dma_dynamic_symbol_int_operands_valid` |
| TC-DMA-011 | 数据转换 | `dma.cast` 合法路径 | `source/result` 的 `shape/stride/space` 一致，仅元素类型不同 | 构造并校验 `dma.cast` | verifier 通过 | `test_dma_cast_verify_success` |
| TC-DMA-012 | 数据转换 | `dma.cast` 结果约束 | `source/result` 的 `shape` 或 `stride` 或 `space` 不一致 | 构造并校验 `dma.cast` | verifier 报错 | `test_dma_cast_layout_or_space_mismatch` |
| TC-DMA-013 | 分配 | `dma.alloc` 合法路径 | `result_type` 为合法 `!nn.memory<...>` | 构造并校验 `dma.alloc` | verifier 通过 | `test_dma_alloc_verify_success` |
| TC-DMA-014 | 视图 | `dma.view` 约束 | `result.element_type` 或 `result.space` 与 `source` 不一致 | 构造并校验 `dma.view` | verifier 报错 | `test_dma_view_type_or_space_mismatch` |
| TC-DMA-015 | 视图 | `dma.view` 形状一致性 | `source/result` 可判定的元素总数不一致 | 构造并校验 `dma.view` | verifier 报错 | `test_dma_view_numel_mismatch` |
| TC-DMA-016 | 变形 | `dma.reshape` 连续约束 | `source` 非连续布局，无法合法 reshape 为连续结果 | 构造并校验 `dma.reshape` | verifier 报错 | `test_dma_reshape_requires_contiguous` |
| TC-DMA-017 | 变形 | `dma.reshape` 动态形状连续 | `shape` 由 SSA `!symbol.int<"expr">` operand 提供，符号维度默认 stride 规则（如 `N`/`M*N`/`?`）生效 | 构造并校验 `dma.reshape` | verifier 通过 | `test_dma_reshape_allows_dynamic_symbol_int_shape_operands` |
| TC-DMA-018 | 变形 | `dma.reshape` 元素总数不一致 | `shape` 由 SSA operand 提供，且与 `source` 可判定的元素总数不一致 | 构造并校验 `dma.reshape` | verifier 报错 | `test_dma_reshape_numel_mismatch` |
| TC-DMA-019 | 视图 | `dma.view` 动态布局输入 | `shape/stride` 由 SSA `!symbol.int<"expr">` operand 提供，结果 rank 匹配 | 构造并校验 `dma.view` | verifier 通过 | `test_dma_view_dynamic_symbol_int_layout_operands_valid` |
| TC-DMA-020 | 分配 | `dma.alloc` 动态形状输入 | `dynamic_shape` 由 SSA `!symbol.int<"expr">` operand 提供，长度与 rank 一致，符号维度默认 stride 规则（如 `N`/`M*N`/`?`）生效 | 构造并校验 `dma.alloc` | verifier 通过 | `test_dma_alloc_dynamic_symbol_int_shape_operands_valid` |
| TC-DMA-021 | 解析/打印 | 动态 shape round-trip | 包含 `dma.alloc/view/load/store/slice/deslice/reshape/cast` 的 SSA `!symbol.int<"expr">` operand 文本 | parse/print | 与输入文本一致 | `test_dma_dynamic_symbol_int_parse_print_round_trip` |
| TC-DMA-022 | 标量输入 | 非 symbol.int 非法 | 任一受影响标量输入为 builtin `index` 或其他非 symbol 标量类型 | 构造并校验 `dma` op | verifier 报错 | `test_dma_rejects_non_symbol_int_scalar_operands` |
| TC-DMA-023 | 生命周期 | `dma.free` 释放内存 | `source` 为 `!nn.memory<...>` 或非该类型 | 构造并校验 `dma.free` | 非内存类型报错 | `test_dma_free_requires_nn_memory_type` |
