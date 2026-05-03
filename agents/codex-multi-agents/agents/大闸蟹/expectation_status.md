# Expectation 状态台账

## 文件说明
- 功能说明：记录 `expectation/` 下可执行验收脚本的最近一次批量运行结果，作为后续质量巡检与差异跟踪的统一台账。
- 使用示例：查看最近结果可执行 `sed -n '1,120p' agents/codex-multi-agents/agents/大闸蟹/expectation_status.md`。
- 使用示例：更新台账时，从仓库根目录执行 `find expectation -type f ! -path "*/__pycache__/*" ! -path "expectation/utils/*" | sort | while IFS= read -r f; do PYTHONPATH=. python "$f"; done`，然后按本文件格式覆盖。
- spec：无单一 spec；本文件记录 [expectation](../../../../expectation) 下验收基线的运行状态。
- test：覆盖 `expectation/` 下所有可执行验收脚本，明确排除 `expectation/utils/*` 与 `__pycache__`。
- 功能实现：各 expectation 脚本自行定义验收行为，本文件只记录状态，不改变 expectation 契约。

## 本次批量执行
- 执行开始：2026-03-29 20:59:27 +0800
- 执行结束：2026-03-29 21:00:10 +0800
- 总数：85
- 通过：76
- 失败：9

## 失败模式摘要
- `dsl/mlir_gen/dialect/dma`：`2` 个失败。
- `dsl/mlir_gen/dialect/symbol`：`7` 个失败。

## dsl

