# memory_pool.md

## 功能简介

- `MemoryPoolPass` 提供 `dma.alloc/dma.free` 生命周期摘要分析，并在显式 `rewrite=True` 时把片上 `dma.alloc` 改写为 `arch.get_dynamic_memory + dma.view + dma.reshape`。
- 默认 `MemoryPoolPass()` 是 analysis-only，不修改 IR；rewrite 只能通过公开构造参数或 registry/ircheck option 显式启用。
- 本 pass 不做内存复用；同一 `func + memory space` 内的 alloc 按词法出现顺序线性切分 backing memory。

## API 列表

- `class MemoryPoolPass(rewrite: bool = False, fold: bool = True, alignment: int = 1024)`
- `MemoryPoolPass.from_options(options: dict[str, str]) -> MemoryPoolPass`
- `MemoryPoolPass.apply(ctx: Context, module: ModuleOp) -> None`
- `MemoryPoolPass.get_summary(func_name: str) -> MemoryPoolSummary`
- `MemoryPoolPass.all_summaries() -> dict[str, MemoryPoolSummary]`
- `class MemoryPoolSummary(func_name: str, intervals: tuple[MemoryPoolInterval, ...], peak_bytes_by_bucket: dict[tuple[str], sympy.Basic], pool_count: int)`
- `MemoryPoolSummary.to_text() -> str`
- `class MemoryPoolInterval(name: str, bucket_key: tuple[str], size_bytes_expr: sympy.Basic, begin_index: int, end_index: int, offset_bytes_expr: sympy.Basic)`

## 文档信息

- `spec`：`spec/pass/lowering/memory_pool.md`
- `功能实现`：`kernel_gen/passes/memory_pool.py`
- `test`：`test/passes/test_memory_pool.py`、`test/passes/test_registry.py`、`test/passes/test_pass_manager.py`
- `合同验收资产`：`expectation/pass/memory_pool`

## 依赖

- `kernel_gen/dialect/arch.py`：提供公开 `ArchGetDynamicMemoryOp`。
- `kernel_gen/dialect/dma.py`：提供公开 `DmaAllocOp`、`DmaFreeOp`、`DmaViewOp`、`DmaReshapeOp`。
- `kernel_gen/dialect/nn.py`：提供 `NnMemoryType` 与 `NnMemorySpaceAttr`。
- `kernel_gen/dialect/symbol.py`：提供 `!symbol.int<"expr">` 物化 op 与类型。
- `kernel_gen/passes/registry.py`：通过 `memory-pool={rewrite=...,fold=...,alignment=...}` 公开 option 构造本 pass。

## 术语

- `interval`：单个 `dma.alloc` 的生命周期摘要，包含 byte size、词法起止索引和线性 byte offset。
- `bucket`：按 memory space 聚合的分桶键；rewrite 时每个 bucket 对应一份 `arch.get_dynamic_memory`。
- `alignment`：byte 对齐值；默认 `1024`，`0` 表示关闭对齐。

## 目标

- summary 路径必须覆盖静态 shape、具名动态 shape、`symbol.for` / `scf.for` 中的 loop-invariant alloc，以及缺少 `dma.free` 的 alloc。
- rewrite 路径只改写 `shared/local/tsm/tlm1/tlm2/tlm3` 片上 memory space；`global` 不属于 `arch.get_dynamic_memory` 支持范围，因此只进入 summary，不生成 dynamic backing rewrite。
- rewrite 结果必须使用 `arch.get_dynamic_memory + dma.view + dma.reshape`，不得生成 byte-pool `dma.alloc/dma.free` 作为本 pass 的 rewrite 结果。
- `offset` 按目标 dtype 的元素单位表达；若 `aligned_offset_bytes / sizeof(target_dtype)` 不能证明整除，必须以 `KernelCodeError(ErrorKind.UNIMPLEMENTED, ErrorModule.PASS, ...)` 失败。

## API详细说明

### `class MemoryPoolPass(rewrite: bool = False, fold: bool = True, alignment: int = 1024)`

- api：`class MemoryPoolPass(rewrite: bool = False, fold: bool = True, alignment: int = 1024)`
- 参数：
  - `rewrite`：是否执行 IR rewrite；类型 `bool`；默认 `False`；非法类型报 `MemoryPoolOptionError: rewrite must be bool`。
  - `fold`：是否启用 pass manager 通用 fold；类型 `bool`；默认 `True`；非法类型报 `MemoryPoolOptionError: fold must be bool`。
  - `alignment`：byte 对齐值；类型 `int`；默认 `1024`；`0` 关闭对齐；负数、`bool` 或非整数报 `MemoryPoolOptionError: alignment must be non-negative integer`。
- 返回值：`MemoryPoolPass` 实例。
- 使用示例：

  ```python
  from kernel_gen.passes.memory_pool import MemoryPoolPass

  pass_obj = MemoryPoolPass(rewrite=True, fold=False, alignment=0)
  ```
