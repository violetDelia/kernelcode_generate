# expectation_dsl_mlir_dma_symbol_closure_plan.md

## 进度

- 更新日期：2026-03-31
- 更新规则：每个任务块进入新子阶段后立即更新本段。
- `E1`：合并完成（main=7704cb0）。
- `E2`：spec 完成（T-20260330-fb75b573）；实现完成（T-20260330-03f1cc3a）；审查通过（T-20260330-f29c2b3c）；补推完成（main=d77e57f）。
- `E3`：实现完成（T-20260331-8e00278e）；复审不通过（T-20260331-120d0d9d，缺 spec/dsl/emit_mlir.md 与 spec/dsl/mlir_gen.md 映射）；spec 修复完成（T-20260331-4ff80dbe）；实现修复完成（T-20260331-cb616bec）；本地合并完成（T-20260331-44d8c436，commit=3b42b59）；补推完成（T-20260331-82cb2f77，origin/main=3b42b59）。
- `E4`：实现完成（T-20260331-cd02880e）；复审不通过（T-20260331-c73395f3，expectation 头部 test 锚点与 spec/test 映射不一致，且 `ne.py` 为 `[immutable-file]` 不可直接改写）；映射修复完成（T-20260331-58bc651f）；复审通过（T-20260331-a57263a0）；spec follow-up 完成（T-20260331-9ad7a358，已将 MGEN-038~041 真实锚点统一回 `test/dsl/test_mlir_gen.py` 并补充 `ne.py` immutable 处理策略）；当前待分发实现跟进（T-20260331-6122deb4，仅处理 `gt/lt/le` 三个 non-immutable expectation 头部 test 锚点，`ne.py` 保持不改）。
- `E5`：未开始。
- `E6`：未开始。
- 当前 expectation 台账：`85` 个脚本中 `76` 通过、`9` 失败。
- 当前外部前置阻塞：无（A2/P12 同步确认已完成）。
- 当前执行中：无。
- 当前建议推进顺序：实现位一旦空闲，立即分发 `E4` 实现跟进（T-20260331-6122deb4）；`E4` 完整关闭后再启动 `E5`，再按依赖推进 `E6`，期间不得抢跑后续 expectation 波次。

## 文件说明

- 功能说明：将当前 `expectation/dsl/mlir_gen/dialect/dma` 与 `expectation/dsl/mlir_gen/dialect/symbol` 的 9 个失败项整理成一份管理员可直接使用的推进计划，明确任务拆分、硬门禁、边界和机械验收口径。
- 使用示例：管理员在分发 expectation 修复链路前，先阅读本文件的 `任务依赖` 与 `任务清单`，仅按 `BLOCKER / READY_IF / DISPATCH_RULE / CLOSE_IF / FAIL_ROUTING` 发放与验收。
- 使用示例：执行者封板时，按各任务下方的 expectation 命令和 pytest 命令逐条回报退出码；若全部为 `0`，再申请关闭对应任务。
- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/expectation_dsl_mlir_dma_symbol_closure_plan.md`](../../ARCHITECTURE/plan/expectation_dsl_mlir_dma_symbol_closure_plan.md)
- `spec`：
  - [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`spec/dialect/dma.md`](../../spec/dialect/dma.md)
  - [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- `功能实现`：
  - [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`kernel_gen/dialect/dma.py`](../../kernel_gen/dialect/dma.py)
  - [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py)
- `test`：
  - [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)
  - [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
  - [`test/dialect/test_dma_dialect.py`](../../test/dialect/test_dma_dialect.py)
  - [`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py)
  - [`agents/codex-multi-agents/agents/大闸蟹/expectation_status.md`](../../agents/codex-multi-agents/agents/大闸蟹/expectation_status.md)

## 计划目的