| expectation 文件 | 状态 | 最近运行时间 | 备注 |
| --- | --- | --- | --- |
| [`expectation/dsl/emit_c/cpu/add.py`](../../../../expectation/dsl/emit_c/cpu/add.py) | PASS | 2026-03-29 20:59:27 +0800 | pass |
| [`expectation/dsl/for_loop.py`](../../../../expectation/dsl/for_loop.py) | PASS | 2026-03-29 20:59:27 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/arch/get_block_id`](../../../../expectation/dsl/mlir_gen/dialect/arch/get_block_id) | PASS | 2026-03-29 20:59:28 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/arch/get_block_num`](../../../../expectation/dsl/mlir_gen/dialect/arch/get_block_num) | PASS | 2026-03-29 20:59:28 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/arch/get_dynamic_memory.py`](../../../../expectation/dsl/mlir_gen/dialect/arch/get_dynamic_memory.py) | PASS | 2026-03-29 20:59:29 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/arch/get_subthread_id`](../../../../expectation/dsl/mlir_gen/dialect/arch/get_subthread_id) | PASS | 2026-03-29 20:59:29 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/arch/get_subthread_num`](../../../../expectation/dsl/mlir_gen/dialect/arch/get_subthread_num) | PASS | 2026-03-29 20:59:30 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/arch/get_thread_id`](../../../../expectation/dsl/mlir_gen/dialect/arch/get_thread_id) | PASS | 2026-03-29 20:59:30 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/arch/get_thread_num.py`](../../../../expectation/dsl/mlir_gen/dialect/arch/get_thread_num.py) | PASS | 2026-03-29 20:59:31 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py`](../../../../expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py) | PASS | 2026-03-29 20:59:31 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/dma/alloc`](../../../../expectation/dsl/mlir_gen/dialect/dma/alloc) | PASS | 2026-03-29 20:59:32 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/dma/cast`](../../../../expectation/dsl/mlir_gen/dialect/dma/cast) | PASS | 2026-03-29 20:59:32 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/dma/copy`](../../../../expectation/dsl/mlir_gen/dialect/dma/copy) | PASS | 2026-03-29 20:59:33 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/dma/deslice`](../../../../expectation/dsl/mlir_gen/dialect/dma/deslice) | PASS | 2026-03-29 20:59:33 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/dma/flatten`](../../../../expectation/dsl/mlir_gen/dialect/dma/flatten) | PASS | 2026-03-29 20:59:33 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/dma/free`](../../../../expectation/dsl/mlir_gen/dialect/dma/free) | FAIL | 2026-03-29 20:59:34 +0800 | AssertionError |
| [`expectation/dsl/mlir_gen/dialect/dma/load`](../../../../expectation/dsl/mlir_gen/dialect/dma/load) | PASS | 2026-03-29 20:59:34 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/dma/reshape`](../../../../expectation/dsl/mlir_gen/dialect/dma/reshape) | PASS | 2026-03-29 20:59:35 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/dma/slice`](../../../../expectation/dsl/mlir_gen/dialect/dma/slice) | PASS | 2026-03-29 20:59:35 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/dma/store`](../../../../expectation/dsl/mlir_gen/dialect/dma/store) | PASS | 2026-03-29 20:59:36 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/dma/view`](../../../../expectation/dsl/mlir_gen/dialect/dma/view) | FAIL | 2026-03-29 20:59:36 +0800 | AssertionError |
| [`expectation/dsl/mlir_gen/dialect/nn/add`](../../../../expectation/dsl/mlir_gen/dialect/nn/add) | PASS | 2026-03-29 20:59:37 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/nn/eq`](../../../../expectation/dsl/mlir_gen/dialect/nn/eq) | PASS | 2026-03-29 20:59:37 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/nn/ge`](../../../../expectation/dsl/mlir_gen/dialect/nn/ge) | PASS | 2026-03-29 20:59:38 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/nn/gt`](../../../../expectation/dsl/mlir_gen/dialect/nn/gt) | PASS | 2026-03-29 20:59:38 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/nn/le`](../../../../expectation/dsl/mlir_gen/dialect/nn/le) | PASS | 2026-03-29 20:59:39 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/nn/lt`](../../../../expectation/dsl/mlir_gen/dialect/nn/lt) | PASS | 2026-03-29 20:59:39 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/nn/mul`](../../../../expectation/dsl/mlir_gen/dialect/nn/mul) | PASS | 2026-03-29 20:59:40 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/nn/ne`](../../../../expectation/dsl/mlir_gen/dialect/nn/ne) | PASS | 2026-03-29 20:59:40 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/nn/sub`](../../../../expectation/dsl/mlir_gen/dialect/nn/sub) | PASS | 2026-03-29 20:59:40 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/nn/truediv`](../../../../expectation/dsl/mlir_gen/dialect/nn/truediv) | PASS | 2026-03-29 20:59:41 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/symbol/add`](../../../../expectation/dsl/mlir_gen/dialect/symbol/add) | PASS | 2026-03-29 20:59:41 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/symbol/eq`](../../../../expectation/dsl/mlir_gen/dialect/symbol/eq) | PASS | 2026-03-29 20:59:42 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/symbol/floordiv`](../../../../expectation/dsl/mlir_gen/dialect/symbol/floordiv) | PASS | 2026-03-29 20:59:42 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/symbol/for_loop.py`](../../../../expectation/dsl/mlir_gen/dialect/symbol/for_loop.py) | PASS | 2026-03-29 20:59:43 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/symbol/ge`](../../../../expectation/dsl/mlir_gen/dialect/symbol/ge) | PASS | 2026-03-29 20:59:43 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/symbol/get_dim.py`](../../../../expectation/dsl/mlir_gen/dialect/symbol/get_dim.py) | FAIL | 2026-03-29 20:59:44 +0800 | kernel_gen.dsl.ast_visitor.AstVisitorError: Unsupported expression |
| [`expectation/dsl/mlir_gen/dialect/symbol/get_stride.py`](../../../../expectation/dsl/mlir_gen/dialect/symbol/get_stride.py) | FAIL | 2026-03-29 20:59:44 +0800 | kernel_gen.dsl.ast_visitor.AstVisitorError: Unsupported expression |
| [`expectation/dsl/mlir_gen/dialect/symbol/gt.py`](../../../../expectation/dsl/mlir_gen/dialect/symbol/gt.py) | FAIL | 2026-03-29 20:59:45 +0800 | kernel_gen.dsl.ast_visitor.AstVisitorError: Unsupported symbol compare op |
| [`expectation/dsl/mlir_gen/dialect/symbol/le.py`](../../../../expectation/dsl/mlir_gen/dialect/symbol/le.py) | FAIL | 2026-03-29 20:59:46 +0800 | kernel_gen.dsl.ast_visitor.AstVisitorError: Unsupported symbol compare op |
| [`expectation/dsl/mlir_gen/dialect/symbol/lt.py`](../../../../expectation/dsl/mlir_gen/dialect/symbol/lt.py) | FAIL | 2026-03-29 20:59:46 +0800 | kernel_gen.dsl.ast_visitor.AstVisitorError: Unsupported symbol compare op |
| [`expectation/dsl/mlir_gen/dialect/symbol/mul`](../../../../expectation/dsl/mlir_gen/dialect/symbol/mul) | PASS | 2026-03-29 20:59:47 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/symbol/ne.py`](../../../../expectation/dsl/mlir_gen/dialect/symbol/ne.py) | FAIL | 2026-03-29 20:59:47 +0800 | kernel_gen.dsl.ast_visitor.AstVisitorError: Unsupported symbol compare op |
| [`expectation/dsl/mlir_gen/dialect/symbol/sub`](../../../../expectation/dsl/mlir_gen/dialect/symbol/sub) | PASS | 2026-03-29 20:59:50 +0800 | pass |
| [`expectation/dsl/mlir_gen/dialect/symbol/to_float.py`](../../../../expectation/dsl/mlir_gen/dialect/symbol/to_float.py) | FAIL | 2026-03-29 20:59:51 +0800 | kernel_gen.dsl.ast_visitor.AstVisitorError: Unsupported annotation |
| [`expectation/dsl/mlir_gen/dialect/symbol/truediv`](../../../../expectation/dsl/mlir_gen/dialect/symbol/truediv) | PASS | 2026-03-29 20:59:51 +0800 | pass |
| [`expectation/dsl/mlir_gen/use_global_value`](../../../../expectation/dsl/mlir_gen/use_global_value) | PASS | 2026-03-29 20:59:52 +0800 | pass |