- 功能说明：创建 memory-pool pass，并配置是否 rewrite、是否 fold 和 byte 对齐策略。
- 注意事项：构造器只公开 `rewrite/fold/alignment` 三个参数；本文件内 helper 不是公开 API，外部实现和测试不得跨文件调用。

### `MemoryPoolPass.from_options(options: dict[str, str]) -> MemoryPoolPass`

- api：`MemoryPoolPass.from_options(options: dict[str, str]) -> MemoryPoolPass`
- 参数：
  - `options`：registry/ircheck 传入的字符串键值；类型 `dict[str, str]`；允许键仅为 `rewrite`、`fold`、`alignment`；未知键报 `MemoryPoolOptionError: unknown option: <name>`。
- 返回值：`MemoryPoolPass` 实例。
- 使用示例：

  ```python
  pass_obj = MemoryPoolPass.from_options({"rewrite": "true", "alignment": "0"})
  ```
- 功能说明：把公开 CLI/registry option 转为 `MemoryPoolPass` 构造参数。
- 注意事项：`rewrite/fold` 接受 `true/false/1/0/yes/no/on/off`；`alignment` 必须是非负整数字符串；registry 可先处理通用 `fold` option 后再透传剩余 option。

### `MemoryPoolPass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`MemoryPoolPass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：xdsl `Context`；本 pass 不从 `ctx` 探测运行期能力。
  - `module`：待处理 `builtin.module`；类型 `ModuleOp`；非 module 报 `MemoryPoolInvalidModule: module must be builtin.module`。
- 返回值：`None`；原地更新 summary，并在 `rewrite=True` 时原地改写 IR。
- 使用示例：

  ```python
  pass_obj = MemoryPoolPass(rewrite=False)
  pass_obj.apply(ctx, module)
  summary = pass_obj.get_summary("main")
  ```
- 功能说明：遍历 module 内 `func.func`，生成 `MemoryPoolSummary`；显式 rewrite 时重写符合输入域的 `dma.alloc/dma.free`。
- 注意事项：
  - analysis-only 路径不修改 IR。
  - analysis-only 路径在 `alignment>0` 且当前 offset 为动态表达式时，summary 保留未对齐的符号 offset，不因无法物化 aligned offset 阻断；该放宽不适用于 `rewrite=True`。
  - analysis-only 路径允许 `dma.alloc` 结果被 `return` 或所在 loop 外部使用，并继续生成摘要；`rewrite=True` 必须拒绝该场景并报 `MemoryPoolEscapingAlloc: alloc escapes current region`，避免生成不可支配的 replacement。
  - `rewrite=True` 允许外层 loop 内的 alloc 被其内层 loop 使用；该用法仍在 alloc 所在 loop 的词法范围内，不属于 escaping use。
  - 缺少 `dma.free` 的 alloc 生命周期按所在 block/region 结束记录。
  - `rewrite=True` 时每个 `func + 可改写片上 memory space` 在函数入口生成一份 `arch.get_dynamic_memory`；`global` alloc 保留为 summary-only，不走 dynamic backing。
  - 多 alloc 线性切分，不因生命周期不重叠而复用 offset。
  - `symbol.for` 内 alloc 的 `dma.view + dma.reshape` 留在 loop body；`scf.for` 内 loop-invariant alloc 的 backing memory 仍在函数入口。
  - `dma.alloc` result `nn.memory` 的 shape/stride 条目只接受已通过 `nn.memory` verifier 的 `SymbolExprAttr`；旧 bare `IntAttr` / `StringAttr` 维度不属于本 pass 输入合同，由 `nn.memory` verifier 在进入 pass 前拒绝。
  - full-rank `dma.alloc.dynamic_shape` operand 可携带 `!symbol.int<"?">` 类型；rewrite 必须在 `dma.view + dma.reshape` metadata 中继续保留 `?`，不得把 `?` 反推为局部变量名或后续 reshape 的公开名字。
  - `SymbolExprAttr` 维度可包含 `iter<start,end,step>` atom；memory-pool 在内部 size/offset 计算中把这类表达作为不透明动态符号处理，rewrite 仍通过公开 `!symbol.int<"...">` operand 保留原 shape 文本，不把 iter token 退化为 `?`。
  - 若 `dma.alloc` result shape 合法保留匿名 `?`，且该 alloc 结果随后通过 `dma.reshape` 细化为同 dtype/space/rank 的公开 shape，memory-pool 只能替换 alloc source，不得用后续 reshape result type 回写或推导 alloc/view/内部 rewrite reshape 的 shape 名称。
  - 非 contiguous/custom stride 报 `MemoryPoolUnsupportedLayout: non-contiguous/custom stride is not supported`，错误类型为 `UNIMPLEMENTED`。
  - 多 block 或无法归属的 control-flow 报 `MemoryPoolUnsupportedControlFlow` 或 `MemoryPoolUnsupportedRegionEscape`，不得静默跳过非法 alloc。