- 目标不是解释“当前为什么失败”，而是给管理员一份可以直接调度、执行者可以直接落地、审查者可以直接验收的 expectation 收口计划。
- expectation 文件在本计划中是“应该是什么”的质量基线，不受当前实现限制。
- 默认规则仍然是：**不修改 expectation 文件本体**，通过补齐 `spec / 实现 / 测试` 来让 expectation 运行成功。
- 计划最终目标是把当前台账从 `76 / 85` 收口到 `85 / 85`，并同步更新 [`expectation_status.md`](../../agents/codex-multi-agents/agents/大闸蟹/expectation_status.md)。

## 当前失败清单

| 编号 | expectation 文件 | 当前失败摘要 |
| --- | --- | --- |
| F1 | [`expectation/dsl/mlir_gen/dialect/dma/free`](../../expectation/dsl/mlir_gen/dialect/dma/free) | 当前 `build_func_op` 只产出 `func.return`，未产出 expectation 需要的 `dma.free` |
| F2 | [`expectation/dsl/mlir_gen/dialect/dma/view`](../../expectation/dsl/mlir_gen/dialect/dma/view) | 当前 lowering 产出 `dma.view`，但结果 `shape/stride` 与 expectation 要求不一致 |
| F3 | [`expectation/dsl/mlir_gen/dialect/symbol/get_dim.py`](../../expectation/dsl/mlir_gen/dialect/symbol/get_dim.py) | AST 尚不接受 `Memory.get_shape()[axis]` |
| F4 | [`expectation/dsl/mlir_gen/dialect/symbol/get_stride.py`](../../expectation/dsl/mlir_gen/dialect/symbol/get_stride.py) | AST 尚不接受 `Memory.get_stride()[axis]` |
| F5 | [`expectation/dsl/mlir_gen/dialect/symbol/gt.py`](../../expectation/dsl/mlir_gen/dialect/symbol/gt.py) | DSL 公开契约仍只支持 symbol `eq/ge` 比较 |
| F6 | [`expectation/dsl/mlir_gen/dialect/symbol/le.py`](../../expectation/dsl/mlir_gen/dialect/symbol/le.py) | DSL 公开契约仍只支持 symbol `eq/ge` 比较 |
| F7 | [`expectation/dsl/mlir_gen/dialect/symbol/lt.py`](../../expectation/dsl/mlir_gen/dialect/symbol/lt.py) | DSL 公开契约仍只支持 symbol `eq/ge` 比较 |
| F8 | [`expectation/dsl/mlir_gen/dialect/symbol/ne.py`](../../expectation/dsl/mlir_gen/dialect/symbol/ne.py) | DSL 公开契约仍只支持 symbol `eq/ge` 比较；且该 expectation 文件为 `[immutable-file]` |
| F9 | [`expectation/dsl/mlir_gen/dialect/symbol/to_float.py`](../../expectation/dsl/mlir_gen/dialect/symbol/to_float.py) | AST 不接受 `-> float` 注解，且 DSL 未闭环 `float(symbol.int)` |

## 拆分原则

1. `dma.free` 与 `dma.view` 不合并。
   - 两者失败根因不同，验收口径不同，合并后会让管理员误以为同一人可一次性收口同一条 DSL 核心路径。
2. `symbol.get_dim` 与 `symbol.get_stride` 合并为 `E3`。
   - 两者共用 `Memory metadata query` 的 AST/emit/mlir_gen 入口，拆开会让两个人同时改 `kernel_gen/dsl/ast.py`、`kernel_gen/dsl/emit_mlir.py`、`kernel_gen/dsl/mlir_gen.py`。
3. `symbol.gt/le/lt/ne` 合并为 `E4`。
   - 四者共用 symbol compare 公开契约与 lowering 入口；继续拆细只会重复改 `spec/dsl/emit_mlir.md`、`spec/dsl/mlir_gen.md` 与同组测试文件。
4. `symbol.to_float` 单独为 `E5`。
   - 它同时涉及返回注解和内建 `float(...)`，根因与 compare/query 不同。
