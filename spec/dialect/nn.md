# nn.md

## 功能简介

`nn dialect` 定义方言层稳定接口，负责建模 memory space、memory type，以及逐元素算术、逐元素比较、逐元素 `exp`、按轴归约（`reduce_sum/reduce_min/reduce_max`）、显式 `broadcast`、`transpose`、`softmax`、`img2col1d/img2col2d` 和二维 `matmul` 的 IR 形态与 verifier 约束。本规范仅描述方言层字段、文本形式与校验语义，不包含上游高层 API 调度逻辑。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- `功能实现`：[`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)
- `test`：[`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py)

## 依赖

- [`spec/operation/nn.md`](../../spec/operation/nn.md)：上游算子语义。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：`Memory` 的 `shape/stride/dtype/space` 基础语义。
- [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)：方言实现。
- [`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py)：方言测试。

## 目标

- 提供 `global/shared/local/tsm/tlm` 五种 memory space 的统一属性表示。
- 提供可解析、可打印、可校验的 `!nn.memory<...>` 类型表示。
- 为 `nn.add/sub/mul/truediv/eq/ne/lt/le/gt/ge/exp/reduce_sum/reduce_min/reduce_max/broadcast/transpose/softmax/img2col1d/img2col2d/matmul` 提供稳定的方言层接口。
- 明确 `nn dialect` 不支持逐元素隐式 broadcast，所有广播必须显式使用 `nn.broadcast`。
- 保证合法文本 IR 可以 round-trip，非法输入在 parse 或 verifier 阶段被拒绝。

## 限制与边界

- 本文件只定义 `kernel_gen/dialect/nn.py` 的方言层接口，不重复上游 `operation/nn` 的高层 API 语义。
- 上游若允许逐元素隐式 broadcast，进入 `nn dialect` 前必须显式展开为 `nn.broadcast`。
- `img2col` 在方言层只允许公开 `nn.img2col1d` 与 `nn.img2col2d` 两个稳定 op，禁止新增笼统公开名 `nn.img2col`。
- `nn.img2col1d/img2col2d` 仅定义 operand/attribute/result/verifier 合同，不在方言层重复上游 `operation/nn` 的 shape/stride 公式与错误边界全文。
- `nn.softmax` 在方言层只定义 `input/result/axis/space` 的结构化合同；`axis=-1` 默认值、负轴归一化与数值稳定公式属于上游 `operation/nn` 语义，不在方言层重复展开。
- `NnMemorySpaceAttr` 仅允许 `global/shared/local/tsm/tlm` 五种取值。
- `NnMemoryType.space` 与各 op 的 `space` attribute 必须使用同一语义口径。
- `NnMemoryType` 中 `shape` 与 `stride` 的 rank 必须一致；每一维支持静态整数、符号或 `?`。
- `shape` 中的 `?` 表示动态维度；`stride` 中的 `?` 不允许与同位置 `shape` 中的 `?` 直接成对出现。
- 二元逐元素 op 的 `lhs/rhs/result` 必须满足 `shape/stride/space` 的 verifier 约束，不能依赖方言层做隐式 broadcast。
- 比较 op 的结果 `element_type` 必须为 `i1`。
- `nn.exp` 仅接受浮点 `!nn.memory`，结果必须与输入保持同 `shape/stride/element_type/space`。
- `nn.reduce_sum/reduce_min/reduce_max` 使用规范化后的 `axes` 与显式 `keepdim` 建模归约语义；`result.shape/stride` 必须与归约合同一致。
- `nn.matmul` 仅建模二维矩阵乘，`lhs.shape[1]` 与 `rhs.shape[0]` 必须语义一致。
- `nn.softmax` 已在 `kernel_gen/dialect/nn.py` 与 `test/dialect/test_nn_dialect.py` 落地；本节作为公开契约与映射编号基线，后续改动必须保持与本合同闭环一致。
- `space` 指 `nn dialect` 中 memory 所在的物理或逻辑空间，由 `NnMemorySpaceAttr` 表示。
- `memory type` 指 `NnMemoryType`，由 `shape/stride/element_type/space` 组成。
- `round-trip` 指文本 IR 在 parse 后再 print，得到稳定且等价的文本表示。
- 合法 `!nn.memory<...>`、`#nn.space<...>` 与包含公开 op 的模块文本必须支持 round-trip。

## 公开接口

### NnMemorySpaceAttr

功能说明：

- 表示 `nn dialect` 中唯一合法的 memory space attribute。

参数说明：

- `name: str`：space 名称，仅允许 `global/shared/local/tsm/tlm`。

使用示例：

```python
space = NnMemorySpaceAttr.from_name("tsm")
```

注意事项：

- 非法名称必须在解析或校验阶段被拒绝。

返回与限制：

- 返回 `NnMemorySpaceAttr`；只接受五种合法值。

### NnMemoryType

功能说明：

- 表示 `nn dialect` 的 memory 类型，统一建模 `shape/stride/element_type/space`。

参数说明：

- `shape: ArrayAttr[Attribute]`：每维为静态整数、符号或 `?`。
- `stride: ArrayAttr[Attribute]`：每维为静态整数、符号或 `?`。
- `element_type: Attribute`：元素类型 attribute。
- `space: NnMemorySpaceAttr`：memory 所在空间。

使用示例：

```python
mem_ty = NnMemoryType(shape, stride, element_type, space)
```

注意事项：

- `shape` 与 `stride` 的 rank 必须一致。
- `shape` 中的 `?` 可表示动态维度；`stride` 中的 `?` 受同位约束限制。
- 缺失字段的文本类型必须在 parse 阶段失败。

返回与限制：

- 返回 `NnMemoryType`；`space` 必须合法，`shape/stride` 必须满足 rank 与同位约束。

### nn.add

功能说明：

- 逐元素加法。

参数说明：

- `lhs: !nn.memory<...> | i32 | f16 | f32 | !symbol.int`：左操作数。
- `rhs: !nn.memory<...> | i32 | f16 | f32 | !symbol.int`：右操作数。
- `result: !nn.memory<...>`：结果类型。
- `space: #nn.space<...>`：op 的空间属性。

使用示例：

```python
op = NnAddOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
# mixed 形态示例：memory + scalar/symbol
op = NnAddOp(lhs_memory, rhs_scalar_or_symbol, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- `result` 必须为 `NnMemoryType`，且 `lhs/rhs` 至少一侧必须为 `NnMemoryType`。
- 当 `lhs/rhs` 均为 `NnMemoryType` 时，`shape/stride/space` 必须一致。
- 当为 `memory + scalar/symbol` 时，`result.shape/stride/space` 必须与 memory operand 一致。
- `scalar/symbol` 仅支持 `i32/f16/f32/!symbol.int`，其中 `!symbol.int` 按 `i32` 参与 dtype promotion。
- dtype promotion 顺序固定为 `i32 < f16 < f32`。
- 不支持隐式 broadcast。

返回与限制：

- 返回 `NnAddOp`：
- memory+memory 形态下，`result.element_type` 必须与 operand 一致；
- memory+scalar/symbol 形态下，`result.element_type` 必须等于 promotion 后类型。

### nn.sub

功能说明：

- 逐元素减法。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnSubOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `nn.add` 相同，不支持隐式 broadcast。

返回与限制：

- 返回 `NnSubOp`；`result.element_type` 必须与 operand 一致。

### nn.mul

功能说明：

- 逐元素乘法。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnMulOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `nn.add` 相同，不支持隐式 broadcast。

返回与限制：

- 返回 `NnMulOp`；`result.element_type` 必须与 operand 一致。

### nn.truediv

功能说明：

- 逐元素真除法。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnTrueDivOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `nn.add` 相同，不支持隐式 broadcast。

返回与限制：

- 返回 `NnTrueDivOp`；`result.element_type` 必须与 operand 一致。

### nn.eq

功能说明：

- 逐元素相等比较。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnEqOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与算术二元 op 基本一致。
- `result.element_type` 必须为 `i1`。
- 不支持隐式 broadcast。

返回与限制：

- 返回 `NnEqOp`；结果元素类型固定为 `i1`。

### nn.ne

功能说明：

- 逐元素不等比较。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnNeOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `nn.eq` 相同，不支持隐式 broadcast。

返回与限制：

- 返回 `NnNeOp`；结果元素类型固定为 `i1`。

### nn.lt

功能说明：

- 逐元素小于比较。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnLtOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `nn.eq` 相同，不支持隐式 broadcast。

返回与限制：

- 返回 `NnLtOp`；结果元素类型固定为 `i1`。

### nn.le

功能说明：

- 逐元素小于等于比较。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnLeOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `nn.eq` 相同，不支持隐式 broadcast。

返回与限制：

- 返回 `NnLeOp`；结果元素类型固定为 `i1`。

### nn.gt

功能说明：

- 逐元素大于比较。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnGtOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `nn.eq` 相同，不支持隐式 broadcast。

返回与限制：

- 返回 `NnGtOp`；结果元素类型固定为 `i1`。

### nn.ge

功能说明：

- 逐元素大于等于比较。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnGeOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `nn.eq` 相同，不支持隐式 broadcast。

返回与限制：

- 返回 `NnGeOp`；结果元素类型固定为 `i1`。

### nn.exp

功能说明：

- 逐元素指数 op，计算 `e^x`。

参数说明：

- `input: !nn.memory<...>`：输入 memory。
- `result: !nn.memory<...>`：结果 memory。
- `space: #nn.space<...>`：op 的空间属性。

使用示例：

```mlir
%0 = nn.exp %value {space = #nn.space<global>}
  : !nn.memory<[2, 4], [4, 1], f32, #nn.space<global>>
 -> !nn.memory<[2, 4], [4, 1], f32, #nn.space<global>>
```

注意事项：

- `input/result` 必须为 `NnMemoryType`。
- `input.element_type` 必须为浮点类型。
- `result.shape == input.shape`，`result.stride == input.stride`。
- `result.element_type == input.element_type`。
- `input.space == result.space == op.space`。
- 高层语义与错误边界锚点见 [`spec/operation/nn.md`](../../spec/operation/nn.md) 的 `exp(value)`。

返回与限制：

- 返回 `NnExpOp`。
- verifier 合同关键字：
  - `operand-must-be-nn-memory`
  - `operand-element-type-must-be-float`
  - `result-shape-stride-must-match-input`
  - `result-element-type-must-match-input`
  - `result-space-must-match-input-and-attr`

### nn.reduce_sum

功能说明：

- 按指定轴执行求和归约。

参数说明：

- `input: !nn.memory<...>`：输入 memory。
- `axes: ArrayAttr[IntegerAttr]`：归约轴集合，必须是规范化后的非空唯一列表。
- `keepdim: IntegerAttr(i1)`：是否保留被归约轴。
- `result: !nn.memory<...>`：结果 memory。
- `space: #nn.space<...>`：op 的空间属性。

使用示例：

```mlir
%0 = nn.reduce_sum %value {
  axes = [1, 2], keepdim = true, space = #nn.space<global>
} : !nn.memory<[2, 3, 4], [12, 4, 1], f32, #nn.space<global>>
 -> !nn.memory<[2, 1, 1], [1, 1, 1], f32, #nn.space<global>>
```

注意事项：

- `input/result` 必须为 `NnMemoryType`。
- `axes` 必须非空、元素唯一且每个轴满足 `0 <= axis < input.rank`。
- `keepdim` 必须是 `i1` 布尔语义 attribute。
- `result.element_type == input.element_type`。
- `input.space == result.space == op.space`。
- `keepdim=true` 时，`result.rank == input.rank` 且 `axes` 位置维度必须为 `1`。
- `keepdim=false` 时，`result.rank == input.rank - len(axes)`；若归约后 rank 为 `0`，结果必须规范化为 rank-1 形状 `[1]`。
- `result.stride` 必须与 `result.shape` 的连续布局一致。
- 高层语义与错误边界锚点见 [`spec/operation/nn.md`](../../spec/operation/nn.md) 的 `reduce_sum`。

返回与限制：

- 返回 `NnReduceSumOp`。
- verifier 合同关键字：
  - `operand-must-be-nn-memory`
  - `axes-must-be-non-empty-unique-and-in-range`
  - `keepdim-must-be-i1-bool-attr`
  - `result-element-type-must-match-input`
  - `result-space-must-match-input-and-attr`
  - `result-shape-must-match-reduce-contract`
  - `result-stride-must-be-contiguous-for-result-shape`

### nn.reduce_min

功能说明：

- 按指定轴执行最小值归约。

参数说明：

- 同 `nn.reduce_sum`。

使用示例：

```mlir
%0 = nn.reduce_min %value {
  axes = [2], keepdim = false, space = #nn.space<global>
} : !nn.memory<[2, 3, 4], [12, 4, 1], f32, #nn.space<global>>
 -> !nn.memory<[2, 3], [3, 1], f32, #nn.space<global>>
```

注意事项：

- `axes/keepdim/shape/stride/element_type/space` 约束与 `nn.reduce_sum` 一致。
- 静态可判定时，任一归约轴维度若为 `0` 必须显式报错。
- 高层语义与错误边界锚点见 [`spec/operation/nn.md`](../../spec/operation/nn.md) 的 `reduce_min`。

返回与限制：

- 返回 `NnReduceMinOp`。
- verifier 合同关键字：
  - `operand-must-be-nn-memory`
  - `axes-must-be-non-empty-unique-and-in-range`
  - `keepdim-must-be-i1-bool-attr`
  - `result-element-type-must-match-input`
  - `result-space-must-match-input-and-attr`
  - `result-shape-must-match-reduce-contract`
  - `result-stride-must-be-contiguous-for-result-shape`
  - `empty-reduction-extent-must-be-rejected-when-static`

### nn.reduce_max

功能说明：

- 按指定轴执行最大值归约。

参数说明：

- 同 `nn.reduce_sum`。

使用示例：

```mlir
%0 = nn.reduce_max %value {
  axes = [0], keepdim = true, space = #nn.space<global>
} : !nn.memory<[2, 3, 4], [12, 4, 1], f32, #nn.space<global>>
 -> !nn.memory<[1, 3, 4], [12, 4, 1], f32, #nn.space<global>>
```

注意事项：

- `axes/keepdim/shape/stride/element_type/space` 约束与 `nn.reduce_sum` 一致。
- 静态可判定时，任一归约轴维度若为 `0` 必须显式报错。
- 高层语义与错误边界锚点见 [`spec/operation/nn.md`](../../spec/operation/nn.md) 的 `reduce_max`。

返回与限制：

- 返回 `NnReduceMaxOp`。
- verifier 合同关键字：
  - `operand-must-be-nn-memory`
  - `axes-must-be-non-empty-unique-and-in-range`
  - `keepdim-must-be-i1-bool-attr`
  - `result-element-type-must-match-input`
  - `result-space-must-match-input-and-attr`
  - `result-shape-must-match-reduce-contract`
  - `result-stride-must-be-contiguous-for-result-shape`
  - `empty-reduction-extent-must-be-rejected-when-static`

### nn.broadcast

功能说明：

- 显式广播 op，用于把上游广播语义展开到方言层。

参数说明：

- `input: !nn.memory<...>`：输入 memory。
- `result: !nn.memory<...>`：广播后的结果类型。
- `space: #nn.space<...>`：op 的空间属性。

使用示例：

```python
op = NnBroadcastOp(inp, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- `input/result` 必须为 `NnMemoryType`。
- `input.element_type == result.element_type`。
- `input.space == result.space == op.space`。
- 广播按尾维对齐，`result.rank >= input.rank`。
- 对齐后维度要么相等，要么输入维度为静态整数 `1`；`?` 仅与同为 `?` 的维度视为一致。

返回与限制：

- 返回 `NnBroadcastOp`；广播必须显式建模。

### nn.transpose

功能说明：

- 置换维度顺序的转置 op。

参数说明：

- `input: !nn.memory<...>`：输入 memory。
- `result: !nn.memory<...>`：转置后的结果类型。
- `perm: ArrayAttr[IntegerAttr]`：轴置换顺序。
- `space: #nn.space<...>`：op 的空间属性。

使用示例：

```python
op = NnTransposeOp(inp, result_type, perm=[1, 0, 2], space=NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- `input/result` 必须为 `NnMemoryType`。
- `perm` 长度必须与 `input.rank` 一致，且必须是 `0..rank-1` 的排列。
- `result.shape` 必须按 `perm` 重排 `input.shape`。
- `result.stride` 必须按 `perm` 重排 `input.stride`。
- `input.element_type == result.element_type`。
- `input.space == result.space == op.space`。

返回与限制：

- 返回 `NnTransposeOp`；不支持隐式广播或隐式转置。

### nn.softmax

功能说明：

- softmax 归一化 op，表示沿给定轴执行归一化并输出与输入同 rank 的 memory。

参数说明：

- `input: !nn.memory<...>`：输入 memory。
- `result: !nn.memory<...>`：输出 memory，rank 必须与 `input` 一致。
- `axis: i64`：归一化轴属性，必须满足 `-rank <= axis < rank`。
- `space: #nn.space<...>`：op 的空间属性。

使用示例：

```mlir
%0 = nn.softmax %value {
  axis = -1,
  space = #nn.space<global>
} : !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
 -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
```

注意事项：

- `input/result` 必须为 `NnMemoryType`。
- `input.rank` 必须大于 `0`，`axis` 必须落在合法区间 `[-rank, rank-1]`。
- `result.shape` 必须与 `input.shape` 一致。
- `result.stride` 必须与 `input.stride` 一致。
- `result.element_type` 必须与 `input.element_type` 一致，且当前合同只允许浮点元素类型（`f16/bf16/f32/f64`）。
- `input.space == result.space == op.space`。
- 与 `operation/nn` 分层边界：方言层不定义 `axis` 默认值，也不复写数值稳定公式，仅校验结构化字段与类型约束。

返回与限制：

- 返回 `NnSoftmaxOp`（合同名）。
- verifier 合同关键字：
  - `operand-and-result-must-be-nn-memory`
  - `input-rank-must-be-positive`
  - `axis-must-be-in-range`
  - `result-shape-must-match-input`
  - `result-stride-must-match-input`
  - `result-element-type-must-match-input-and-be-float`
  - `result-space-must-match-input-and-attr`

### nn.matmul

功能说明：

- 二维矩阵乘 op。

参数说明：

- `lhs: !nn.memory<...>`：左矩阵。
- `rhs: !nn.memory<...>`：右矩阵。
- `result: !nn.memory<...>`：结果矩阵类型。
- `space: #nn.space<...>`：op 的空间属性。

使用示例：

```python
op = NnMatmulOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- `lhs/rhs/result` 必须为 `NnMemoryType`。
- 三者 `shape` 必须为 rank=2。
- `lhs.shape[1]` 与 `rhs.shape[0]` 必须语义一致。
- `result.shape[0] == lhs.shape[0]`，`result.shape[1] == rhs.shape[1]`。
- `element_type` 与 `space` 必须一致。

返回与限制：

- 返回 `NnMatmulOp`；仅定义二维矩阵乘语义。

### nn.img2col1d

功能说明：

- 一维窗口展开方言 op，将 rank-3 输入 memory 显式重排为 rank-3 列块 memory。

参数说明：

- `input: !nn.memory<...>`：输入 memory，rank 必须为 3。
- `kw: i64`：卷积核宽度，必须为正整数。
- `sw: i64`：窗口宽度步长，必须为正整数。
- `dw: i64`：窗口宽度膨胀，必须为正整数。
- `pl: i64`：左侧 padding，必须为非负整数。
- `pr: i64`：右侧 padding，必须为非负整数。
- `space: #nn.space<...>`：op 的空间属性。
- `result: !nn.memory<...>`：结果 memory，rank 必须为 3。

使用示例：

```mlir
%0 = nn.img2col1d %value {
  kw = 3, sw = 1, dw = 1, pl = 1, pr = 1,
  space = #nn.space<global>
} : !nn.memory<[1, 16, 32], [512, 32, 1], f32, #nn.space<global>>
 -> !nn.memory<[1, 48, 32], [1536, 32, 1], f32, #nn.space<global>>
```

注意事项：

- operand/result 必须是 `!nn.memory`。
- operand rank 必须是 3，result rank 必须是 3。
- `kw/sw/dw` 必须为正整数；`pl/pr` 必须为非负整数。
- `result.element_type` 必须与 `input.element_type` 一致。
- `result.space` 必须与 `input.space` 和 `op.space` 一致。
- `result.shape/stride` 必须满足 `img2col1d` 方言合同；具体高层公式由 `operation/nn` 规范定义。

返回与限制：

- 返回 `NnImg2col1dOp`。
- verifier 合同关键字：
  - `operand-must-be-rank-3-nn-memory`
  - `kw-sw-dw-must-be-positive`
  - `pl-pr-must-be-non-negative`
  - `result-rank-must-be-3`
  - `result-element-type-matches-input`
  - `result-space-matches-input`
  - `result-shape-stride-must-match-img2col1d-contract`

### nn.img2col2d

功能说明：

- 二维窗口展开方言 op，将 rank-4 输入 memory 显式重排为 rank-3 列块 memory。

参数说明：

- `input: !nn.memory<...>`：输入 memory，rank 必须为 4。
- `kh: i64`：卷积核高度，必须为正整数。
- `kw: i64`：卷积核宽度，必须为正整数。
- `sh: i64`：高度步长，必须为正整数。
- `sw: i64`：宽度步长，必须为正整数。
- `dh: i64`：高度膨胀，必须为正整数。
- `dw: i64`：宽度膨胀，必须为正整数。
- `ph: i64`：顶部 padding，必须为非负整数。
- `pw: i64`：底部 padding，必须为非负整数。
- `pl: i64`：左侧 padding，必须为非负整数。
- `pr: i64`：右侧 padding，必须为非负整数。
- `space: #nn.space<...>`：op 的空间属性。
- `result: !nn.memory<...>`：结果 memory，rank 必须为 3。

使用示例：

```mlir
%0 = nn.img2col2d %value {
  kh = 3, kw = 3,
  sh = 1, sw = 1,
  dh = 1, dw = 1,
  ph = 1, pw = 1, pl = 1, pr = 1,
  space = #nn.space<global>
} : !nn.memory<[1, 3, 5, 5], [75, 25, 5, 1], f32, #nn.space<global>>
 -> !nn.memory<[1, 27, 25], [675, 25, 1], f32, #nn.space<global>>
```

注意事项：

- operand/result 必须是 `!nn.memory`。
- operand rank 必须是 4，result rank 必须是 3。
- `kh/kw/sh/sw/dh/dw` 必须为正整数；`ph/pw/pl/pr` 必须为非负整数。
- `result.element_type` 必须与 `input.element_type` 一致。
- `result.space` 必须与 `input.space` 和 `op.space` 一致。
- `result.shape/stride` 必须满足 `img2col2d` 方言合同；具体高层公式由 `operation/nn` 规范定义。

返回与限制：

- 返回 `NnImg2col2dOp`。
- verifier 合同关键字：
  - `operand-must-be-rank-4-nn-memory`
  - `kh-kw-sh-sw-dh-dw-must-be-positive`
  - `ph-pw-pl-pr-must-be-non-negative`
  - `result-rank-must-be-3`
  - `result-element-type-matches-input`
  - `result-space-matches-input`
  - `result-shape-stride-must-match-img2col2d-contract`

## 测试

- 测试文件：[`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py)
- 执行命令：`pytest -q test/dialect/test_nn_dialect.py`

### 测试目标

- 验证 `NnMemorySpaceAttr` 的合法取值、非法输入与文本 round-trip。
- 验证 `NnMemoryType` 的字段完整性、rank 约束、`shape/stride` 合法性与文本 round-trip。
- 验证 `nn.add/sub/mul/truediv/eq/ne/lt/le/gt/ge` 的 operand/result/type/space verifier 约束，其中 `nn.add` 覆盖 memory+scalar/symbol 与 dtype promotion 规则。
- 验证 `nn.exp` 的浮点输入约束、`shape/stride/element_type/space` 一致性与错误路径。
- 验证 `nn.reduce_sum/reduce_min/reduce_max` 的 `axes/keepdim` 约束、结果 `shape/stride` 合同、`dtype/space` 一致性、`keepdim` 非 `i1` 拒绝、结果 `stride` 非连续布局拒绝与静态空归约域错误路径。
- 验证 `nn.broadcast` 的显式广播规则、space 一致性、element type 一致性与文本 round-trip。
- 验证 `nn.transpose` 的 perm/shape/stride/space/element type 约束与文本 round-trip。
- 验证 `nn.softmax` 的 rank/axis/shape/stride/space/element type verifier 约束与错误路径闭环。
- 验证 `nn.img2col1d` 的 operand rank、属性合法性、result rank/type/space 与方言合同约束。
- 验证 `nn.img2col2d` 的 operand rank、属性合法性、result rank/type/space 与方言合同约束。
- 验证 `nn.matmul` 的 rank、shape、space、element type 约束与文本 round-trip。
- 验证逐元素链路拒绝隐式 broadcast。

### 功能与用例清单

| 用例 ID | 测试点 | 对应测试 |
| --- | --- | --- |
| NN-DIA-001 | `NnMemoryType` round-trip | `test_memory_type_round_trip` |
| NN-DIA-002 | `NnMemorySpaceAttr` round-trip | `test_space_attr_round_trip` |
| NN-DIA-003 | 非法 space 拒绝 | `test_invalid_space_attr_rejected` |
| NN-DIA-004 | memory type rank 不一致 | `test_memory_type_rank_mismatch_rejected` |
| NN-DIA-005 | `nn.add` 合法路径 | `test_add_op_verify_success` |
| NN-DIA-006 | `nn.add` operand space 不一致 | `test_add_op_rejects_operand_space_mismatch` |
| NN-DIA-007 | `nn.add` attribute space 不一致 | `test_add_op_rejects_attr_space_mismatch` |
| NN-DIA-008 | 比较结果必须为 `i1` | `test_compare_op_requires_i1_result` |
| NN-DIA-009 | 模块 round-trip | `test_module_round_trip` |
| NN-DIA-010 | 文本 operand space 不一致 | `test_space_mismatch_from_text_rejected` |
| NN-DIA-011 | 文本 attribute space 不一致 | `test_attr_space_mismatch_from_text_rejected` |
| NN-DIA-012 | memory type 缺失字段 | `test_memory_type_parse_requires_all_fields` |
| NN-DIA-013 | `nn.broadcast` 合法路径 | `test_broadcast_op_verify_success` |
| NN-DIA-014 | `nn.broadcast` space 不一致 | `test_broadcast_op_space_mismatch` |
| NN-DIA-015 | `nn.broadcast` element type 不一致 | `test_broadcast_op_element_type_mismatch` |
| NN-DIA-016 | broadcast 模块 round-trip | `test_broadcast_module_round_trip` |
| NN-DIA-017 | `nn.matmul` 合法路径 | `test_matmul_op_verify_success` |
| NN-DIA-018 | `nn.matmul` contracting 维不匹配 | `test_matmul_op_shape_mismatch` |
| NN-DIA-019 | `nn.matmul` 结果 shape 不匹配 | `test_matmul_op_result_shape_mismatch` |
| NN-DIA-020 | matmul 模块 round-trip | `test_matmul_module_round_trip` |
| NN-DIA-021 | `nn.matmul` operand space 不一致 | `test_matmul_op_space_mismatch` |
| NN-DIA-022 | `nn.matmul` attribute space 不一致 | `test_matmul_op_attr_space_mismatch` |
| NN-DIA-023 | `nn.matmul` rank 不匹配 | `test_matmul_op_rank_mismatch` |
| NN-DIA-024 | `nn.matmul` element type 不一致 | `test_matmul_op_element_type_mismatch` |
| NN-DIA-025 | `nn.add` 拒绝隐式 broadcast | `test_add_op_rejects_implicit_broadcast_shape_mismatch` |
| NN-DIA-026 | `nn.eq` 拒绝隐式 broadcast | `test_compare_op_rejects_implicit_broadcast_shape_mismatch` |
| NN-DIA-027 | memory type space 不是 `nn.space` | `test_memory_type_parse_rejects_non_space_attr` |
| NN-DIA-028 | memory type 非法维度条目 | `test_memory_type_rejects_invalid_dim_entry` |
| NN-DIA-029 | stride `?` 与 shape `?` 同位拒绝 | `test_memory_type_rejects_stride_question_dim_pair` |
| NN-DIA-030 | `nn.add` 纯 scalar/symbol operand 拒绝 | `test_add_op_rejects_pure_scalar_operands` |
| NN-DIA-031 | `nn.add` space/stride/element type 不一致 | `test_add_op_rejects_type_mismatch` |
| NN-DIA-032 | 算术 op(sub/mul/truediv) 合法路径 | `test_arithmetic_ops_verify_success` |
| NN-DIA-033 | 比较 op(ne/lt/le/gt/ge) 合法路径 | `test_compare_ops_verify_success` |
| NN-DIA-034 | `nn.broadcast` space/rank/shape 不一致 | `test_broadcast_op_rejects_invalid_inputs` |
| NN-DIA-035 | `nn.matmul` result space 不一致 | `test_matmul_op_result_space_mismatch` |
| NN-DIA-036 | `nn.transpose` 合法路径 | `test_transpose_op_verify_success` |
| NN-DIA-037 | `nn.transpose` perm 非法 | `test_transpose_op_rejects_invalid_perm` |
| NN-DIA-038 | `nn.transpose` shape/stride 不匹配 | `test_transpose_op_result_mismatch` |
| NN-DIA-039 | transpose 模块 round-trip | `test_transpose_module_round_trip` |
| NN-DIA-040 | `nn.add` 接受 memory + const scalar 并做 promotion | `test_add_op_accepts_memory_const_rhs` |
| NN-DIA-041 | `nn.add` 接受 memory + symbol.int 并做 promotion | `test_add_op_accepts_memory_symbol_rhs` |
| NN-DIA-042 | `nn.add` mixed 形态 result shape 不匹配拒绝 | `test_add_op_rejects_mixed_result_shape_mismatch` |
| NN-DIA-043 | `nn.img2col1d` 合同（operand/attrs/result/verifier） | `test_nn_dialect_img2col1d_contract_v1` |
| NN-DIA-044 | `nn.img2col2d` 合同（operand/attrs/result/verifier） | `test_nn_dialect_img2col2d_contract_v1` |
| NN-DIA-045 | `nn.softmax` 合法路径（rank/axis/shape/stride/space/element type） | `test_softmax_op_verify_success` |
| NN-DIA-046 | `nn.softmax` axis 越界或输入 rank 非法时拒绝 | `test_softmax_op_rejects_invalid_axis_or_rank` |
| NN-DIA-047 | `nn.softmax` result shape/stride/dtype/space 不一致时拒绝 | `test_softmax_op_rejects_result_mismatch` |
| NN-DIA-048 | `nn.exp` 合法路径（浮点输入与元信息保持） | `test_exp_op_verify_success` |
| NN-DIA-049 | `nn.exp` 拒绝非浮点输入与 space/shape/stride 不一致 | `test_exp_op_rejects_invalid_inputs` |
| NN-DIA-050 | `nn.reduce_sum` 的 `axes/keepdim` 与结果 shape 合同 | `test_reduce_sum_op_shape_contract` |
| NN-DIA-051 | `nn.reduce_sum` 的 `axes` 非法输入拒绝 | `test_reduce_sum_op_rejects_invalid_axes` |
| NN-DIA-052 | `nn.reduce_min` 的 `keepdim` 与静态空归约域拒绝 | `test_reduce_min_op_contract_and_empty_extent_rejection` |
| NN-DIA-053 | `nn.reduce_max` 的 `keepdim` 与静态空归约域拒绝 | `test_reduce_max_op_contract_and_empty_extent_rejection` |
| NN-DIA-054 | `nn.reduce_*` 的 `dtype/space` 不一致拒绝 | `test_reduce_ops_reject_type_or_space_mismatch` |
| NN-DIA-055 | `nn.exp` 与 `nn.reduce_*` 模块 round-trip | `test_exp_reduce_module_round_trip` |
| NN-DIA-056 | `nn.reduce_*` 的 `keepdim` 非 `i1` attribute 拒绝 | `test_reduce_ops_reject_non_i1_keepdim_attr` |
| NN-DIA-057 | `nn.reduce_*` 的结果 `stride` 非连续布局拒绝 | `test_reduce_ops_reject_non_contiguous_result_stride` |