### `MemoryPoolPass.get_summary(func_name: str) -> MemoryPoolSummary`

- api：`MemoryPoolPass.get_summary(func_name: str) -> MemoryPoolSummary`
- 参数：
  - `func_name`：函数名；类型 `str`；必须对应最近一次 `apply(...)` 已分析的 `func.func`。
- 返回值：`MemoryPoolSummary`。
- 使用示例：

  ```python
  summary = pass_obj.get_summary("main")
  ```
- 功能说明：返回指定函数的 summary。
- 注意事项：函数名不存在时报 `MemoryPoolSummaryNotFound: <func_name>`。

### `MemoryPoolPass.all_summaries() -> dict[str, MemoryPoolSummary]`

- api：`MemoryPoolPass.all_summaries() -> dict[str, MemoryPoolSummary]`
- 参数：无。
- 返回值：`dict[str, MemoryPoolSummary]`；返回浅拷贝。
- 使用示例：

  ```python
  summaries = pass_obj.all_summaries()
  ```
- 功能说明：返回最近一次 `apply(...)` 产生的全部函数摘要。
- 注意事项：调用方修改返回字典不得影响 pass 内部缓存。

### `class MemoryPoolSummary(func_name: str, intervals: tuple[MemoryPoolInterval, ...], peak_bytes_by_bucket: dict[tuple[str], sympy.Basic], pool_count: int)`

- api：`class MemoryPoolSummary(func_name: str, intervals: tuple[MemoryPoolInterval, ...], peak_bytes_by_bucket: dict[tuple[str], sympy.Basic], pool_count: int)`
- 参数：
  - `func_name`：summary 对应函数名。
  - `intervals`：按分析顺序排列的 allocation 生命周期。
  - `peak_bytes_by_bucket`：每个 bucket 的 peak byte 表达式。
  - `pool_count`：bucket 数量。
- 返回值：`MemoryPoolSummary` 实例。
- 使用示例：

  ```python
  summary = MemoryPoolSummary("main", intervals, peak_bytes_by_bucket, pool_count=1)
  ```
- 功能说明：表示单个函数的 memory-pool 摘要。
- 注意事项：summary 是只读数据结构；rewrite 是否启用不改变 `MemoryPoolSummary` 的字段含义。

### `MemoryPoolSummary.to_text() -> str`

- api：`MemoryPoolSummary.to_text() -> str`
- 参数：无。
- 返回值：稳定文本摘要。
- 使用示例：

  ```python
  text = summary.to_text()
  ```
- 功能说明：输出可供 pytest 和调试比对的 summary 文本。
- 注意事项：文本必须包含 `func_name`、`intervals`、`peak_bytes_by_bucket` 和 `pool_count`。

### `class MemoryPoolInterval(name: str, bucket_key: tuple[str], size_bytes_expr: sympy.Basic, begin_index: int, end_index: int, offset_bytes_expr: sympy.Basic)`

- api：`class MemoryPoolInterval(name: str, bucket_key: tuple[str], size_bytes_expr: sympy.Basic, begin_index: int, end_index: int, offset_bytes_expr: sympy.Basic)`
- 参数：
  - `name`：allocation 名称；无显式 name hint 时使用稳定 `alloc<n>`。
  - `bucket_key`：memory bucket；当前至少包含 memory space 文本。
  - `size_bytes_expr`：allocation byte size 的 `sympy.Basic` 表达式。
  - `begin_index`：词法生命周期起点。
  - `end_index`：词法生命周期终点；缺 free 时为所在 block/region 结束。
  - `offset_bytes_expr`：summary 中按线性切分得到的 byte offset 表达式。
- 返回值：`MemoryPoolInterval` 实例。
- 使用示例：

  ```python
  interval = MemoryPoolInterval("alloc1", ("#SM",), sympy.Integer(32), 0, 1, sympy.Integer(0))
  ```
- 功能说明：记录单个 allocation 的 summary 区间。
- 注意事项：`offset_bytes_expr` 是 byte 单位；rewrite 中的 `dma.view.offsets[0]` 会再转换为目标 dtype 的元素单位。

## 测试

- 测试文件：`test/passes/test_memory_pool.py`、`test/passes/test_registry.py`、`test/passes/test_pass_manager.py`
- 执行命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_pool.py test/passes/test_registry.py test/passes/test_pass_manager.py`
- 合同验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.memory_pool`

### 测试目标

