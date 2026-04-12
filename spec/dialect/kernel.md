# kernel.md

## 功能简介

- 定义 `kernel` dialect 的执行步骤层运算语义，用于描述逐元素计算、比较、选择、类型转换，以及 `binary_elewise / exp / softmax / reduce(kind=...) / reduce_* / matmul / img2col*` 等 lower 后目标 op 的稳定合同。
- 所有结果通过显式 `outs(...)` 写回，不产生 SSA result。
- 复用 `nn` dialect 的 memory type 与 space attribute，不新增独立 memory 类型体系。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dialect/kernel.md`](../../spec/dialect/kernel.md)
- `功能实现`：[`kernel_gen/dialect/kernel.py`](../../kernel_gen/dialect/kernel.py)
- `test`：[`test/dialect/test_kernel_dialect.py`](../../test/dialect/test_kernel_dialect.py)

## 依赖

- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：`NnMemorySpaceAttr` 与 `NnMemoryType` 复用规则。

## 目标

- 提供可解析、可校验的逐元素、结构化张量变换与 reduction/matmul 类 `kernel.*` op 集合。
- 明确 `ins(...)` / `outs(...)` 形式下的类型、shape、stride、space 与关键 attrs 一致性校验规则。
- 明确 `NnLoweringPass` 面向 `kernel.binary_elewise`、`kernel.compare family`、`kernel.exp`、`kernel.softmax`、`kernel.reduce(kind=...)`、`kernel.matmul`、`kernel.img2col1d`、`kernel.img2col2d` 的目标 op 名字与输出消费链路；`kernel.reduce_sum/min/max` 仍保留为具名 op，但 NnLoweringPass 产出以 `kernel.reduce(kind=...)` 为准。
- 明确 expectation 所要求的 `dma.alloc -> kernel.* -> func.return` 是真实消费链路：`out` operand 必须被目标 op 实际写入，不允许只命中 op 名称而缺失输出写回语义。

## 限制与边界

- 本文件只定义 `kernel dialect` 的 op 合同，不负责函数输出 ABI、module 组织、调度策略或 pass 内部重写细节。
- 不允许使用“万能 kernel op”兜底 `exp / softmax / reduce_* / matmul / img2col*`；上述能力必须以各自具名 `kernel.*` op 公开。
- 所有 op 不产生 SSA result，结果必须写入 `outs(...)`；不得把 `out` 写回链路写成“实现自定”或“可选消费”。
- 本版仅支持 memory operand，不支持标量 operand；标量扩展留待后续版本。
- 对逐元素算术、比较、选择与类型转换，输入 operand 默认要求 `shape/stride/space/element_type` 一致；`kernel` 层不提供 broadcast/transpose 形状变换入口（它们必须在 `dma` 层显式物化）。
- `kernel.reduce` 与 `kernel.reduce_sum/min/max` 可以并存，但 dialect 层必须保持 op 名字与 verifier 语义区分，不能折叠为同一个无差别 op。
- `matmul`、`img2col1d`、`img2col2d` 的结构性变换必须在 verifier 阶段完成 rank / shape / attrs 的机械校验。
- memory operand 的 `shape/stride/space` 必须在 verifier 阶段完成一致性校验。

## 公开接口

### NnMemorySpaceAttr

功能说明：

- 复用 `nn` dialect 的 memory space attribute。

参数说明：

- `name(str)`：space 名称，仅允许 `global/shared/local/tsm/tlm`。

使用示例：

```python
space = NnMemorySpaceAttr.from_name("global")
```

注意事项：

- 非法 space 名称必须在解析或校验阶段被拒绝。

返回与限制：

- 返回 `NnMemorySpaceAttr`。
- 仅接受 `global/shared/local/tsm/tlm` 五种取值。

### NnMemoryType

功能说明：

- 复用 `nn` dialect 的 memory 类型，统一建模 `shape/stride/element_type/space`。

参数说明：

- `shape(ArrayAttr[Attribute])`：每维为静态整数、符号或 `?`。
- `stride(ArrayAttr[Attribute])`：每维为静态整数、符号或 `?`。
- `element_type(Attribute)`：元素类型 attribute。
- `space(NnMemorySpaceAttr)`：memory 所在空间。

使用示例：

```python
mem_ty = NnMemoryType(shape, stride, element_type, space)
```

注意事项：

- `shape` 与 `stride` 的 rank 必须一致。
- `shape` 中的 `?` 表示动态维度。

返回与限制：

- 返回 `NnMemoryType`。
- `shape/stride/space` 必须满足 rank 与合法空间约束。

### kernel.binary_elewise

功能说明：

- 统一的二元逐元素算术与比较 op，通过 `kind` 指定语义，并把结果写入输出 operand。

参数说明：

- `lhs(!nn.memory<...>)`：左输入 operand。
- `rhs(!nn.memory<...>)`：右输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `kind(str)`：语义类型，允许 `add/sub/mul/div/truediv/eq/ne/lt/le/gt/ge`。
- `space(#nn.space<...>)`：op 的空间属性。

使用示例：

```mlir
%out = dma.alloc ... : !nn.memory<f32, [N, C], GM>
kernel.binary_elewise %lhs, %rhs, %out {kind = "add", space = #nn.space<global>} : ...
func.return %out : !nn.memory<f32, [N, C], GM>
```

注意事项：

- `lhs/rhs/out` 的 `shape/stride/space` 必须一致，`kernel` 层不负责形状变换。
- 当 `kind` 为比较类（`eq/ne/lt/le/gt/ge`）时，`out.element_type` 必须是 `i1`。
- 当 `kind` 为算术类（`add/sub/mul/div/truediv`）时，`lhs/rhs/out` 的 `element_type` 必须一致。

返回与限制：

- 返回 `KernelBinaryElewiseOp`。
- 结果写入 `out`。

### kernel.add

功能说明：

- 逐元素加法，将输入 operand 的计算结果写入输出 operand。

参数说明：

- `lhs(!nn.memory<...>)`：左输入 operand。
- `rhs(!nn.memory<...>)`：右输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `space(#nn.space<...>)`：op 的空间属性。

使用示例：

```python
op = KernelAddOp(lhs, rhs, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- `lhs/rhs/out` 的 `shape/stride/space` 必须一致。
- `lhs.element_type` 与 `rhs.element_type` 必须一致，且等于 `out.element_type`。
- op 不产生 SSA result。

返回与限制：

- 返回 `KernelAddOp`。
- 结果写入 `out`。

### kernel.sub

功能说明：

- 逐元素减法，将输入 operand 的计算结果写入输出 operand。

参数说明：

- 同 `kernel.add`。

使用示例：

```python
op = KernelSubOp(lhs, rhs, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `kernel.add` 相同。

返回与限制：

- 返回 `KernelSubOp`。
- 结果写入 `out`。

### kernel.mul

功能说明：

- 逐元素乘法，将输入 operand 的计算结果写入输出 operand。

参数说明：

- 同 `kernel.add`。

使用示例：

```python
op = KernelMulOp(lhs, rhs, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `kernel.add` 相同。

返回与限制：

- 返回 `KernelMulOp`。
- 结果写入 `out`。

### kernel.div

功能说明：

- 逐元素除法，将输入 operand 的计算结果写入输出 operand。

参数说明：

- 同 `kernel.add`。

使用示例：

```python
op = KernelDivOp(lhs, rhs, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `kernel.add` 相同。

返回与限制：

- 返回 `KernelDivOp`。
- 结果写入 `out`。

### kernel.eq

功能说明：

- 逐元素相等比较，将比较结果写入输出 operand。

参数说明：

- `lhs(!nn.memory<...>)`：左输入 operand。
- `rhs(!nn.memory<...>)`：右输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `space(#nn.space<...>)`：op 的空间属性。

使用示例：

```python
op = KernelEqOp(lhs, rhs, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- `lhs/rhs/out` 的 `shape/stride/space` 必须一致。
- `out.element_type` 必须为 `i1`。
- op 不产生 SSA result。

返回与限制：

- 返回 `KernelEqOp`。
- 结果写入 `out`。

### kernel.lt

功能说明：

- 逐元素小于比较，将比较结果写入输出 operand。

参数说明：

- 同 `kernel.eq`。

使用示例：

```python
op = KernelLtOp(lhs, rhs, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `kernel.eq` 相同。

返回与限制：

- 返回 `KernelLtOp`。
- 结果写入 `out`。

### kernel.gt

功能说明：

- 逐元素大于比较，将比较结果写入输出 operand。

参数说明：

- 同 `kernel.eq`。

使用示例：

```python
op = KernelGtOp(lhs, rhs, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `kernel.eq` 相同。

返回与限制：

- 返回 `KernelGtOp`。
- 结果写入 `out`。

### kernel.select

功能说明：

- 逐元素条件选择，根据条件 operand 在两个输入 operand 间选择结果并写入输出 operand。

参数说明：

- `cond(!nn.memory<...>)`：条件 operand。
- `lhs(!nn.memory<...>)`：条件为真时的输入 operand。
- `rhs(!nn.memory<...>)`：条件为假时的输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `space(#nn.space<...>)`：op 的空间属性。

使用示例：

```python
op = KernelSelectOp(cond, lhs, rhs, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- `cond.element_type` 必须为 `i1`。
- `cond/lhs/rhs/out` 的 `shape/stride/space` 必须一致。
- `lhs/rhs/out` 的 `element_type` 必须一致。

返回与限制：

- 返回 `KernelSelectOp`。
- 结果写入 `out`。

### kernel.cast

功能说明：

- 逐元素类型转换，将转换结果写入输出 operand。

参数说明：

- `input(!nn.memory<...>)`：输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `space(#nn.space<...>)`：op 的空间属性。

使用示例：

```python
op = KernelCastOp(input_value, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- `input` 与 `out` 的 `shape/stride/space` 必须一致。
- `input.element_type` 与 `out.element_type` 必须为整数或浮点类型；允许 `i8/i16/i32/i64` 与 `f16/bf16/f32/f64`，不允许 `i1`。

返回与限制：

- 返回 `KernelCastOp`。
- 结果写入 `out`。

### kernel.exp

功能说明：

- 对输入 operand 做逐元素指数计算，并把结果写入输出 operand。

参数说明：

- `input(!nn.memory<...>)`：输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `space(#nn.space<...>)`：op 的空间属性。

使用示例：

```mlir
%out = dma.alloc ... : !nn.memory<f32, [N, C], GM>
kernel.exp %src, %out : ...
func.return %out : !nn.memory<f32, [N, C], GM>
```

注意事项：

- `input/out` 的 `shape/stride/space` 必须一致。
- `input.element_type` 与 `out.element_type` 必须一致，且必须为浮点类型。

返回与限制：

- 返回 `KernelExpOp`。
- 结果写入 `out`。

### kernel.softmax

功能说明：

- 沿指定 `axis` 对输入 operand 执行 softmax，并把结果写入输出 operand。

参数说明：

- `input(!nn.memory<...>)`：输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `axis(i64)`：softmax 归一化轴。
- `space(#nn.space<...>)`：op 的空间属性。

使用示例：

```mlir
%out = dma.alloc ... : !nn.memory<f32, [B, C], GM>
kernel.softmax %src, %out {axis = 1 : i64} : ...
func.return %out : !nn.memory<f32, [B, C], GM>
```

注意事项：

- `input/out` 的 `shape/stride/space` 必须一致。
- `axis` 必须命中 `input` 的合法维度范围。
- `input.element_type` 与 `out.element_type` 必须一致，且必须为浮点类型。

返回与限制：

- 返回 `KernelSoftmaxOp`。
- 结果写入 `out`。

### kernel.reduce_sum

功能说明：

- 沿指定 `axis` 对输入 operand 执行求和 reduction，并把结果写入输出 operand。

参数说明：

- `input(!nn.memory<...>)`：输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `axis(i64)`：reduction 轴。
- `keepdim(bool)`：是否保留被归约维度。
- `space(#nn.space<...>)`：op 的空间属性。

使用示例：

```mlir
%out = dma.alloc ... : !nn.memory<f32, [B], GM>
kernel.reduce_sum %src, %out {axis = 1 : i64, keepdim = false} : ...
func.return %out : !nn.memory<f32, [B], GM>
```

注意事项：

- `reduce_sum`、`reduce_min`、`reduce_max` 共享 axis/keepdim 合同，但 op 名字必须保持区分。
- `axis` 必须命中合法维度；`keepdim` 必须与 `out.rank/out.shape` 机械一致。

返回与限制：

- 返回 `KernelReduceSumOp`。
- 结果写入 `out`。

### kernel.reduce

功能说明：

- 通过 `kind` 指定归约语义，对输入 operand 执行 reduction，并把结果写入输出 operand。

参数说明：

- `input(!nn.memory<...>)`：输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `axis(i64)`：reduction 轴。
- `keepdim(bool)`：是否保留被归约维度。
- `kind(str)`：归约类型，允许 `sum/min/max`。
- `space(#nn.space<...>)`：op 的空间属性。

使用示例：

```mlir
%out = dma.alloc ... : !nn.memory<f32, [B], GM>
kernel.reduce %src, %out {axis = 1 : i64, keepdim = false, kind = "sum", space = #nn.space<global>} : ...
func.return %out : !nn.memory<f32, [B], GM>
```

注意事项：

- `kind` 必须命中 `sum/min/max` 集合。
- `axis` 必须命中合法维度范围；`keepdim` 必须与 `out.rank/out.shape` 机械一致。
- `input.element_type` 与 `out.element_type` 必须一致，且 `input/out/space` 必须一致。

返回与限制：

- 返回 `KernelReduceOp`。
- 结果写入 `out`。

### kernel.reduce_min

功能说明：

- 沿指定 `axis` 对输入 operand 执行最小值 reduction，并把结果写入输出 operand。

参数说明：

- 同 `kernel.reduce_sum`。

使用示例：

```mlir
%out = dma.alloc ... : !nn.memory<f32, [B], GM>
kernel.reduce_min %src, %out {axis = 1 : i64, keepdim = false} : ...
func.return %out : !nn.memory<f32, [B], GM>
```

注意事项：

- verifier 的 `axis/keepdim/out.shape` 约束与 `kernel.reduce_sum` 相同。

返回与限制：

- 返回 `KernelReduceMinOp`。
- 结果写入 `out`。

### kernel.reduce_max

功能说明：

- 沿指定 `axis` 对输入 operand 执行最大值 reduction，并把结果写入输出 operand。

参数说明：

- 同 `kernel.reduce_sum`。

使用示例：

```mlir
%out = dma.alloc ... : !nn.memory<f32, [B], GM>
kernel.reduce_max %src, %out {axis = 1 : i64, keepdim = false} : ...
func.return %out : !nn.memory<f32, [B], GM>
```

注意事项：

- verifier 的 `axis/keepdim/out.shape` 约束与 `kernel.reduce_sum` 相同。

返回与限制：

- 返回 `KernelReduceMaxOp`。
- 结果写入 `out`。

### kernel.matmul

功能说明：

- 对左右输入 operand 执行矩阵乘，并把结果写入输出 operand。

参数说明：

- `lhs(!nn.memory<...>)`：左输入 operand。
- `rhs(!nn.memory<...>)`：右输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `space(#nn.space<...>)`：op 的空间属性。

使用示例：

```mlir
%out = dma.alloc ... : !nn.memory<f32, [M, N], GM>
kernel.matmul %lhs, %rhs, %out : ...
func.return %out : !nn.memory<f32, [M, N], GM>
```

注意事项：

- `lhs/rhs/out` 必须满足二维矩阵乘合同：`lhs=[M, K]`、`rhs=[K, N]`、`out=[M, N]`。
- `lhs`、`rhs`、`out` 的 rank 都必须严格等于 `2`；任一 operand 不是二维 memory 时必须 verifier 失败，不能静默压扁、扩维或转交下游兜底。
- `lhs.shape[1]` 必须等于 `rhs.shape[0]`，且 `out.shape` 必须机械等于 `[lhs.shape[0], rhs.shape[1]]`；任一 shape 不匹配都必须 verifier 失败。
- `lhs.element_type`、`rhs.element_type`、`out.element_type` 必须一致；dtype mismatch 必须 verifier 失败，不能静默放行。
- `kernel.matmul` 不接受批维 broadcast 或隐式 transpose。

返回与限制：

- 返回 `KernelMatmulOp`。
- 结果写入 `out`。

### kernel.img2col1d

功能说明：

- 对 1D 输入 memory 执行窗口展开，并把结构化结果写入输出 operand。

参数说明：

- `input(!nn.memory<...>)`：输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `k(i64)`：卷积核宽度。
- `s(i64)`：步长。
- `d(i64)`：dilation。
- `p_left(i64)`：左 padding。
- `p_right(i64)`：右 padding。
- `space(#nn.space<...>)`：op 的空间属性。

使用示例：

```mlir
%out = dma.alloc ... : !nn.memory<f16, [N, C, K, W_out], GM>
kernel.img2col1d %src, %out {k = 3 : i64, s = 1 : i64, d = 1 : i64, p_left = 0 : i64, p_right = 0 : i64} : ...
func.return %out : !nn.memory<f16, [N, C, K, W_out], GM>
```

注意事项：

- `out` 必须保持结构化窗口轴，不允许回退为压扁列块结果。
- `input` 必须是 rank=`3` 的 `!nn.memory<elem, [N, C, W], space>`，轴语义固定为 `N/C/W`；不接受压扁输入、缺失 channel 轴或其他 layout 解释。
- `out.shape[2]` 必须机械等于 `k`，`W_out` 必须机械满足 `W_out = floor((W + p_left + p_right - d * (k - 1) - 1) / s) + 1`；若 `out.shape[2] != k`、按 `input.shape[2]` 与 attrs 计算得到的 `W_out` 与 `out.shape[3]` 不一致，或计算结果 `< 1`，必须 verifier 失败。
- `k/s/d/p_left/p_right` 必须与 `input.shape -> out.shape` 的上述关系机械一致，不能只校验 attrs 显式存在而放行错误输出形状。
- `out` 必须是 rank=`4` 的 `!nn.memory<elem, [N, C, K, W_out], space>`，并与 `input` 保持同一 `element_type` 与 `space`。

返回与限制：

- 返回 `KernelImg2col1dOp`。
- 结果写入 `out`。

### kernel.img2col2d

功能说明：

- 对 2D 输入 memory 执行窗口展开，并把结构化结果写入输出 operand。

参数说明：

- `input(!nn.memory<...>)`：输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `kh(i64)`：卷积核高。
- `kw(i64)`：卷积核宽。
- `sh(i64)`：高方向步长。
- `sw(i64)`：宽方向步长。
- `dh(i64)`：高方向 dilation。
- `dw(i64)`：宽方向 dilation。
- `ph(i64)`：上 padding。
- `pw(i64)`：下 padding。
- `pl(i64)`：左 padding。
- `pr(i64)`：右 padding。
- `space(#nn.space<...>)`：op 的空间属性。

使用示例：

```mlir
%out = dma.alloc ... : !nn.memory<f16, [N, C, KH, KW, OH, OW], GM>
kernel.img2col2d %src, %out {kh = 2 : i64, kw = 3 : i64, sh = 1 : i64, sw = 1 : i64, dh = 1 : i64, dw = 1 : i64, ph = 0 : i64, pw = 0 : i64, pl = 0 : i64, pr = 0 : i64} : ...
func.return %out : !nn.memory<f16, [N, C, KH, KW, OH, OW], GM>
```

注意事项：

- `out` 必须保持结构化窗口轴，不允许回退为压扁列块结果。
- `input` 必须是 rank=`4` 的 `!nn.memory<elem, [N, C, H, W], space>`，轴语义固定为 `N/C/H/W`；不接受 NHWC、压扁输入或其他 layout 解释。
- `out.shape[2:4]` 必须机械等于 `[kh, kw]`；`OH` 必须机械满足 `OH = floor((H + ph + pw - dh * (kh - 1) - 1) / sh) + 1`，`OW` 必须机械满足 `OW = floor((W + pl + pr - dw * (kw - 1) - 1) / sw) + 1`；若 `out.shape[2:4] != [kh, kw]`、按 `input.shape[2:4]` 与 attrs 计算得到的 `OH/OW` 与 `out.shape[4:6]` 不一致，或任一计算结果 `< 1`，必须 verifier 失败。
- `kh/kw/sh/sw/dh/dw/ph/pw/pl/pr` 必须与 `input.shape -> out.shape` 的上述关系机械一致，不能只校验 attrs 显式存在而放行错误输出形状。
- `out` 必须是 rank=`6` 的 `!nn.memory<elem, [N, C, KH, KW, OH, OW], space>`，并与 `input` 保持同一 `element_type` 与 `space`。
- `kernel.img2col2d` 的 attrs 必须显式可见，不允许把窗口参数隐藏在“实现自定”逻辑中。

返回与限制：

- 返回 `KernelImg2col2dOp`。
- 结果写入 `out`。

## 测试

- 测试文件：
  - [`test/dialect/test_kernel_dialect.py`](../../test/dialect/test_kernel_dialect.py)
  - [`test/pass/nn_lowering/public_contract_kernel.py`](../../test/pass/nn_lowering/public_contract_kernel.py)
- 执行命令：
  - `pytest -q test/dialect/test_kernel_dialect.py`
  - `pytest -q test/pass/nn_lowering/public_contract_kernel.py`

### 测试目标

- 验证 `NnMemorySpaceAttr` 与 `NnMemoryType` 在 `kernel` 方言中的复用与校验行为。
- 验证基础逐元素算术、比较、选择与类型转换 op 的 verifier 约束。
- 验证 `kernel.binary_elewise / kernel.exp / kernel.softmax / kernel.reduce / kernel.reduce_* / kernel.matmul / kernel.img2col*` 的 op 名字、关键 attrs 与 `out` 消费链路合同。
- 验证 `kernel.matmul` 对非二维 operand、`[M,K] x [K,N] -> [M,N]` 形状不匹配的 verifier 拒绝路径已被机械锁定。
- 验证 `kernel.img2col1d/img2col2d` 的输入 rank/layout 合同与结构化输出合同已被机械锁定。
- 验证 `kernel.img2col1d` 的 `input.shape + attrs -> W_out`、`kernel.img2col2d` 的 `input.shape + attrs -> OH/OW` 公式与拒绝路径已被机械锁定。
- 验证“无 SSA result、显式输出 operand”约束。

### 功能与用例清单

| 用例 ID | 功能 | 对应测试 |
| --- | --- | --- |
| TC-KRN-001 | 合法 space 创建成功 | `test_kernel_space_attr_valid` |
| TC-KRN-002 | 非法 space 被拒绝 | `test_kernel_space_attr_invalid` |
| TC-KRN-003 | `shape/stride` rank 不一致 | `test_kernel_memory_type_rank_mismatch` |
| TC-KRN-004 | `kernel.add` 正常路径 | `test_kernel_add_success` |
| TC-KRN-005 | `kernel.add` shape 不一致报错 | `test_kernel_add_shape_mismatch` |
| TC-KRN-006 | `kernel.eq` 输出类型为 `i1` | `test_kernel_eq_output_type` |
| TC-KRN-007 | `kernel.eq` 输出类型非法 | `test_kernel_eq_output_type_error` |
| TC-KRN-008 | `kernel.select` 条件类型非法 | `test_kernel_select_cond_type_error` |
| TC-KRN-009 | `kernel.cast` 类型非法 | `test_kernel_cast_type_error` |
| TC-KRN-010 | op 不产生 SSA result | `test_kernel_ops_no_result` |
| TC-KRN-012 | `kernel.softmax` 的 `axis` 非法触发 verifier 失败 | `test_kernel_softmax_axis_error` |
| TC-KRN-013 | `kernel.reduce_sum/min/max` 保持具名区分且校验 `axis/keepdim` | `test_kernel_reduce_max_family_contract` |
| TC-KRN-020 | `kernel.reduce_max` 拒绝越界 `axis` 与非法 `keepdim` | `test_kernel_reduce_max_axis_and_keepdim_error` |
| TC-KRN-021 | `kernel.binary_elewise` 与 `kernel.reduce` 公开合同可用 | `test_public_contract_kernel_binary_elewise_and_reduce` |
| TC-KRN-014 | `kernel.matmul` 拒绝 dtype mismatch | `test_kernel_matmul_dtype_mismatch` |
| TC-KRN-015 | `kernel.matmul` 拒绝非二维 operand 与 `[M,K] x [K,N] -> [M,N]` shape 失配 | `test_kernel_matmul_rank_shape_contract` |
| TC-KRN-017 | `kernel.img2col1d/img2col2d` 保持结构化输出与显式窗口 attrs | `test_kernel_img2col_structured_contract` |
| TC-KRN-018 | `kernel.img2col1d/img2col2d` 拒绝非法输入 rank 或 layout | `test_kernel_img2col_input_rank_layout_contract` |
| TC-KRN-019 | `kernel.img2col1d/img2col2d` 拒绝 `input.shape + attrs` 推导出的 `W_out/OH/OW` 与 `out.shape` 不一致、公式结果 `< 1` 或窗口轴不等于 `k/[kh,kw]` | `test_kernel_img2col_output_extent_contract` |