5. `E6` 只做全量收口，不掺杂新的实现任务。

## 管理执行规则

- 本计划只负责“给管理员的执行规则”，不代替管理员分发，不带 `-to` 指派。
- expectation 链路统一遵循：`spec -> 实现 -> 审查 -> expectation 回归`。
- 默认不得修改 expectation 文件本体；只有用户对某个 expectation 文件明确授权时，才允许修改该 expectation 文件。
- 各任务回报必须显式写明：
  - expectation 文件是否保持只读
  - 变更的 `spec / 实现 / 测试` 文件列表
  - expectation 命令与退出码
  - pytest 命令与退出码
  - 若有 spec 更新，需附“spec 条目 -> 测试函数 -> 实现文件”对照表
- 各任务验收格式统一使用以下字段：
  - `BLOCKER`：当前任务开始前必须解除的阻塞
  - `READY_IF`：管理员可机械判断“允许分发”的条件
  - `DISPATCH_RULE`：分发规则
  - `CLOSE_IF`：允许关闭任务的验收条件
  - `FAIL_ROUTING`：若未满足 `CLOSE_IF` 应退回哪条链路

## 任务依赖

### Wave 0：前置阻塞解除

- `E1 ~ E5` 的共同外部阻塞为：`A2 DONE` 且 `P12 DONE`。
- 未满足该条件时，管理员**不得分发** `E1 ~ E5`。

### Wave 1：主修复链路

- `E1`：无内部前置；但必须等待 `A2/P12`。
- `E2`：依赖 `E1`。
- `E3`：依赖 `E2`。
- `E4`：依赖 `E3`。
- `E5`：依赖 `E4`。

### Wave 2：全量回归

- `E6`：依赖 `E1/E2/E3/E4/E5` 全部完成。

## 任务清单

### E1. `dma.free expectation` 闭环

- 目标文件：[`expectation/dsl/mlir_gen/dialect/dma/free`](../../expectation/dsl/mlir_gen/dialect/dma/free)
- 目标：让 `free(src)` 在 DSL lowering 与 `build_func_op` 链路中显式生成 `dma.free`，同时保留空返回的函数语义。
- 建议修改范围：
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
- 不得修改：
  - [`expectation/dsl/mlir_gen/dialect/dma/free`](../../expectation/dsl/mlir_gen/dialect/dma/free)
- 示例：

```python
def free_kernel(src: "Tensor[f32, 4, 4]"):
    free(src)
```

- `BLOCKER`：`A2`、`P12`
- `READY_IF`：管理员记录中 `A2 DONE` 且 `P12 DONE`
- `DISPATCH_RULE`：`ONLY_IF READY_IF=true`
- 验收标准：
  - `test_emit_mlir_dma_free_statement`
    - 输入：`DmaFreeAST(value=TensorAST("src"))`
    - 预期输出：`emit_node_mlir(...)` 返回 `None`；block 内含且仅含 `1` 个 `DmaFreeOp`
  - `test_build_func_op_supports_dma_free_statement`
    - 输入：`build_func_op(free_kernel, SOURCE_MEMORY)`
    - 预期输出：`FuncOp.body.block.ops` 顺序为 `[DmaFreeOp, func.ReturnOp]`；`ReturnOp.arguments` 长度为 `0`
- 验收命令：

```bash
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/free
PYTHONPATH=. pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_dma_free_statement
PYTHONPATH=. pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_supports_dma_free_statement
PYTHONPATH=. pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_dma_free_statement
```

- `CLOSE_IF`：上述 4 条命令退出码全部为 `0`
- `FAIL_ROUTING`：若 expectation 仍失败，转回 `dsl/emit_mlir + dsl/mlir_gen` 实现链路，不得关闭任务

### E2. `dma.view expectation` 闭环

