# kernel.md

## 功能简介

定义 `kernel_gen.dsl.ast.nodes.kernel` 中的 out-first kernel AST 节点。节点只负责把 `kernel_gen.operation.kernel` 公开 helper lower 到既有 `kernel` dialect op；`kernel.add/sub/...` helper 不生成同名 dialect op，统一发射为 `kernel.binary_elewise`。

## API 列表

- `class KernelBinaryElewiseAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, kind: KernelBinaryElewiseKind, location: SourceLocation | None = None)`
- `class KernelAddAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class KernelSubAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class KernelMulAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class KernelDivAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class KernelTrueDivAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class KernelEqAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class KernelNeAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class KernelLtAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class KernelLeAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class KernelGtAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class KernelGeAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class KernelMatmulAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `class KernelImg2Col1dAST(out: ValueAST, input_value: ValueAST, k: ValueAST, s: ValueAST | None = None, d: ValueAST | None = None, p_left: ValueAST | None = None, p_right: ValueAST | None = None, location: SourceLocation | None = None)`
- `class KernelImg2Col2dAST(out: ValueAST, input_value: ValueAST, kh: ValueAST, kw: ValueAST, sh: ValueAST | None = None, sw: ValueAST | None = None, dh: ValueAST | None = None, dw: ValueAST | None = None, ph: ValueAST | None = None, pw: ValueAST | None = None, pl: ValueAST | None = None, pr: ValueAST | None = None, location: SourceLocation | None = None)`

## 文档信息

- `spec`：`spec/dsl/ast/nodes/kernel.md`
- `功能实现`：`kernel_gen/dsl/ast/nodes/kernel.py`
- `test`：`test/dsl/ast/nodes/test_kernel.py`
- `expectation`：`expectation/dsl/mlir_gen/dialect/kernel/**`

## 依赖

- `spec/operation/kernel.md`：operation helper 的公开参数和校验语义。
- `spec/dialect/kernel.md`：目标 kernel dialect op。
- `spec/dsl/ast/plugin/kernel.md`：Python helper 到本节点的注册关系。
- `spec/dsl/ast/nodes/basic.md`：`ValueAST`、`StatementAST`、`MemoryAST`。
- `spec/dsl/ast/nodes/symbol.md`：img2col 参数的 symbol operand。

## API 详细说明

### `class KernelBinaryElewiseAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, kind: KernelBinaryElewiseKind, location: SourceLocation | None = None)`

- 参数：
  - `out`：写回目标 memory 节点；必须 lower 为 `!nn.memory`。
  - `lhs`：左输入 memory 节点；必须 lower 为 `!nn.memory`。
  - `rhs`：右输入 memory 节点；必须 lower 为 `!nn.memory`。
  - `kind`：`KernelBinaryElewiseKind` 枚举成员；不接受字符串。
  - `location`：可选源码位置。
- 返回值：构造 `KernelBinaryElewiseAST`；`emit_mlir(...)` 返回 `KernelBinaryElewiseOp`。
- 使用示例：

  ```python
  node = KernelBinaryElewiseAST(out, lhs, rhs, KernelBinaryElewiseKind.ADD)
  ```
- 功能说明：发射 `kernel.binary_elewise(out, lhs, rhs) {kind = ...}`。
- 注意事项：必须复用 `kernel_gen.operation.kernel.binary_elewise(...)` 的公开校验；算术/比较 shape、stride、space、dtype 规则不得在 AST 层另开口径。

### `class KernelAddAST / KernelSubAST / KernelMulAST / KernelDivAST / KernelTrueDivAST / KernelEqAST / KernelNeAST / KernelLtAST / KernelLeAST / KernelGtAST / KernelGeAST`

- 参数：
  - `out`：写回目标 memory 节点。
  - `lhs`：左输入 memory 节点。
  - `rhs`：右输入 memory 节点。
  - `location`：可选源码位置。
- 返回值：对应固定 kind 的 AST 节点；`emit_mlir(...)` 返回 `KernelBinaryElewiseOp`。
- 使用示例：

  ```python
  node = KernelAddAST(out, lhs, rhs)
  ```
- 功能说明：将便捷 helper lower 到 `kernel.binary_elewise`。
- 注意事项：不得生成 `kernel.add`、`kernel.sub` 等不存在的 dialect op；比较节点仍要求输出 memory dtype 为 Bool。

### `class KernelMatmulAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`

- 参数：
  - `out`：rank-2 写回目标 memory 节点。
  - `lhs`：rank-2 左矩阵 memory 节点。
  - `rhs`：rank-2 右矩阵 memory 节点。
  - `location`：可选源码位置。
- 返回值：`KernelMatmulAST`；`emit_mlir(...)` 返回无结果 `KernelMatmulOp`。
- 使用示例：

  ```python
  node = KernelMatmulAST(out, lhs, rhs)
  ```
- 功能说明：发射 out-first `kernel.matmul(out, lhs, rhs)`。
- 注意事项：不接受 `memoryspace` 参数；mixed-space 是否可用以 `spec/operation/kernel.md` 和 `spec/dialect/kernel.md` 为准。

### `class KernelImg2Col1dAST(...)`

- 参数：
  - `out`：写回目标 rank-4 memory 节点。
  - `input_value`：rank-3 输入 memory 节点。
  - `k`、`s`、`d`、`p_left`、`p_right`：窗口参数；必须 lower 为 `!symbol.int`；省略时按 operation kernel 默认值补齐。
  - `location`：可选源码位置。
- 返回值：`KernelImg2Col1dAST`；`emit_mlir(...)` 返回无结果 `KernelImg2col1dOp`。
- 使用示例：

  ```python
  node = KernelImg2Col1dAST(out, input_value, k)
  ```
- 功能说明：发射 out-first `kernel.img2col1d`。
- 注意事项：窗口、stride、dilation 必须为正；padding 必须非负。

### `class KernelImg2Col2dAST(...)`

- 参数：
  - `out`：写回目标 rank-6 memory 节点。
  - `input_value`：rank-4 输入 memory 节点。
  - `kh`、`kw`、`sh`、`sw`、`dh`、`dw`、`ph`、`pw`、`pl`、`pr`：二维窗口参数；必须 lower 为 `!symbol.int`；省略时按 operation kernel 默认值补齐。
  - `location`：可选源码位置。
- 返回值：`KernelImg2Col2dAST`；`emit_mlir(...)` 返回无结果 `KernelImg2col2dOp`。
- 使用示例：

  ```python
  node = KernelImg2Col2dAST(out, input_value, kh, kw, ph=ConstValueAST(1), pw=ConstValueAST(1))
  ```
- 功能说明：发射 out-first `kernel.img2col2d`。
- 注意事项：支持非对称 padding 参数 `ph/pw/pl/pr`；不允许从 AST 层绕过 operation kernel 的输出 shape/stride 校验。

## 测试

- 测试文件：`test/dsl/ast/nodes/test_kernel.py`
- 执行命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/nodes/test_kernel.py`

### 测试目标

- 验证 out-first kernel AST 节点能发射当前公开 kernel dialect op。
- 验证便捷 elementwise AST 节点统一 lower 为 `kernel.binary_elewise`，不产生不存在的 `kernel.add/sub/...` dialect op。
- 验证 `KernelBinaryElewiseAST` 拒绝字符串 kind，只接受 `KernelBinaryElewiseKind`。
- 验证 matmul 与 img2col AST 节点复用 operation kernel 公开校验，不绕开 shape、dtype、rank 和窗口参数边界。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-NODES-KERNEL-001 | pass 改写 | add helper lower | 构造公开 `KernelAddAST`。 | 发射 MLIR。 | 返回 `KernelBinaryElewiseOp(kind="add")`。 | `test_kernel_add_node_emits_binary_elewise_op` |
| TC-DSL-AST-NODES-KERNEL-002 | 边界/异常 | string kind rejected | 构造 `KernelBinaryElewiseAST(..., "add")`。 | 初始化节点。 | 抛 `KernelCodeError`。 | `test_kernel_binary_elewise_node_rejects_string_kind` |
| TC-DSL-AST-NODES-KERNEL-003 | pass 改写 | matmul lower | 构造 mixed-space rank-2 memory。 | 发射 MLIR。 | 返回无结果 `KernelMatmulOp`。 | `test_kernel_matmul_node_emits_matmul_op` |
| TC-DSL-AST-NODES-KERNEL-004 | pass 改写 | img2col2d lower | 构造公开 img2col2d memory 与参数。 | 发射 MLIR。 | 返回 `KernelImg2col2dOp`。 | `test_kernel_img2col2d_node_emits_img2col2d_op` |