## operation

| expectation 文件 | 状态 | 最近运行时间 | 备注 |
| --- | --- | --- | --- |
| [`expectation/operation/dma/alloc`](../../../../expectation/operation/dma/alloc) | PASS | 2026-03-29 20:59:52 +0800 | pass |
| [`expectation/operation/dma/cast`](../../../../expectation/operation/dma/cast) | PASS | 2026-03-29 20:59:53 +0800 | pass |
| [`expectation/operation/dma/copy`](../../../../expectation/operation/dma/copy) | PASS | 2026-03-29 20:59:53 +0800 | pass |
| [`expectation/operation/dma/deslice`](../../../../expectation/operation/dma/deslice) | PASS | 2026-03-29 20:59:54 +0800 | pass |
| [`expectation/operation/dma/flatten`](../../../../expectation/operation/dma/flatten) | PASS | 2026-03-29 20:59:55 +0800 | pass |
| [`expectation/operation/dma/free`](../../../../expectation/operation/dma/free) | PASS | 2026-03-29 20:59:55 +0800 | pass |
| [`expectation/operation/dma/load`](../../../../expectation/operation/dma/load) | PASS | 2026-03-29 20:59:55 +0800 | pass |
| [`expectation/operation/dma/reshape`](../../../../expectation/operation/dma/reshape) | PASS | 2026-03-29 20:59:56 +0800 | pass |
| [`expectation/operation/dma/slice`](../../../../expectation/operation/dma/slice) | PASS | 2026-03-29 20:59:56 +0800 | pass |
| [`expectation/operation/dma/store`](../../../../expectation/operation/dma/store) | PASS | 2026-03-29 20:59:57 +0800 | pass |
| [`expectation/operation/dma/view`](../../../../expectation/operation/dma/view) | PASS | 2026-03-29 20:59:57 +0800 | pass |
| [`expectation/operation/nn/add`](../../../../expectation/operation/nn/add) | PASS | 2026-03-29 20:59:58 +0800 | pass |
| [`expectation/operation/nn/broadcast`](../../../../expectation/operation/nn/broadcast) | PASS | 2026-03-29 20:59:58 +0800 | pass |
| [`expectation/operation/nn/broadcast_to`](../../../../expectation/operation/nn/broadcast_to) | PASS | 2026-03-29 20:59:59 +0800 | pass |
| [`expectation/operation/nn/eq`](../../../../expectation/operation/nn/eq) | PASS | 2026-03-29 20:59:59 +0800 | pass |
| [`expectation/operation/nn/floordiv`](../../../../expectation/operation/nn/floordiv) | PASS | 2026-03-29 21:00:00 +0800 | pass |
| [`expectation/operation/nn/ge`](../../../../expectation/operation/nn/ge) | PASS | 2026-03-29 21:00:00 +0800 | pass |
| [`expectation/operation/nn/gt`](../../../../expectation/operation/nn/gt) | PASS | 2026-03-29 21:00:00 +0800 | pass |
| [`expectation/operation/nn/le`](../../../../expectation/operation/nn/le) | PASS | 2026-03-29 21:00:01 +0800 | pass |
| [`expectation/operation/nn/lt`](../../../../expectation/operation/nn/lt) | PASS | 2026-03-29 21:00:01 +0800 | pass |
| [`expectation/operation/nn/matmul`](../../../../expectation/operation/nn/matmul) | PASS | 2026-03-29 21:00:02 +0800 | pass |
| [`expectation/operation/nn/mul`](../../../../expectation/operation/nn/mul) | PASS | 2026-03-29 21:00:02 +0800 | pass |
| [`expectation/operation/nn/ne`](../../../../expectation/operation/nn/ne) | PASS | 2026-03-29 21:00:03 +0800 | pass |
| [`expectation/operation/nn/sub`](../../../../expectation/operation/nn/sub) | PASS | 2026-03-29 21:00:03 +0800 | pass |
| [`expectation/operation/nn/truediv`](../../../../expectation/operation/nn/truediv) | PASS | 2026-03-29 21:00:04 +0800 | pass |
| [`expectation/operation/scf/loop`](../../../../expectation/operation/scf/loop) | PASS | 2026-03-29 21:00:04 +0800 | pass |