- 目标文件：[`expectation/dsl/mlir_gen/dialect/dma/view`](../../expectation/dsl/mlir_gen/dialect/dma/view)
- 目标：让 `view(src, offset, size, stride)` 的 lowering 结果类型与 expectation 一致，即 `shape` 来自 `size`、`stride` 来自 DSL 传入的 `stride` 参数，而不是直接复用 operation 返回的 memory 元信息。
- 建议修改范围：
  - [`spec/dialect/dma.md`](../../spec/dialect/dma.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`kernel_gen/dialect/dma.py`](../../kernel_gen/dialect/dma.py)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`test/dialect/test_dma_dialect.py`](../../test/dialect/test_dma_dialect.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
- 不得修改：
  - [`expectation/dsl/mlir_gen/dialect/dma/view`](../../expectation/dsl/mlir_gen/dialect/dma/view)
- 示例：

```python
def view_kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
    return view(src, [1, 1], [2, 2], [1, 1])
```

- `BLOCKER`：`E1`
- `READY_IF`：`E1 CLOSE_IF=true`
- `DISPATCH_RULE`：`ONLY_IF READY_IF=true`
- 验收标准：
  - `test_emit_mlir_dma_view_lowering`
    - 输入：`DmaViewAST(source=src, offset=[1,1], size=[2,2], stride=[1,1])`
    - 预期输出：生成 `1` 个 `DmaViewOp`；`result.type.shape == [2, 2]`；`result.type.stride == [1, 1]`
  - `test_build_func_op_supports_dma_view_helper`
    - 输入：`build_func_op(view_kernel, SOURCE_MEMORY)`
    - 预期输出：函数体含 `1` 个 `DmaViewOp` 与 `1` 个 `func.ReturnOp`；二者类型都与 expectation 中 `EXPECTED_MEMORY` 一致
  - `test_dma_view_accepts_matching_numel_subset_with_explicit_stride`
    - 输入：显式 `shape/stride` operand 与 `result_type.shape/stride` 对齐的 `DmaViewOp`
    - 预期输出：`verify()` 通过
- 验收命令：

```bash
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/view
PYTHONPATH=. pytest -q test/dialect/test_dma_dialect.py -k 'test_dma_view_accepts_matching_numel_subset_with_explicit_stride or test_dma_view_dynamic_symbol_int_layout_operands_valid'
PYTHONPATH=. pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_dma_view_lowering
PYTHONPATH=. pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_dma_view_lowering
PYTHONPATH=. pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_dma_view_helper
```

- `CLOSE_IF`：上述 5 条命令退出码全部为 `0`
- `FAIL_ROUTING`：若 expectation 失败原因落回 verifier，转回 `dialect/dma + dsl/emit_mlir` 链路，不得关闭任务

### E3. `symbol.get_dim/get_stride expectation` 闭环

- 目标文件：
  - [`expectation/dsl/mlir_gen/dialect/symbol/get_dim.py`](../../expectation/dsl/mlir_gen/dialect/symbol/get_dim.py)
  - [`expectation/dsl/mlir_gen/dialect/symbol/get_stride.py`](../../expectation/dsl/mlir_gen/dialect/symbol/get_stride.py)
- 目标：让 `Memory.get_shape()[axis]` 与 `Memory.get_stride()[axis]` 可沿 `AST -> emit_mlir -> build_func_op` 正常 lowering，并把“仅允许 Memory 调用、负轴非法、越界轴非法”写成公开契约。
- 建议修改范围：
  - [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
- 不得修改：
  - [`expectation/dsl/mlir_gen/dialect/symbol/get_dim.py`](../../expectation/dsl/mlir_gen/dialect/symbol/get_dim.py)
  - [`expectation/dsl/mlir_gen/dialect/symbol/get_stride.py`](../../expectation/dsl/mlir_gen/dialect/symbol/get_stride.py)
- 示例：

```python
def get_dim(value: "Tensor[f32, 4, 8]") -> int:
    return value.get_shape()[1]


def get_stride(value: "Tensor[f32, 4, 8]") -> int:
    return value.get_stride()[0]
```

- `BLOCKER`：`E2`
- `READY_IF`：`E2 CLOSE_IF=true`
- `DISPATCH_RULE`：`ONLY_IF READY_IF=true`
- 验收标准：
  - `test_parse_function_supports_memory_get_shape_index`
    - 输入：`return value.get_shape()[1]`
    - 预期输出：AST 解析成功；生成 `MemoryQuery` 对应 AST 节点而不是 `Unsupported expression`
  - `test_parse_function_supports_memory_get_stride_index`
    - 输入：`return value.get_stride()[0]`
    - 预期输出：AST 解析成功
  - `test_build_func_op_lowers_symbol_get_dim`
    - 输入：`build_func_op(get_dim_static, STATIC_MEMORY)` 与 `build_func_op(get_dim_dynamic, DYNAMIC_MEMORY)`
    - 预期输出：分别生成 `1` 个 `SymbolGetDimOp`；返回值类型分别为静态/动态 `symbol.int`
  - `test_build_func_op_lowers_symbol_get_stride`
    - 输入：`build_func_op(get_stride_static, STATIC_MEMORY)` 与 `build_func_op(get_stride_dynamic, DYNAMIC_MEMORY)`
    - 预期输出：分别生成 `1` 个 `SymbolGetStrideOp`；返回值类型分别为静态/动态 `symbol.int`
  - `test_build_func_op_rejects_non_memory_get_shape_or_stride`
    - 输入：`value: int` 上调用 `get_shape()` 或 `get_stride()`
    - 预期输出：抛 `AstVisitorError`
  - `test_build_func_op_rejects_invalid_axis_for_get_shape_or_stride`
    - 输入：负轴或越界轴
    - 预期输出：抛 `AstVisitorError`
- 验收命令：

```bash
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/get_dim.py
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/get_stride.py
PYTHONPATH=. pytest -q test/dsl/test_ast.py test/dsl/test_ast_visitor.py test/dsl/test_emit_mlir.py test/dsl/test_mlir_gen.py -k 'get_dim or get_stride or get_shape'
```

- `CLOSE_IF`：上述 3 条命令退出码全部为 `0`
- `FAIL_ROUTING`：若仍是 `Unsupported expression`，转回 `dsl/ast`；若 AST 已过但 lowering 失败，转回 `dsl/emit_mlir + dsl/mlir_gen`

### E4. `symbol compare family expectation` 闭环

- 目标文件：
  - [`expectation/dsl/mlir_gen/dialect/symbol/gt.py`](../../expectation/dsl/mlir_gen/dialect/symbol/gt.py)
  - [`expectation/dsl/mlir_gen/dialect/symbol/le.py`](../../expectation/dsl/mlir_gen/dialect/symbol/le.py)
  - [`expectation/dsl/mlir_gen/dialect/symbol/lt.py`](../../expectation/dsl/mlir_gen/dialect/symbol/lt.py)
  - [`expectation/dsl/mlir_gen/dialect/symbol/ne.py`](../../expectation/dsl/mlir_gen/dialect/symbol/ne.py)
- 目标：把 DSL 公开 symbol compare 契约从当前的 `eq/ge` 扩展为 expectation 需要的 `gt/le/lt/ne`，并保证 `[immutable-file]` 的 `ne.py` 保持只读。
- 建议修改范围：
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
- 不得修改：
  - [`expectation/dsl/mlir_gen/dialect/symbol/ne.py`](../../expectation/dsl/mlir_gen/dialect/symbol/ne.py)
  - 其他 4 个 expectation 文件默认也保持只读
- 示例：

```python
def gt_func(lhs: int, rhs: int) -> bool:
    return lhs > rhs


def ne_func(lhs: int, rhs: int) -> bool:
    return lhs != rhs
```

- `BLOCKER`：`E3`
- `READY_IF`：`E3 CLOSE_IF=true`
- `DISPATCH_RULE`：`ONLY_IF READY_IF=true`
- 验收标准：
  - `test_emit_mlir_lowers_symbol_gt`
    - 输入：`lhs > rhs`
    - 预期输出：生成 `1` 个 `SymbolGtOp`，结果类型为 `i1`
  - `test_emit_mlir_lowers_symbol_le`
    - 输入：`lhs <= rhs`
    - 预期输出：生成 `1` 个 `SymbolLeOp`，结果类型为 `i1`
  - `test_emit_mlir_lowers_symbol_lt`
    - 输入：`lhs < rhs`
    - 预期输出：生成 `1` 个 `SymbolLtOp`，结果类型为 `i1`
  - `test_emit_mlir_lowers_symbol_ne`
    - 输入：`lhs != rhs`
    - 预期输出：生成 `1` 个 `SymbolNeOp`，结果类型为 `i1`
  - `test_build_func_op_lowers_symbol_gt`
    - 输入：静态整数实参、符号整数实参各一组
    - 预期输出：`FuncOp` 中恰有 `1` 个 `SymbolGtOp` 与 `1` 个 `ReturnOp`
  - `test_build_func_op_lowers_symbol_le`
    - 输入：静态整数实参、符号整数实参各一组
    - 预期输出：`FuncOp` 中恰有 `1` 个 `SymbolLeOp` 与 `1` 个 `ReturnOp`
  - `test_build_func_op_lowers_symbol_lt`
    - 输入：静态整数实参、符号整数实参各一组
    - 预期输出：`FuncOp` 中恰有 `1` 个 `SymbolLtOp` 与 `1` 个 `ReturnOp`
  - `test_build_func_op_lowers_symbol_ne`
    - 输入：静态整数实参、符号整数实参各一组
    - 预期输出：`FuncOp` 中恰有 `1` 个 `SymbolNeOp` 与 `1` 个 `ReturnOp`
- 验收命令：

```bash
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/gt.py
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/le.py
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/lt.py
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/ne.py
PYTHONPATH=. pytest -q test/dsl/test_emit_mlir.py test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py -k 'symbol_gt or symbol_le or symbol_lt or symbol_ne'
```

- `CLOSE_IF`：上述 5 条命令退出码全部为 `0`
- `FAIL_ROUTING`：若仍报 `Unsupported symbol compare op`，转回 `spec/dsl/emit_mlir.md + dsl/emit_mlir/mlir_gen` 链路，不得关闭任务

### E5. `symbol.to_float expectation` 闭环

- 目标文件：[`expectation/dsl/mlir_gen/dialect/symbol/to_float.py`](../../expectation/dsl/mlir_gen/dialect/symbol/to_float.py)
- 目标：让 `-> float` 返回注解与 `float(symbol.int)` 都形成稳定 DSL 公开契约，并能 lowering 为 `symbol.to_float`。
- 建议修改范围：
  - [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
- 不得修改：
  - [`expectation/dsl/mlir_gen/dialect/symbol/to_float.py`](../../expectation/dsl/mlir_gen/dialect/symbol/to_float.py)
- 示例：

```python
def to_float_func(value: int) -> float:
    return float(value)
```

- `BLOCKER`：`E4`
- `READY_IF`：`E4 CLOSE_IF=true`
- `DISPATCH_RULE`：`ONLY_IF READY_IF=true`
- 验收标准：
  - `test_parse_function_supports_float_return_annotation`
    - 输入：`def to_float_func(value: int) -> float`
    - 预期输出：AST 解析成功，不再报 `Unsupported annotation`
  - `test_parse_function_supports_builtin_float_on_symbol_int`
    - 输入：`return float(value)`，`value` 为静态整数或 `SymbolDim`
    - 预期输出：AST 与 lowering 均成功
  - `test_build_func_op_lowers_symbol_to_float`
    - 输入：`build_func_op(to_float_func, VALUE)` 与 `build_func_op(to_float_func, SYMBOL_VALUE)`
    - 预期输出：函数体中恰有 `1` 个 `SymbolToFloatOp`；`ReturnOp.arguments[0].type == f32`
- 验收命令：

```bash
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/to_float.py
PYTHONPATH=. pytest -q test/dsl/test_ast.py test/dsl/test_ast_visitor.py test/dsl/test_emit_mlir.py test/dsl/test_mlir_gen.py -k 'to_float or float_return_annotation'
```

- `CLOSE_IF`：上述 2 条命令退出码全部为 `0`
- `FAIL_ROUTING`：若仍报 `Unsupported annotation`，转回 `dsl/ast`；若 AST 已过但 lowering 失败，转回 `dsl/emit_mlir + dsl/mlir_gen`

### E6. 全量 expectation 收口

- 目标：在不改 expectation 文件本体的前提下，完成当前 `85` 个 expectation 脚本的全量复跑，并更新状态台账。
- 建议修改范围：
  - [`agents/codex-multi-agents/agents/大闸蟹/expectation_status.md`](../../agents/codex-multi-agents/agents/大闸蟹/expectation_status.md)
- 不得修改：
  - 本轮已经通过的 expectation 文件本体
- `BLOCKER`：`E1`、`E2`、`E3`、`E4`、`E5`
- `READY_IF`：`E1/E2/E3/E4/E5 CLOSE_IF=true`
- `DISPATCH_RULE`：`ONLY_IF READY_IF=true`
- 验收标准：
  - expectation 批量命令
    - 输入：`expectation/` 下全部可执行脚本，排除 `expectation/utils/*` 与 `__pycache__`
    - 预期输出：总数 `85`，失败 `0`
  - `expectation_status.md`
    - 输入：本次全量执行结果
    - 预期输出：台账中的开始时间、结束时间、总数、通过数、失败数、失败摘要、文件表全部与本次执行一致
- 验收命令：

```bash
find expectation -type f ! -path "*/__pycache__/*" ! -path "expectation/utils/*" | sort | while IFS= read -r f; do PYTHONPATH=. python "$f"; done
```

- `CLOSE_IF`：
  - 上述命令退出码为 `0`
  - 台账更新为 `通过=85`、`失败=0`
- `FAIL_ROUTING`：若全量回归仍失败，按新增失败文件所在子域重新建 expectation 修复任务，不得直接关闭 `E6`

## 反思与最终选择

1. 为什么现在才补计划书：
   - 我之前只把拆分方案通过会话同步给了管理员，没有同步落成 `ARCHITECTURE/plan` 文档。这会导致“口头已达成、仓库里无计划书”的断层，后续接手人不容易快速判断当前约束与验收口径。
2. 为什么仍然保留 `E1~E6`：
   - `E3` 合并 `get_dim/get_stride`，是为了避免 AST/query 入口多人同时改同一组文件。
   - `E4` 合并 `gt/le/lt/ne`，是为了避免 compare 公开契约被拆成四份重复改同一组 spec/test。
   - 这一粒度与现有主仓失败根因最一致，也与管理员当前已接收的口头拆分保持一致。
3. 更细拆分是否可能：
   - 可以，但不是默认方案。
   - 若后续 `A2/P12` 全部结束，且管理员确认有独立 lane 可以承接 AST/query 双任务，则可把 `E3` 再细拆成“`get_dim`”和“`get_stride`”两个子任务；在那之前，不建议默认拆开。
4. 依赖句为什么采用 `BLOCKER / READY_IF / DISPATCH_RULE / CLOSE_IF / FAIL_ROUTING`：
   - 因为管理员不看代码，这套格式能直接决定“现在能不能发”“现在能不能关”“关不掉该退回哪里”，避免出现“建议优先”“大体通过”这类不可执行话术。