- 验证 summary API、文本输出、缺 free 生命周期、dtype/shape/stride 错误、loop 生命周期错误。
- 验证 `rewrite=True` 生成 `arch.get_dynamic_memory + dma.view + dma.reshape`，且不残留可改写的 `dma.alloc`。
- 验证 `alignment=0`、默认 alignment、正 alignment、非法 alignment 和 registry/ircheck option 路径。
- 验证测试只通过公开 `MemoryPoolPass`、registry、PassManager 与公开 dialect op 入口运行，不调用 `memory_pool.py` 内部 helper。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-MP-001 | summary | 单 alloc/free | 构造 `dma.alloc + dma.free` | 运行 `MemoryPoolPass(rewrite=False).apply(...)` | 生成一个 interval 与 bucket peak | `test_memory_pool_summary_basic` |
| TC-MP-002 | summary API | 空函数、缺失查询、拷贝语义 | 构造空函数 module | 查询 `get_summary/all_summaries` | 空 summary 稳定，缺失函数报 `MemoryPoolSummaryNotFound` | `test_memory_pool_public_summary_access_edges` |
| TC-MP-003 | rewrite | 单 space 多 alloc | `shared` alloc/free，`alignment=0` | 运行 `MemoryPoolPass(rewrite=True, alignment=0)` | 一个 dynamic memory、多个 view/reshape、无 alloc/free 残留 | `test_memory_pool_rewrite_straight_line_pool_reuse` |
| TC-MP-004 | rewrite | 多 memory space | `shared` 与 `tlm1` alloc | 运行 rewrite | 每个 space 一份 dynamic memory | `test_memory_pool_rewrite_multiple_buckets` |
| TC-MP-005 | rewrite | 不同 size 线性切分 | 同 space 不同 shape | 运行 rewrite | view offset/shape 按出现顺序相邻 | `test_memory_pool_rewrite_size_mismatch` |
| TC-MP-006 | rewrite | 生命周期重叠 | 同 space alloc 重叠 | 运行 rewrite | 不复用 offset，线性切分 | `test_memory_pool_rewrite_overlap` |
| TC-MP-007 | dtype/shape | dtype 矩阵与符号 shape | 内置 dtype、非法 dtype、动态 shape | 运行 summary/rewrite | byte size 与符号表达稳定，非法 dtype 失败；动态 shape rewrite 保持结构化 `SymbolExprAttr` layout | `test_memory_pool_dtype_and_symbolic_shape_matrix` |
| TC-MP-007A | dtype/shape | full-rank unknown dynamic_shape | alloc result shape 为 `[?, ?]`，dynamic_shape operand 为 `!symbol.int<"?">` | 运行 `MemoryPoolPass(rewrite=True, alignment=0)` | rewrite 生成 `dma.view + dma.reshape`，shape metadata 继续保留匿名 `?` | `test_memory_pool_rewrite_preserves_unknown_full_rank_dynamic_shape` |
| TC-MP-007C | dtype/shape | anonymous alloc with public reshape layout | alloc result shape 为 `[?, ?]`，后续 reshape result shape 为 `[M, N]` | 运行 `MemoryPoolPass(rewrite=True, alignment=0)` | rewrite 不从后续 reshape 反推 alloc/view shape 名称；用户 reshape 保持自己的公开 shape | `test_memory_pool_rewrite_does_not_infer_following_reshape_layout` |
| TC-MP-008 | 边界 | 非 contiguous/custom stride | 非连续 stride memory | 运行 `apply(...)` | `UNIMPLEMENTED` + `MemoryPoolUnsupportedLayout` | `test_memory_pool_public_invalid_shape_stride_and_free_edges` |
| TC-MP-009 | 边界 | 缺 free | 单 alloc 无 free | 运行 analysis-only | interval end 为 block/region 结束 | `test_memory_pool_unpaired_alloc` |
| TC-MP-010 | loop | `symbol.for` alloc | loop 内 alloc/free | 运行 rewrite | backing 在函数入口，view/reshape 留在 loop body | `test_memory_pool_symbol_for_reuse` |
| TC-MP-010D | loop/dynamic shape | `iter<...>` shape atom | alloc shape 为 `min(4, 6 - iter<0,6,4>)` 且 dynamic_shape 传入同语义 `!symbol.int` | 运行 `MemoryPoolPass(rewrite=True, alignment=0)` | rewrite 通过，移除原 alloc，并保留原 dynamic shape operand 供 reshape 使用 | `test_memory_pool_rewrite_accepts_iter_token_shape_expression` |
| TC-MP-011 | registry | memory-pool options | `rewrite/fold/alignment` option | 运行 `build_registered_pass(...)` | 构造 `MemoryPoolPass`，非法 option 稳定失败 | `test_build_registered_memory_pool_alignment_options` |
| TC-MP-012 | 合同验收 | expectation memory_pool | 只读 `expectation/pass/memory_pool` | 运行 `python3 -m expectation.pass.memory_pool` | 全部合同通过且不修改 expectation | `expectation.pass.memory_pool` |