## pass

| expectation 文件 | 状态 | 最近运行时间 | 备注 |
| --- | --- | --- | --- |
| [`expectation/pass/lowing/nn_to_kernel/add.py`](../../../../expectation/pass/lowing/nn_to_kernel/add.py) | PASS | 2026-03-29 21:00:04 +0800 | pass |
| [`expectation/pass/lowing/nn_to_kernel/eq.py`](../../../../expectation/pass/lowing/nn_to_kernel/eq.py) | PASS | 2026-03-29 21:00:05 +0800 | pass |
| [`expectation/pass/lowing/nn_to_kernel/ge.py`](../../../../expectation/pass/lowing/nn_to_kernel/ge.py) | PASS | 2026-03-29 21:00:05 +0800 | pass |
| [`expectation/pass/lowing/nn_to_kernel/gt.py`](../../../../expectation/pass/lowing/nn_to_kernel/gt.py) | PASS | 2026-03-29 21:00:06 +0800 | pass |
| [`expectation/pass/lowing/nn_to_kernel/le.py`](../../../../expectation/pass/lowing/nn_to_kernel/le.py) | PASS | 2026-03-29 21:00:06 +0800 | pass |
| [`expectation/pass/lowing/nn_to_kernel/lt.py`](../../../../expectation/pass/lowing/nn_to_kernel/lt.py) | PASS | 2026-03-29 21:00:07 +0800 | pass |
| [`expectation/pass/lowing/nn_to_kernel/mul.py`](../../../../expectation/pass/lowing/nn_to_kernel/mul.py) | PASS | 2026-03-29 21:00:07 +0800 | pass |
| [`expectation/pass/lowing/nn_to_kernel/ne.py`](../../../../expectation/pass/lowing/nn_to_kernel/ne.py) | PASS | 2026-03-29 21:00:08 +0800 | pass |
| [`expectation/pass/lowing/nn_to_kernel/sub.py`](../../../../expectation/pass/lowing/nn_to_kernel/sub.py) | PASS | 2026-03-29 21:00:08 +0800 | pass |
| [`expectation/pass/lowing/nn_to_kernel/truediv.py`](../../../../expectation/pass/lowing/nn_to_kernel/truediv.py) | PASS | 2026-03-29 21:00:08 +0800 | pass |

## symbol_variable

| expectation 文件 | 状态 | 最近运行时间 | 备注 |
| --- | --- | --- | --- |
| [`expectation/symbol_variable/memory`](../../../../expectation/symbol_variable/memory) | PASS | 2026-03-29 21:00:09 +0800 | pass |
| [`expectation/symbol_variable/symbol_dim`](../../../../expectation/symbol_variable/symbol_dim) | PASS | 2026-03-29 21:00:09 +0800 | pass |
