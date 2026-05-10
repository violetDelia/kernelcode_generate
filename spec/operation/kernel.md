# kernel.md

## 功能简介

`kernel_gen.operation.kernel` 定义 out-first kernel operation helper。该模块对齐 `kernel` dialect 的无结果写回语义：调用方显式传入 `out`，helper 只校验公开 `Memory` 元信息并返回 `None`，不创建新 `Memory`，不提供隐式 broadcast，不把 helper 上提到 `kernel_gen.operation` 顶层。

## API 列表

- `class KernelBinaryElewiseKind(Enum)`
- `binary_elewise(out: Memory, lhs: Memory, rhs: Memory, *, kind: KernelBinaryElewiseKind) -> None`
- `add(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `sub(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `mul(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `div(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `truediv(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `eq(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `ne(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `lt(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `le(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `gt(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `ge(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `matmul(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `img2col1d(out: Memory, input_value: Memory, k: int | SymbolDim, s: int | SymbolDim = 1, d: int | SymbolDim = 1, p_left: int | SymbolDim = 0, p_right: int | SymbolDim = 0) -> None`
- `img2col2d(out: Memory, input_value: Memory, kh: int | SymbolDim, kw: int | SymbolDim, sh: int | SymbolDim = 1, sw: int | SymbolDim = 1, dh: int | SymbolDim = 1, dw: int | SymbolDim = 1, ph: int | SymbolDim = 0, pw: int | SymbolDim = 0, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> None`
- `kernel_gen.operation.kernel`

## 文档信息

- `spec`：`spec/operation/kernel.md`
- `功能实现`：
  - `kernel_gen/operation/kernel/__init__.py`：公开子模块导出。
  - `kernel_gen/operation/kernel/elementwise.py`：二元逐元素算术与比较 helper。
  - `kernel_gen/operation/kernel/structured.py`：`matmul` 与 `img2col` helper。
  - `kernel_gen/operation/__init__.py`：只导出 `kernel` 子模块，不上提 out-first helper。
- `test`：
  - `test/operation/kernel/test_elementwise.py`
  - `test/operation/kernel/test_structured.py`
  - `test/operation/kernel/test_package.py`
  - `test/operation/test_package.py`
- `expectation`：
  - `expectation/operation/kernel/**` 是本计划授权合同验收资产。

## 依赖

- `spec/symbol_variable/memory.md`：定义 `Memory`、`MemorySpace`、`shape`、`stride`、`dtype`、`format` 公开语义。
- `spec/symbol_variable/symbol_dim.md`：定义 `SymbolDim` 与符号整数表达。
- `spec/symbol_variable/type.md`：定义 `NumericType`、`Farmat` 与 `NumericType.Bool`。
- `spec/dialect/kernel.md`：定义 `kernel.binary_elewise`、`kernel.matmul`、`kernel.img2col1d` 与 `kernel.img2col2d` IR 写回语义。
- `spec/dsl/ast/plugin/kernel.md`：定义 Python DSL 中 kernel helper 到 AST 的解析关系。
- `spec/dsl/ast/nodes/kernel.md`：定义 kernel AST 节点到 MLIR 的发射关系。

## 术语

- out-first：第一个参数为写回目标 `out`，helper 成功时返回 `None`。
- 算术 kind：`ADD`、`SUB`、`MUL`、`DIV`、`TRUEDIV`。
- 比较 kind：`EQ`、`NE`、`LT`、`LE`、`GT`、`GE`。

## API详细说明

### `class KernelBinaryElewiseKind(Enum)`

- api：`class KernelBinaryElewiseKind(Enum)`
- 参数：无。
- 返回值：枚举类型；成员固定为 `ADD`、`SUB`、`MUL`、`DIV`、`TRUEDIV`、`EQ`、`NE`、`LT`、`LE`、`GT`、`GE`。
- 使用示例：

  ```python
  from kernel_gen.operation import kernel

  kind = kernel.KernelBinaryElewiseKind.ADD
  ```
- 功能说明：定义 `binary_elewise(...)` 的合法 `kind` 输入集合。
- 注意事项：字符串 `"add"`、`"eq"` 或其它字符串不是合法公开输入；调用方必须传 `KernelBinaryElewiseKind` 成员。

### `binary_elewise(out: Memory, lhs: Memory, rhs: Memory, *, kind: KernelBinaryElewiseKind) -> None`

- api：`binary_elewise(out: Memory, lhs: Memory, rhs: Memory, *, kind: KernelBinaryElewiseKind) -> None`
- 参数：
  - `out`：写回目标；类型 `Memory`；无默认值；不允许 `None`；`shape`、`stride`、`space` 必须与 `lhs`、`rhs` 一致。
  - `lhs`：左输入；类型 `Memory`；无默认值；不允许 `None`；不被 helper 修改。
  - `rhs`：右输入；类型 `Memory`；无默认值；不允许 `None`；不被 helper 修改。
  - `kind`：二元 op 种类；类型 `KernelBinaryElewiseKind`；只能以 keyword 传入；不允许字符串。
- 返回值：`None`；非法输入抛出 `KernelCodeError`。
- 使用示例：

  ```python
  from kernel_gen.operation import kernel
  from kernel_gen.symbol_variable.memory import Memory
  from kernel_gen.symbol_variable.type import NumericType

  out = Memory([16, 32], NumericType.Float32)
  lhs = Memory([16, 32], NumericType.Float32)
  rhs = Memory([16, 32], NumericType.Float32)

  kernel.binary_elewise(out, lhs, rhs, kind=kernel.KernelBinaryElewiseKind.ADD)
  ```
- 功能说明：校验 out-first 二元逐元素 kernel 写回合同。
- 注意事项：算术 kind 要求 `out/lhs/rhs` dtype 一致；比较 kind 要求 `out.dtype` 为 `NumericType.Bool`，`lhs/rhs` dtype 可不同；不做隐式 broadcast、dtype 提升、layout 转换或空间转换。

### `add(out: Memory, lhs: Memory, rhs: Memory) -> None`

- api：`add(out: Memory, lhs: Memory, rhs: Memory) -> None`
- 参数：
  - `out`：写回目标；类型 `Memory`；无默认值；不允许 `None`；必须满足 `binary_elewise(..., kind=ADD)` 的 shape/stride/space/dtype 合同。
  - `lhs`：左输入；类型 `Memory`；无默认值；不允许 `None`。
  - `rhs`：右输入；类型 `Memory`；无默认值；不允许 `None`。
- 返回值：`None`；非法输入抛出 `KernelCodeError`。
- 使用示例：

  ```python
  from kernel_gen.operation import kernel

  kernel.add(out, lhs, rhs)
  ```
- 功能说明：执行 `binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.ADD)` 的公开便捷入口。
- 注意事项：该 helper 在 DSL 中 lower 到 `kernel.binary_elewise(kind="add")`，不会生成 `kernel.add` dialect op。

### `sub(out: Memory, lhs: Memory, rhs: Memory) -> None`

- api：`sub(out: Memory, lhs: Memory, rhs: Memory) -> None`
- 参数：
  - `out`：写回目标；类型 `Memory`；无默认值；不允许 `None`；必须满足算术 binary elewise 合同。
  - `lhs`：左输入；类型 `Memory`；无默认值；不允许 `None`。
  - `rhs`：右输入；类型 `Memory`；无默认值；不允许 `None`。
- 返回值：`None`；非法输入抛出 `KernelCodeError`。
- 使用示例：

  ```python
  from kernel_gen.operation import kernel

  kernel.sub(out, lhs, rhs)
  ```
- 功能说明：执行 `binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.SUB)`。
- 注意事项：在 DSL 中 lower 到 `kernel.binary_elewise(kind="sub")`。

### `mul(out: Memory, lhs: Memory, rhs: Memory) -> None`

- api：`mul(out: Memory, lhs: Memory, rhs: Memory) -> None`
- 参数：
  - `out`：写回目标；类型 `Memory`；无默认值；不允许 `None`；必须满足算术 binary elewise 合同。
  - `lhs`：左输入；类型 `Memory`；无默认值；不允许 `None`。
  - `rhs`：右输入；类型 `Memory`；无默认值；不允许 `None`。
- 返回值：`None`；非法输入抛出 `KernelCodeError`。
- 使用示例：

  ```python
  from kernel_gen.operation import kernel

  kernel.mul(out, lhs, rhs)
  ```
- 功能说明：执行 `binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.MUL)`。
- 注意事项：在 DSL 中 lower 到 `kernel.binary_elewise(kind="mul")`。

### `div(out: Memory, lhs: Memory, rhs: Memory) -> None`

- api：`div(out: Memory, lhs: Memory, rhs: Memory) -> None`
- 参数：
  - `out`：写回目标；类型 `Memory`；无默认值；不允许 `None`；必须满足算术 binary elewise 合同。
  - `lhs`：左输入；类型 `Memory`；无默认值；不允许 `None`。
  - `rhs`：右输入；类型 `Memory`；无默认值；不允许 `None`。
- 返回值：`None`；非法输入抛出 `KernelCodeError`。
- 使用示例：

  ```python
  from kernel_gen.operation import kernel

  kernel.div(out, lhs, rhs)
  ```
- 功能说明：执行 `binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.DIV)`。
- 注意事项：在 DSL 中 lower 到 `kernel.binary_elewise(kind="div")`。

### `truediv(out: Memory, lhs: Memory, rhs: Memory) -> None`

- api：`truediv(out: Memory, lhs: Memory, rhs: Memory) -> None`
- 参数：
  - `out`：写回目标；类型 `Memory`；无默认值；不允许 `None`；必须满足算术 binary elewise 合同。
  - `lhs`：左输入；类型 `Memory`；无默认值；不允许 `None`。
  - `rhs`：右输入；类型 `Memory`；无默认值；不允许 `None`。
- 返回值：`None`；非法输入抛出 `KernelCodeError`。
- 使用示例：

  ```python
  from kernel_gen.operation import kernel

  kernel.truediv(out, lhs, rhs)
  ```
- 功能说明：执行 `binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.TRUEDIV)`。
- 注意事项：在 DSL 中 lower 到 `kernel.binary_elewise(kind="truediv")`。

### `eq(out: Memory, lhs: Memory, rhs: Memory) -> None`

- api：`eq(out: Memory, lhs: Memory, rhs: Memory) -> None`
- 参数：
  - `out`：写回目标；类型 `Memory`；无默认值；不允许 `None`；dtype 必须为 `NumericType.Bool`。
  - `lhs`：左输入；类型 `Memory`；无默认值；不允许 `None`；shape/stride/space 必须与 `out` 一致。
  - `rhs`：右输入；类型 `Memory`；无默认值；不允许 `None`；shape/stride/space 必须与 `out` 一致。
- 返回值：`None`；非法输入抛出 `KernelCodeError`。
- 使用示例：

  ```python
  from kernel_gen.operation import kernel

  kernel.eq(out_bool, lhs, rhs)
  ```
- 功能说明：执行 `binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.EQ)`。
- 注意事项：在 DSL 中 lower 到 `kernel.binary_elewise(kind="eq")`；`lhs/rhs` dtype 可不同。

### `ne(out: Memory, lhs: Memory, rhs: Memory) -> None`

- api：`ne(out: Memory, lhs: Memory, rhs: Memory) -> None`
- 参数：
  - `out`：写回目标；类型 `Memory`；无默认值；不允许 `None`；dtype 必须为 `NumericType.Bool`。
  - `lhs`：左输入；类型 `Memory`；无默认值；不允许 `None`。
  - `rhs`：右输入；类型 `Memory`；无默认值；不允许 `None`。
- 返回值：`None`；非法输入抛出 `KernelCodeError`。
- 使用示例：

  ```python
  from kernel_gen.operation import kernel

  kernel.ne(out_bool, lhs, rhs)
  ```
- 功能说明：执行 `binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.NE)`。
- 注意事项：在 DSL 中 lower 到 `kernel.binary_elewise(kind="ne")`；`lhs/rhs` dtype 可不同。

### `lt(out: Memory, lhs: Memory, rhs: Memory) -> None`

- api：`lt(out: Memory, lhs: Memory, rhs: Memory) -> None`
- 参数：
  - `out`：写回目标；类型 `Memory`；无默认值；不允许 `None`；dtype 必须为 `NumericType.Bool`。
  - `lhs`：左输入；类型 `Memory`；无默认值；不允许 `None`。
  - `rhs`：右输入；类型 `Memory`；无默认值；不允许 `None`。
- 返回值：`None`；非法输入抛出 `KernelCodeError`。
- 使用示例：

  ```python
  from kernel_gen.operation import kernel

  kernel.lt(out_bool, lhs, rhs)
  ```
- 功能说明：执行 `binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.LT)`。
- 注意事项：在 DSL 中 lower 到 `kernel.binary_elewise(kind="lt")`；`lhs/rhs` dtype 可不同。

### `le(out: Memory, lhs: Memory, rhs: Memory) -> None`

- api：`le(out: Memory, lhs: Memory, rhs: Memory) -> None`
- 参数：
  - `out`：写回目标；类型 `Memory`；无默认值；不允许 `None`；dtype 必须为 `NumericType.Bool`。
  - `lhs`：左输入；类型 `Memory`；无默认值；不允许 `None`。
  - `rhs`：右输入；类型 `Memory`；无默认值；不允许 `None`。
- 返回值：`None`；非法输入抛出 `KernelCodeError`。
- 使用示例：

  ```python
  from kernel_gen.operation import kernel

  kernel.le(out_bool, lhs, rhs)
  ```
- 功能说明：执行 `binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.LE)`。
- 注意事项：在 DSL 中 lower 到 `kernel.binary_elewise(kind="le")`；`lhs/rhs` dtype 可不同。

### `gt(out: Memory, lhs: Memory, rhs: Memory) -> None`

- api：`gt(out: Memory, lhs: Memory, rhs: Memory) -> None`
- 参数：
  - `out`：写回目标；类型 `Memory`；无默认值；不允许 `None`；dtype 必须为 `NumericType.Bool`。
  - `lhs`：左输入；类型 `Memory`；无默认值；不允许 `None`。
  - `rhs`：右输入；类型 `Memory`；无默认值；不允许 `None`。
- 返回值：`None`；非法输入抛出 `KernelCodeError`。
- 使用示例：

  ```python
  from kernel_gen.operation import kernel

  kernel.gt(out_bool, lhs, rhs)
  ```
- 功能说明：执行 `binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.GT)`。
- 注意事项：在 DSL 中 lower 到 `kernel.binary_elewise(kind="gt")`；`lhs/rhs` dtype 可不同。

### `ge(out: Memory, lhs: Memory, rhs: Memory) -> None`

- api：`ge(out: Memory, lhs: Memory, rhs: Memory) -> None`
- 参数：
  - `out`：写回目标；类型 `Memory`；无默认值；不允许 `None`；dtype 必须为 `NumericType.Bool`。
  - `lhs`：左输入；类型 `Memory`；无默认值；不允许 `None`。
  - `rhs`：右输入；类型 `Memory`；无默认值；不允许 `None`。
- 返回值：`None`；非法输入抛出 `KernelCodeError`。
- 使用示例：

  ```python
  from kernel_gen.operation import kernel

  kernel.ge(out_bool, lhs, rhs)
  ```
- 功能说明：执行 `binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.GE)`。
- 注意事项：在 DSL 中 lower 到 `kernel.binary_elewise(kind="ge")`；`lhs/rhs` dtype 可不同。

### `matmul(out: Memory, lhs: Memory, rhs: Memory) -> None`

- api：`matmul(out: Memory, lhs: Memory, rhs: Memory) -> None`
- 参数：
  - `out`：写回目标；类型 `Memory`；无默认值；不允许 `None`；rank 必须为 2；shape 必须为 `[lhs.M, rhs.N]`。
  - `lhs`：左输入；类型 `Memory`；无默认值；不允许 `None`；rank 必须为 2。
  - `rhs`：右输入；类型 `Memory`；无默认值；不允许 `None`；rank 必须为 2。
- 返回值：`None`；非法输入抛出 `KernelCodeError` 或 Python `TypeError`。
- 使用示例：

  ```python
  from kernel_gen.operation import kernel
  from kernel_gen.symbol_variable.memory import Memory, MemorySpace
  from kernel_gen.symbol_variable.type import NumericType

  out = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.TSM)
  lhs = Memory(["M", "K"], NumericType.Float32, space=MemorySpace.TLM1)
  rhs = Memory(["K", "N"], NumericType.Float32, space=MemorySpace.TLM2)

  kernel.matmul(out, lhs, rhs)
  ```
- 功能说明：校验 out-first rank-2 matrix multiply 写回合同。
- 注意事项：`lhs.shape[1]` 必须等于 `rhs.shape[0]`；`out.shape` 必须等于 `[lhs.shape[0], rhs.shape[1]]`；三者 dtype 必须一致；允许三者位于不同 `MemorySpace`；不接受 `memoryspace` 参数。

### `img2col1d(out: Memory, input_value: Memory, k: int | SymbolDim, s: int | SymbolDim = 1, d: int | SymbolDim = 1, p_left: int | SymbolDim = 0, p_right: int | SymbolDim = 0) -> None`

- api：`img2col1d(out: Memory, input_value: Memory, k: int | SymbolDim, s: int | SymbolDim = 1, d: int | SymbolDim = 1, p_left: int | SymbolDim = 0, p_right: int | SymbolDim = 0) -> None`
- 参数：
  - `out`：写回目标；类型 `Memory`；无默认值；不允许 `None`；shape 必须为 `[N, C, k, W_out]`。
  - `input_value`：输入 memory；类型 `Memory`；无默认值；不允许 `None`；format 必须为 `Farmat.Norm`；rank 必须为 3，语义为 `[N, C, W]`。
  - `k`：卷积窗口宽度；类型 `int | SymbolDim`；默认值无；静态整数必须大于 0。
  - `s`：步长；类型 `int | SymbolDim`；默认值 `1`；静态整数必须大于 0。
  - `d`：dilation；类型 `int | SymbolDim`；默认值 `1`；静态整数必须大于 0。
  - `p_left`：左 padding；类型 `int | SymbolDim`；默认值 `0`；静态整数必须大于等于 0。
  - `p_right`：右 padding；类型 `int | SymbolDim`；默认值 `0`；静态整数必须大于等于 0。
- 返回值：`None`；非法输入抛出 `KernelCodeError`。
- 使用示例：

  ```python
  from kernel_gen.operation import kernel

  kernel.img2col1d(out, input_value, k=3, s=1, d=1, p_left=1, p_right=1)
  ```
- 功能说明：校验一维 img2col out-first 写回合同。
- 注意事项：`W_out = ((W + p_left + p_right - d * (k - 1) - 1) // s) + 1`；`out` 的 dtype、space、format、stride 必须与该公式构造的公开结果一致；`bool` 不属于合法窗口参数。

### `img2col2d(out: Memory, input_value: Memory, kh: int | SymbolDim, kw: int | SymbolDim, sh: int | SymbolDim = 1, sw: int | SymbolDim = 1, dh: int | SymbolDim = 1, dw: int | SymbolDim = 1, ph: int | SymbolDim = 0, pw: int | SymbolDim = 0, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> None`

- api：`img2col2d(out: Memory, input_value: Memory, kh: int | SymbolDim, kw: int | SymbolDim, sh: int | SymbolDim = 1, sw: int | SymbolDim = 1, dh: int | SymbolDim = 1, dw: int | SymbolDim = 1, ph: int | SymbolDim = 0, pw: int | SymbolDim = 0, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> None`
- 参数：
  - `out`：写回目标；类型 `Memory`；无默认值；不允许 `None`；shape 必须为 `[N, C, kh, kw, H_out, W_out]`。
  - `input_value`：输入 memory；类型 `Memory`；无默认值；不允许 `None`；format 必须为 `Farmat.Norm`；rank 必须为 4，语义为 `[N, C, H, W]`。
  - `kh`：窗口高度；类型 `int | SymbolDim`；无默认值；静态整数必须大于 0。
  - `kw`：窗口宽度；类型 `int | SymbolDim`；无默认值；静态整数必须大于 0。
  - `sh`：高度步长；类型 `int | SymbolDim`；默认值 `1`；静态整数必须大于 0。
  - `sw`：宽度步长；类型 `int | SymbolDim`；默认值 `1`；静态整数必须大于 0。
  - `dh`：高度 dilation；类型 `int | SymbolDim`；默认值 `1`；静态整数必须大于 0。
  - `dw`：宽度 dilation；类型 `int | SymbolDim`；默认值 `1`；静态整数必须大于 0。
  - `ph`：顶部 padding；类型 `int | SymbolDim`；默认值 `0`；静态整数必须大于等于 0。
  - `pw`：底部 padding；类型 `int | SymbolDim`；默认值 `0`；静态整数必须大于等于 0。
  - `pl`：左侧 padding；类型 `int | SymbolDim`；默认值 `0`；静态整数必须大于等于 0。
  - `pr`：右侧 padding；类型 `int | SymbolDim`；默认值 `0`；静态整数必须大于等于 0。
- 返回值：`None`；非法输入抛出 `KernelCodeError`。
- 使用示例：

  ```python
  from kernel_gen.operation import kernel

  kernel.img2col2d(out, input_value, kh=3, kw=3, sh=1, sw=1, ph=1, pw=1, pl=1, pr=1)
  ```
- 功能说明：校验二维 img2col out-first 写回合同。
- 注意事项：`H_out = ((H + ph + pw - dh * (kh - 1) - 1) // sh) + 1`；`W_out = ((W + pl + pr - dw * (kw - 1) - 1) // sw) + 1`；`out` 的 dtype、space、format、stride 必须与该公式构造的公开结果一致；`bool` 不属于合法窗口参数。

### `kernel_gen.operation.kernel`

- api：`kernel_gen.operation.kernel`
- 参数：无。
- 返回值：`kernel` 子模块对象；可通过 `from kernel_gen.operation import kernel` 导入。
- 使用示例：

  ```python
  from kernel_gen.operation import kernel

  assert kernel.add is not None
  ```
- 功能说明：在 `kernel_gen.operation` 包根暴露完整 `kernel` 子模块。
- 注意事项：`kernel.add`、`kernel.matmul`、`kernel.img2col2d` 等 helper 不上提到 `kernel_gen.operation` 顶层；调用方必须通过 `kernel_gen.operation.kernel` 或 `from kernel_gen.operation import kernel` 访问。

## 测试

- 测试文件：
  - `test/operation/kernel/test_elementwise.py`
  - `test/operation/kernel/test_structured.py`
  - `test/operation/kernel/test_package.py`
  - `test/operation/test_package.py`
- 执行命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/kernel test/operation/test_package.py`
- 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.operation.kernel`

### 测试目标

- 验证 kernel operation helper 的 out-first 返回 `None` 合同。
- 验证 `binary_elewise` 算术与比较的 shape、stride、space、dtype 和 enum kind 边界。
- 验证 `matmul` 的 mixed-space、rank、shape、dtype 和 `memoryspace` 非目标边界。
- 验证 `img2col1d/2d` 的静态与符号窗口参数、输出元信息和错误边界。
- 验证 `kernel_gen.operation` 只导出 `kernel` 子模块，不上提 out-first helper。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-OP-KERNEL-ELEWISE-001 | 算术 helper | `add/sub/mul/div/truediv` 成功写回 | `out/lhs/rhs` shape、stride、space、dtype 一致 | 运行 operation kernel pytest | helper 返回 `None` | `test_kernel_arithmetic_helpers_are_out_first_and_return_none` |
| TC-OP-KERNEL-ELEWISE-002 | 比较 helper | `eq/ne/lt/le/gt/ge` 写入 Bool out | `out.dtype=Bool`，`lhs/rhs` dtype 可不同 | 运行 operation kernel pytest | helper 返回 `None` | `test_kernel_compare_helpers_require_bool_out_and_allow_input_dtype_mismatch` |
| TC-OP-KERNEL-ELEWISE-003 | 错误边界 | 字符串 kind、shape mismatch、dtype mismatch | 构造非法公开输入 | 运行 operation kernel pytest | 抛出 `KernelCodeError` | `test_kernel_binary_elewise_rejects_non_api_kind_and_mismatched_metadata` |
| TC-OP-KERNEL-STRUCTURED-001 | matmul | mixed-space rank-2 matmul | `lhs[M,K]`、`rhs[K,N]`、`out[M,N]` | 运行 structured pytest | 返回 `None`；`memoryspace` keyword 被拒绝 | `test_kernel_matmul_supports_mixed_space_and_rejects_non_api_memoryspace` |
| TC-OP-KERNEL-STRUCTURED-002 | img2col1d | 静态与符号窗口参数 | Norm rank-3 input 与匹配 out | 运行 structured pytest | 返回 `None`；错误 shape 被拒绝 | `test_kernel_img2col1d_validates_expected_out_memory` |
| TC-OP-KERNEL-STRUCTURED-003 | img2col2d | 静态与符号窗口参数 | Norm rank-4 input 与匹配 out | 运行 structured pytest | 返回 `None`；错误 format 被拒绝 | `test_kernel_img2col2d_validates_expected_out_memory` |
| TC-OP-KERNEL-PKG-001 | package 导出 | `kernel` 子模块可达 | 导入 `kernel_gen.operation` | 运行 package pytest | `operation.kernel is kernel` | `test_operation_package_exports_kernel_submodule_only` |
