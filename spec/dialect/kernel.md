# kernel.md

## 功能简介

- 定义 `kernel` dialect 的执行步骤层运算语义，用于描述逐元素计算、比较、选择，以及 `binary_elewise / exp / reduce(kind=...) / reduce_* / matmul / img2col*` 等 lower 后目标 op 的稳定合同。
- 所有结果通过显式 `outs(...)` 写回，不产生 SSA result。
- 复用 `nn` dialect 的 memory type 与 space attribute，不新增独立 memory 类型体系。

## API 列表

- `class Kernel(Dialect)`
- `class KernelBinaryElewiseOp(out: SSAValue | Operation, lhs: SSAValue | Operation, rhs: SSAValue | Operation, *, kind: str | StringAttr, space: NnMemorySpaceAttr)`
- `class KernelSelectOp(out: SSAValue | Operation, cond: SSAValue | Operation, lhs: SSAValue | Operation, rhs: SSAValue | Operation, space: NnMemorySpaceAttr)`
- `class KernelExpOp(input_value: SSAValue | Operation, out: SSAValue | Operation, space: NnMemorySpaceAttr)`
- `class KernelReduceOp(out: SSAValue | Operation, input_value: SSAValue | Operation, *, kind: str | StringAttr, axis: int | IntegerAttr | IntAttr, keepdim: bool | int | IntegerAttr | IntAttr, space: NnMemorySpaceAttr)`
- `class KernelReduceMinOp(out: SSAValue | Operation, input_value: SSAValue | Operation, axis: int | IntegerAttr | IntAttr, keepdim: bool | int | IntegerAttr | IntAttr, space: NnMemorySpaceAttr)`
- `class KernelMatmulOp(out: SSAValue | Operation, lhs: SSAValue | Operation, rhs: SSAValue | Operation, space: NnMemorySpaceAttr)`
- `class KernelImg2col1dOp(out: SSAValue | Operation, input_value: SSAValue | Operation, k: SSAValue | Operation, s: SSAValue | Operation, d: SSAValue | Operation, p_left: SSAValue | Operation, p_right: SSAValue | Operation, space: NnMemorySpaceAttr)`
- `class KernelImg2col2dOp(out: SSAValue | Operation, input_value: SSAValue | Operation, kh: SSAValue | Operation, kw: SSAValue | Operation, sh: SSAValue | Operation, sw: SSAValue | Operation, dh: SSAValue | Operation, dw: SSAValue | Operation, ph: SSAValue | Operation, pw: SSAValue | Operation, pl: SSAValue | Operation, pr: SSAValue | Operation, space: NnMemorySpaceAttr)`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dialect/kernel.md`](../../spec/dialect/kernel.md)
- `功能实现`：[`kernel_gen/dialect/kernel.py`](../../kernel_gen/dialect/kernel.py)
- `test`：[`test/dialect/test_kernel.py`](../../test/dialect/test_kernel.py)

## 依赖

- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：`NnMemorySpaceAttr` 与 `NnMemoryType` 复用规则。

## 目标

- 提供可解析、可校验的逐元素、结构化张量变换与 reduction/matmul 类 `kernel.*` op 集合。
- 明确 `ins(...)` / `outs(...)` 形式下的类型、shape、stride、space 与关键 attrs 校验规则。
- 明确 `NnLoweringPass` 面向 `kernel.binary_elewise`、`kernel.exp`、`kernel.reduce(kind=...)`、`kernel.matmul`、`kernel.img2col1d`、`kernel.img2col2d` 的目标 op 名字与输出消费链路；`kernel.reduce_min` 是当前保留的具名最小值归约 op，但 NnLoweringPass 产出以 `kernel.reduce(kind=...)` 为准。
- 明确 `dma.alloc -> kernel.* -> func.return` 是真实消费链路：`out` operand 必须被目标 op 实际写入，不允许只命中 op 名称而缺失输出写回语义。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本文件只定义 `kernel dialect` 的 op 合同，不负责函数输出 ABI、module 组织、调度策略或 pass 内部重写细节。
- 不允许使用“万能 kernel op”兜底 `exp / reduce_* / matmul / img2col*`；上述能力必须以各自具名 `kernel.*` op 公开。
- 所有 op 不产生 SSA result，结果必须写入 `outs(...)`；不得把 `out` 写回链路写成“实现自定”或“可选消费”。
- 本版仅支持 memory operand，不支持标量 operand；标量扩展留待后续版本。
- 对逐元素算术、比较与选择，输入 operand 默认要求 `shape/stride/space/element_type` 一致；`kernel` 层不提供 broadcast/transpose 形状变换入口（它们必须在 `dma` 层显式物化）。
- `kernel.reduce` 是当前通用 reduction 入口；`kernel.reduce_min` 是现存保留具名 op，二者必须保持 op 名字与 verifier 语义区分。
- `matmul`、`img2col1d`、`img2col2d` 的结构性变换必须在 verifier 阶段完成 rank / shape / attrs 的机械校验。
- 除 `kernel.matmul` 的 mixed-space 合同外，memory operand 的 `shape/stride/space` 必须在 verifier 阶段完成一致性校验；`kernel.matmul` 只放开 out/lhs/rhs 的 space 一致性要求，仍校验 rank、shape 与 element_type。

### 非公开旧名说明

- 功能说明：

- 旧具名逐元素算术 op 不属于当前公开 API。
- 旧具名逐元素比较 op 不属于当前公开 API。
- 旧 cast op 不属于当前公开 API。
- 旧 softmax op 不属于当前公开 API。

- 注意事项：

- 上述旧具名逐元素公开名不属于 `kernel` dialect 的公开 API 列表。
- 逐元素算术与比较统一通过 `kernel.binary_elewise(kind=...)` 表达。

## API详细说明

### `class Kernel(Dialect)`

- api：`class Kernel(Dialect)`
- 参数：无。
- 返回值：`Kernel` dialect 类。
- 使用示例：

  ```python
  from kernel_gen.dialect.kernel import Kernel

  assert Kernel.name == "kernel"
  ```
- 功能说明：声明并导出 `kernel dialect`，聚合本文件列出的公开 op。
- 注意事项：`Kernel` 只承载 dialect 注册信息；memory type / memory space 继续复用 `nn dialect`。

### `class KernelBinaryElewiseOp(out: SSAValue | Operation, lhs: SSAValue | Operation, rhs: SSAValue | Operation, *, kind: str | StringAttr, space: NnMemorySpaceAttr)`

- api：`class KernelBinaryElewiseOp(out: SSAValue | Operation, lhs: SSAValue | Operation, rhs: SSAValue | Operation, *, kind: str | StringAttr, space: NnMemorySpaceAttr)`

- 功能说明：

- 统一的二元逐元素算术与比较 op，通过 `kind` 指定语义，并把结果写入输出 operand。

- 参数：

- `lhs(!nn.memory<...>)`：左输入 operand。
- `rhs(!nn.memory<...>)`：右输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `kind(str)`：语义类型，允许 `add/sub/mul/div/truediv/eq/ne/lt/le/gt/ge`。
- `space(#nn.space<...>)`：op 的空间属性。

- 使用示例：

```mlir
%out = dma.alloc value : !nn.memory<f32, [N, C], GM>
kernel.binary_elewise %out, %lhs, %rhs {kind = "add", space = #nn.space<global>} : value
func.return %out : !nn.memory<f32, [N, C], GM>
```

- 注意事项：

- `lhs/rhs/out` 的 `shape/stride/space` 必须一致，`kernel` 层不负责形状变换。
- 当 `kind` 为比较类（`eq/ne/lt/le/gt/ge`）时，`out.element_type` 必须是 `i1`。
- 当 `kind` 为算术类（`add/sub/mul/div/truediv`）时，`lhs/rhs/out` 的 `element_type` 必须一致。

- 返回值：

- 返回 `KernelBinaryElewiseOp`。
- 结果写入 `out`。

### `class KernelSelectOp(out: SSAValue | Operation, cond: SSAValue | Operation, lhs: SSAValue | Operation, rhs: SSAValue | Operation, space: NnMemorySpaceAttr)`

- api：`class KernelSelectOp(out: SSAValue | Operation, cond: SSAValue | Operation, lhs: SSAValue | Operation, rhs: SSAValue | Operation, space: NnMemorySpaceAttr)`

- 功能说明：

- 逐元素条件选择，根据条件 operand 在两个输入 operand 间选择结果并写入输出 operand。

- 参数：

- `cond(!nn.memory<...>)`：条件 operand。
- `lhs(!nn.memory<...>)`：条件为真时的输入 operand。
- `rhs(!nn.memory<...>)`：条件为假时的输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `space(#nn.space<...>)`：op 的空间属性。

- 使用示例：

```python
op = KernelSelectOp(cond, lhs, rhs, out, NnMemorySpaceAttr.from_name("global"))
```

- 注意事项：

- `cond.element_type` 必须为 `i1`。
- `cond/lhs/rhs/out` 的 `shape/stride/space` 必须一致。
- `lhs/rhs/out` 的 `element_type` 必须一致。

- 返回值：

- 返回 `KernelSelectOp`。
- 结果写入 `out`。

### `class KernelExpOp(input_value: SSAValue | Operation, out: SSAValue | Operation, space: NnMemorySpaceAttr)`

- api：`class KernelExpOp(input_value: SSAValue | Operation, out: SSAValue | Operation, space: NnMemorySpaceAttr)`

- 功能说明：

- 对输入 operand 做逐元素指数计算，并把结果写入输出 operand。

- 参数：

- `input(!nn.memory<...>)`：输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `space(#nn.space<...>)`：op 的空间属性。

- 使用示例：

```mlir
%out = dma.alloc value : !nn.memory<f32, [N, C], GM>
kernel.exp %src, %out : value
func.return %out : !nn.memory<f32, [N, C], GM>
```

- 注意事项：

- `input/out` 的 `shape/stride/space` 必须一致。
- `input.element_type` 与 `out.element_type` 必须一致，且必须为浮点类型。

- 返回值：

- 返回 `KernelExpOp`。
- 结果写入 `out`。

### `class KernelReduceOp(out: SSAValue | Operation, input_value: SSAValue | Operation, *, kind: str | StringAttr, axis: int | IntegerAttr | IntAttr, keepdim: bool | int | IntegerAttr | IntAttr, space: NnMemorySpaceAttr)`

- api：`class KernelReduceOp(out: SSAValue | Operation, input_value: SSAValue | Operation, *, kind: str | StringAttr, axis: int | IntegerAttr | IntAttr, keepdim: bool | int | IntegerAttr | IntAttr, space: NnMemorySpaceAttr)`

- 功能说明：

- 通过 `kind` 指定归约语义，对输入 operand 执行 reduction，并把结果写入输出 operand。

- 参数：

- `input(!nn.memory<...>)`：输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `axis(i64)`：reduction 轴。
- `keepdim(bool)`：是否保留被归约维度。
- `kind(str)`：归约类型，允许 `sum/min/max`。
- `space(#nn.space<...>)`：op 的空间属性。

- 使用示例：

```mlir
%out = dma.alloc ... : !nn.memory<f32, [B], GM>
kernel.reduce %src, %out {axis = 1 : i64, keepdim = false, kind = "sum", space = #nn.space<global>} : ...
func.return %out : !nn.memory<f32, [B], GM>
```

- 注意事项：

- `kind` 必须命中 `sum/min/max` 集合。
- `axis` 必须命中合法维度范围；`keepdim` 必须与 `out.rank/out.shape` 机械一致。
- `input.element_type` 与 `out.element_type` 必须一致，且 `input/out/space` 必须一致。

- 返回值：

- 返回 `KernelReduceOp`。
- 结果写入 `out`。

### `class KernelReduceMinOp(out: SSAValue | Operation, input_value: SSAValue | Operation, axis: int | IntegerAttr | IntAttr, keepdim: bool | int | IntegerAttr | IntAttr, space: NnMemorySpaceAttr)`

- api：`class KernelReduceMinOp(out: SSAValue | Operation, input_value: SSAValue | Operation, axis: int | IntegerAttr | IntAttr, keepdim: bool | int | IntegerAttr | IntAttr, space: NnMemorySpaceAttr)`

- 功能说明：

- 沿指定 `axis` 对输入 operand 执行最小值 reduction，并把结果写入输出 operand。

- 参数：

- 同 `kernel.reduce`。

- 使用示例：

```mlir
%out = dma.alloc value : !nn.memory<f32, [B], GM>
kernel.reduce_min %src, %out {axis = 1 : i64, keepdim = false} : value
func.return %out : !nn.memory<f32, [B], GM>
```

- 注意事项：

- verifier 的 `axis/keepdim/out.shape` 约束与 `kernel.reduce` 相同。

- 返回值：

- 返回 `KernelReduceMinOp`。
- 结果写入 `out`。

### `class KernelMatmulOp(out: SSAValue | Operation, lhs: SSAValue | Operation, rhs: SSAValue | Operation, space: NnMemorySpaceAttr)`

- api：`class KernelMatmulOp(out: SSAValue | Operation, lhs: SSAValue | Operation, rhs: SSAValue | Operation, space: NnMemorySpaceAttr)`

- 功能说明：

- 对左右输入 operand 执行矩阵乘，并把结果写入输出 operand。

- 参数：

- `lhs(!nn.memory<...>)`：左输入 operand。
- `rhs(!nn.memory<...>)`：右输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `space(#nn.space<...>)`：op 的空间属性。

- 使用示例：

```mlir
%out = dma.alloc value : !nn.memory<f32, [M, N], GM>
kernel.matmul %lhs, %rhs, %out : value
func.return %out : !nn.memory<f32, [M, N], GM>
```

- 注意事项：

- `lhs/rhs/out` 必须满足二维矩阵乘合同：`lhs=[M, K]`、`rhs=[K, N]`、`out=[M, N]`。
- `lhs`、`rhs`、`out` 的 rank 都必须严格等于 `2`；任一 operand 不是二维 memory 时必须 verifier 失败，不能静默压扁、扩维或转交下游兜底。
- `lhs.shape[1]` 必须等于 `rhs.shape[0]`，且 `out.shape` 必须机械等于 `[lhs.shape[0], rhs.shape[1]]`；任一 shape 不匹配都必须 verifier 失败。
- `lhs.element_type`、`rhs.element_type`、`out.element_type` 必须一致；dtype mismatch 必须 verifier 失败，不能静默放行。
- `lhs`、`rhs`、`out` 可以使用不同合法 memory space；该 mixed-space 只对 `kernel.matmul` 生效，不扩展到 `kernel.binary_elewise`、`kernel.select`、`kernel.exp`、`kernel.reduce` 或 `kernel.img2col*`。
- `space` attribute 只要求是合法 `NnMemorySpaceAttr`；不要求与 `lhs/rhs/out` 任一 operand 的 space 相同，也不重新定义为 out space 或执行主导 space。
- `kernel.matmul` 不接受批维 broadcast 或隐式 transpose。

- 返回值：

- 返回 `KernelMatmulOp`。
- 结果写入 `out`。

### `class KernelImg2col1dOp(out: SSAValue | Operation, input_value: SSAValue | Operation, k: SSAValue | Operation, s: SSAValue | Operation, d: SSAValue | Operation, p_left: SSAValue | Operation, p_right: SSAValue | Operation, space: NnMemorySpaceAttr)`

- api：`class KernelImg2col1dOp(out: SSAValue | Operation, input_value: SSAValue | Operation, k: SSAValue | Operation, s: SSAValue | Operation, d: SSAValue | Operation, p_left: SSAValue | Operation, p_right: SSAValue | Operation, space: NnMemorySpaceAttr)`

- 功能说明：

- 对 1D 输入 memory 执行窗口展开，并把结构化结果写入输出 operand。

- 参数：

- `input(!nn.memory<...>)`：输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `k(i64)`：卷积核宽度。
- `s(i64)`：步长。
- `d(i64)`：dilation。
- `p_left(i64)`：左 padding。
- `p_right(i64)`：右 padding。
- `space(#nn.space<...>)`：op 的空间属性。

- 使用示例：

```mlir
%out = dma.alloc value : !nn.memory<f16, [N, C, K, W_out], GM>
kernel.img2col1d %src, %out {k = 3 : i64, s = 1 : i64, d = 1 : i64, p_left = 0 : i64, p_right = 0 : i64} : value
func.return %out : !nn.memory<f16, [N, C, K, W_out], GM>
```

- 注意事项：

- `out` 必须保持结构化窗口轴，不允许回退为压扁列块结果。
- `input` 必须是 rank=`3` 的 `!nn.memory<elem, [N, C, W], space>`，轴语义固定为 `N/C/W`；不接受压扁输入、缺失 channel 轴或其他 layout 解释。
- `out.shape[2]` 必须机械等于 `k`，`W_out` 必须机械满足 `W_out = floor((W + p_left + p_right - d * (k - 1) - 1) / s) + 1`；若 `out.shape[2] != k`、按 `input.shape[2]` 与 attrs 计算得到的 `W_out` 与 `out.shape[3]` 不一致，或计算结果 `< 1`，必须 verifier 失败。
- `k/s/d/p_left/p_right` 必须与 `input.shape -> out.shape` 的上述关系机械一致，不能只校验 attrs 显式存在而放行错误输出形状。
- `k/s/d/p_left/p_right` 可以来自 `arith.constant`、`symbol.const`、单层 `builtin.unrealized_conversion_cast` 或函数 block argument；当参数或参与公式的 shape 维度不是静态整数时，verifier 只校验 operand 类型、正数/非负静态边界、rank、space、dtype 与窗口轴静态可判定部分，不把动态参数误判为公式不匹配。
- `out` 必须是 rank=`4` 的 `!nn.memory<elem, [N, C, K, W_out], space>`，并与 `input` 保持同一 `element_type` 与 `space`。

- 返回值：

- 返回 `KernelImg2col1dOp`。
- 结果写入 `out`。

### `class KernelImg2col2dOp(out: SSAValue | Operation, input_value: SSAValue | Operation, kh: SSAValue | Operation, kw: SSAValue | Operation, sh: SSAValue | Operation, sw: SSAValue | Operation, dh: SSAValue | Operation, dw: SSAValue | Operation, ph: SSAValue | Operation, pw: SSAValue | Operation, pl: SSAValue | Operation, pr: SSAValue | Operation, space: NnMemorySpaceAttr)`

- api：`class KernelImg2col2dOp(out: SSAValue | Operation, input_value: SSAValue | Operation, kh: SSAValue | Operation, kw: SSAValue | Operation, sh: SSAValue | Operation, sw: SSAValue | Operation, dh: SSAValue | Operation, dw: SSAValue | Operation, ph: SSAValue | Operation, pw: SSAValue | Operation, pl: SSAValue | Operation, pr: SSAValue | Operation, space: NnMemorySpaceAttr)`

- 功能说明：

- 对 2D 输入 memory 执行窗口展开，并把结构化结果写入输出 operand。

- 参数：

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

- 使用示例：

```mlir
%out = dma.alloc value : !nn.memory<f16, [N, C, KH, KW, OH, OW], GM>
kernel.img2col2d %src, %out {kh = 2 : i64, kw = 3 : i64, sh = 1 : i64, sw = 1 : i64, dh = 1 : i64, dw = 1 : i64, ph = 0 : i64, pw = 0 : i64, pl = 0 : i64, pr = 0 : i64} : value
func.return %out : !nn.memory<f16, [N, C, KH, KW, OH, OW], GM>
```

- 注意事项：

- `out` 必须保持结构化窗口轴，不允许回退为压扁列块结果。
- `input` 必须是 rank=`4` 的 `!nn.memory<elem, [N, C, H, W], space>`，轴语义固定为 `N/C/H/W`；不接受 NHWC、压扁输入或其他 layout 解释。
- `out.shape[2:4]` 必须机械等于 `[kh, kw]`；`OH` 必须机械满足 `OH = floor((H + ph + pw - dh * (kh - 1) - 1) / sh) + 1`，`OW` 必须机械满足 `OW = floor((W + pl + pr - dw * (kw - 1) - 1) / sw) + 1`；若 `out.shape[2:4] != [kh, kw]`、按 `input.shape[2:4]` 与 attrs 计算得到的 `OH/OW` 与 `out.shape[4:6]` 不一致，或任一计算结果 `< 1`，必须 verifier 失败。
- `kh/kw/sh/sw/dh/dw/ph/pw/pl/pr` 必须与 `input.shape -> out.shape` 的上述关系机械一致，不能只校验 attrs 显式存在而放行错误输出形状。
- `kh/kw/sh/sw/dh/dw/ph/pw/pl/pr` 可以来自 `arith.constant`、`symbol.const`、单层 `builtin.unrealized_conversion_cast` 或函数 block argument；当参数或参与公式的 shape 维度不是静态整数时，verifier 只校验 operand 类型、正数/非负静态边界、rank、space、dtype 与窗口轴静态可判定部分，不把动态参数误判为公式不匹配。
- `out` 必须是 rank=`6` 的 `!nn.memory<elem, [N, C, KH, KW, OH, OW], space>`，并与 `input` 保持同一 `element_type` 与 `space`。
- `kernel.img2col2d` 的 attrs 必须显式可见，不允许把窗口参数隐藏在“实现自定”逻辑中。

- 返回值：

- 返回 `KernelImg2col2dOp`。
- 结果写入 `out`。

## 测试

- 测试文件：
  - `test/dialect/test_kernel.py`
  - `test/passes/lowering/nn_lowering/test_nn_lowering.py`
- 执行命令：
  - `pytest -q test/dialect/test_kernel.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py`

### 测试目标

- 验证 `NnMemorySpaceAttr` 与 `NnMemoryType` 在 `kernel` 方言中的复用与校验行为。
- 验证基础逐元素算术、比较与选择 op 的 verifier 约束。
- 验证 `kernel.binary_elewise / kernel.exp / kernel.reduce / kernel.reduce_min / kernel.matmul / kernel.img2col*` 的 op 名字、关键 attrs 与 `out` 消费链路合同。
- 验证 `kernel.matmul` mixed-space 合同只放开 out/lhs/rhs space 一致性，不放开 shape、rank 或 dtype。
- 验证 `kernel.matmul` 对非二维 operand、`[M,K] x [K,N] -> [M,N]` 形状不匹配的 verifier 拒绝路径已被机械锁定。
- 验证 `kernel.img2col1d/img2col2d` 的输入 rank/layout 合同与结构化输出合同已被机械锁定。
- 验证 `kernel.img2col1d` 的 `input.shape + attrs -> W_out`、`kernel.img2col2d` 的 `input.shape + attrs -> OH/OW` 公式与拒绝路径已被机械锁定。
- 验证“无 SSA result、显式输出 operand”约束。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-KRN-001 | 公开入口 | 合法 space 创建成功 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_kernel_space_attr_valid`。 | 公开入口在“合法 space 创建成功”场景下可导入、构造、注册或按名称发现。 | `test_kernel_space_attr_valid` |
| TC-KRN-002 | 边界/异常 | 非法 space 被拒绝 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_space_attr_invalid`。 | “非法 space 被拒绝”场景按公开错误语义失败或被拒绝。 | `test_kernel_space_attr_invalid` |
| TC-KRN-003 | 边界/异常 | `shape/stride` rank 不一致 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_memory_type_rank_mismatch`。 | “`shape/stride` rank 不一致”场景按公开错误语义失败或被拒绝。 | `test_kernel_memory_type_rank_mismatch` |
| TC-KRN-004 | 公开入口 | `kernel.binary_elewise(kind="add")` 正常路径 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_kernel_binary_elewise_add_success`。 | 公开入口在“`kernel.binary_elewise(kind="add")` 正常路径”场景下可导入、构造、注册或按名称发现。 | `test_kernel_binary_elewise_add_success` |
| TC-KRN-005 | 边界/异常 | `kernel.binary_elewise(kind="add")` layout 或 dtype 不一致报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_binary_elewise_add_layout_mismatch`。 | “`kernel.binary_elewise(kind="add")` layout 或 dtype 不一致报错”场景按公开错误语义失败或被拒绝。 | `test_kernel_binary_elewise_add_layout_mismatch` |
| TC-KRN-006 | 执行结果 | `kernel.binary_elewise(kind="eq")` 输出类型为 `i1` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_kernel_binary_elewise_compare_output_type`。 | 命令返回码、输出、执行结果或状态变更体现“`kernel.binary_elewise(kind="eq")` 输出类型为 `i1`”场景。 | `test_kernel_binary_elewise_compare_output_type` |
| TC-KRN-007 | 边界/异常 | `kernel.binary_elewise` 比较输出类型或 kind 非法 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_binary_elewise_compare_output_type_error`。 | “`kernel.binary_elewise` 比较输出类型或 kind 非法”场景按公开错误语义失败或被拒绝。 | `test_kernel_binary_elewise_compare_output_type_error` |
| TC-KRN-008 | 边界/异常 | `kernel.select` 条件类型非法 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_select_cond_type_error`。 | “`kernel.select` 条件类型非法”场景按公开错误语义失败或被拒绝。 | `test_kernel_select_cond_type_error` |
| TC-KRN-010 | 执行结果 | op 不产生 SSA result | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_kernel_ops_no_result`。 | 命令返回码、输出、执行结果或状态变更体现“op 不产生 SSA result”场景。 | `test_kernel_ops_no_result` |
| TC-KRN-013 | 符号语义 | `kernel.reduce_min` 正常路径并校验 `axis/keepdim` | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_kernel_reduce_min_success`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“`kernel.reduce_min` 正常路径并校验 `axis/keepdim`”场景。 | `test_kernel_reduce_min_success` |
| TC-KRN-020 | 边界/异常 | `kernel.reduce_min` 拒绝越界 `axis`、非法 `keepdim` 与输出形状不匹配 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_reduce_min_axis_error` / `test_kernel_reduce_min_keepdim_error` / `test_kernel_reduce_min_out_shape_mismatch`。 | “`kernel.reduce_min` 拒绝越界 `axis`、非法 `keepdim` 与输出形状不匹配”场景按公开错误语义失败或被拒绝。 | `test_kernel_reduce_min_axis_error` / `test_kernel_reduce_min_keepdim_error` / `test_kernel_reduce_min_out_shape_mismatch` |
| TC-KRN-014A | 内存/DMA | `kernel.matmul` 允许 out/lhs/rhs mixed-space | 准备 out@tsm、lhs@tlm1、rhs@tlm2 且 shape/dtype 合法的公开 memory operand。 | 运行 `test_kernel_matmul_allows_mixed_spaces`。 | `kernel.matmul` verifier 通过，不要求 operand space 与 `space` attribute 一致。 | `test_kernel_matmul_allows_mixed_spaces` |
| TC-KRN-014 | 边界/异常 | `kernel.matmul` 拒绝 dtype mismatch | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_matmul_dtype_mismatch`。 | “`kernel.matmul` 拒绝 dtype mismatch”场景按公开错误语义失败或被拒绝。 | `test_kernel_matmul_dtype_mismatch` |
| TC-KRN-015 | 边界/异常 | `kernel.matmul` 拒绝非二维 operand 与 `[M,K] x [K,N] -> [M,N]` shape 失配 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_matmul_rank_shape_contract`。 | “`kernel.matmul` 拒绝非二维 operand 与 `[M,K] x [K,N] -> [M,N]` shape 失配”场景按公开错误语义失败或被拒绝。 | `test_kernel_matmul_rank_shape_contract` |
| TC-KRN-017 | 执行结果 | `kernel.img2col1d/img2col2d` 保持结构化输出与显式窗口 attrs | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_kernel_img2col_structured_contract`。 | 命令返回码、输出、执行结果或状态变更体现“`kernel.img2col1d/img2col2d` 保持结构化输出与显式窗口 attrs”场景。 | `test_kernel_img2col_structured_contract` |
| TC-KRN-018 | 边界/异常 | `kernel.img2col1d/img2col2d` 拒绝非法输入 rank 或 layout | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_img2col_input_rank_layout_contract`。 | “`kernel.img2col1d/img2col2d` 拒绝非法输入 rank 或 layout”场景按公开错误语义失败或被拒绝。 | `test_kernel_img2col_input_rank_layout_contract` |
| TC-KRN-019 | 边界/异常 | `kernel.img2col1d/img2col2d` 拒绝 `input.shape + attrs` 推导出的 `W_out/OH/OW` 与 `out.shape` 不一致、公式结果 `< 1` 或窗口轴不等于 `k/[kh,kw]` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_img2col_output_extent_contract`。 | “`kernel.img2col1d/img2col2d` 拒绝 `input.shape + attrs` 推导出的 `W_out/OH/OW` 与 `out.shape` 不一致、公式结果 `< 1` 或窗口轴不等于 `k/[kh,kw]`”场景按公开错误语义失败或被拒绝。 | `test_kernel_img2col_output_extent_contract` |
| TC-KRN-024 | 边界/异常 | `kernel.binary_elewise` 支持公开 kind 矩阵并拒绝非字符串 kind | 准备公开 kind 与非法 kind 类型。 | 运行 `test_kernel_binary_elewise_public_kind_matrix`。 | 算术 / 比较 kind 可通过 verifier；非字符串 kind 按公开错误语义拒绝。 | `test_kernel_binary_elewise_public_kind_matrix` |
| TC-KRN-025 | 边界/异常 | `kernel.matmul` mixed-space 矩阵与非法 space 拒绝边界 | 准备不同合法 memory space 的 `lhs/rhs/out` 与非法属性 space 组合。 | 运行 `test_kernel_matmul_space_contract_matrix`。 | 合法 mixed-space 场景通过 verifier；非法 space 名称按公开错误语义失败。 | `test_kernel_matmul_space_contract_matrix` |
| TC-KRN-026 | 边界/异常 | `kernel.img2col1d` 支持 `symbol.const` / cast 参数并拒绝非法参数类型和值 | 准备 symbol、cast、动态 symbol、动态 shape 与非法参数 operand。 | 运行 `test_kernel_img2col1d_public_param_operand_matrix`。 | 静态 symbol / cast 参数可通过，动态场景跳过机械 shape 推导；非法参数类型、非正窗口与负 padding 被拒绝。 | `test_kernel_img2col1d_public_param_operand_matrix` |
| TC-KRN-027 | 边界/异常 | `kernel.img2col2d` 拒绝 space/dtype/window 失配并支持动态参数和动态 shape | 准备 2D img2col 的 space、dtype、窗口轴、动态 symbol 与动态 shape 组合。 | 运行 `test_kernel_img2col2d_public_contract_matrix`。 | 非法 space/dtype/window 失配被拒绝；动态参数或动态 shape 不误报静态合同失败。 | `test_kernel_img2col2d_public_contract_matrix` |
| TC-KRN-028 | 边界/异常 | `kernel.reduce` 通用入口覆盖 `kind/axis/keepdim/shape` 公开矩阵 | 准备 `sum/min/max`、不同 axis/keepdim 形态与非法输出。 | 运行 `test_kernel_reduce_public_kind_axis_keepdim_matrix`。 | 合法通用 reduce 通过；非法 kind、dtype、space、shape 按公开错误语义失败。 | `test_kernel_reduce_public_kind_axis_keepdim_matrix` |
| TC-KRN-029 | 边界/异常 | `kernel.reduce_min` 拒绝 dtype 与 space 不一致 | 准备 dtype、输出 space 与属性 space 失配场景。 | 运行 `test_kernel_reduce_min_dtype_space_matrix`。 | `kernel.reduce_min` 对 dtype 和 space 失配按公开错误语义失败。 | `test_kernel_reduce_min_dtype_space_matrix` |
