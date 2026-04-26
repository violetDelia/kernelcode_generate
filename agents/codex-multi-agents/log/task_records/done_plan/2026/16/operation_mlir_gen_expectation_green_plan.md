# operation_mlir_gen_expectation_green_plan.md

## 文档信息

- 创建者：`守护最好的爱莉希雅`
- 最后一次更改：`睡觉小分队`
- 目标 `spec`：
  [`spec/dialect/kernel.md`](../../spec/dialect/kernel.md)、
  [`spec/dialect/dma.md`](../../spec/dialect/dma.md)、
  [`spec/pass/lowering/nn_lowering/spec.md`](../../spec/pass/lowering/nn_lowering/spec.md)、
  [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)、
  [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)、
  [`spec/operation/dma.md`](../../spec/operation/dma.md)、
  [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- 目标 `API`：
  `kernel` 写入类 `out-first`、
  `dma` 写入类 `target-first`、
  `dma.load / dma.cast` 为 side-effect op、
  `softmax(value)` 默认 `axis=-1` 先在 helper 层归一化
- 目标 `test`：
  [`test/dialect/test_kernel_dialect.py`](../../test/dialect/test_kernel_dialect.py)、
  [`test/dialect/test_dma_dialect.py`](../../test/dialect/test_dma_dialect.py)、
  [`test/pass/nn_lowering/test_expectation_img2col.py`](../../test/pass/nn_lowering/test_expectation_img2col.py)、
  [`test/pass/nn_lowering/test_expectation_broadcast_new_symbol_dim.py`](../../test/pass/nn_lowering/test_expectation_broadcast_new_symbol_dim.py)、
  [`test/dsl/test_expectation_softmax_negative_axis_normalize.py`](../../test/dsl/test_expectation_softmax_negative_axis_normalize.py)、
  [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
- 目标 `验收资产`：
  [`expectation/pass/lowing/nn_lowering/select.py`](../../expectation/pass/lowing/nn_lowering/select.py)、
  [`expectation/pass/lowing/nn_lowering/softmax.py`](../../expectation/pass/lowing/nn_lowering/softmax.py)、
  [`expectation/pass/lowing/nn_lowering/matmul.py`](../../expectation/pass/lowing/nn_lowering/matmul.py)、
  [`expectation/pass/lowing/nn_lowering/reduce/reduce_sum.py`](../../expectation/pass/lowing/nn_lowering/reduce/reduce_sum.py)、
  [`expectation/pass/lowing/nn_lowering/img2col/img2col1d.py`](../../expectation/pass/lowing/nn_lowering/img2col/img2col1d.py)、
  [`expectation/pass/lowing/nn_lowering/img2col/img2col2d.py`](../../expectation/pass/lowing/nn_lowering/img2col/img2col2d.py)、
  [`expectation/pass/lowing/nn_lowering/broadcast_new_symbol_dim.py`](../../expectation/pass/lowing/nn_lowering/broadcast_new_symbol_dim.py)、
  [`expectation/dsl/mlir_gen/dialect/nn/softmax.py`](../../expectation/dsl/mlir_gen/dialect/nn/softmax.py)、
  [`expectation/dsl/gen_kernel/npu_demo_add_barrier`](../../expectation/dsl/gen_kernel/npu_demo_add_barrier)
- 目标 `功能实现`：
  [`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py)、
  [`kernel_gen/dialect/kernel.py`](../../kernel_gen/dialect/kernel.py)、
  [`kernel_gen/dialect/dma.py`](../../kernel_gen/dialect/dma.py)、
  [`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py)、
  [`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)、
  [`kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)、
  [`kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py)、
  [`kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py)、
  [`kernel_gen/dsl/ast/nodes.py`](../../kernel_gen/dsl/ast/nodes.py)、
  [`kernel_gen/dsl/ast/parser.py`](../../kernel_gen/dsl/ast/parser.py)、
  [`kernel_gen/dsl/mlir_gen/emit/core.py`](../../kernel_gen/dsl/mlir_gen/emit/core.py)、
  [`kernel_gen/dsl/mlir_gen/emit/call_dma.py`](../../kernel_gen/dsl/mlir_gen/emit/call_dma.py)、
  [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)、
  [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| S1 | 无 | `wt-20260418-op-mlir-plan-s1` | `agents/codex-multi-agents/log/task_records/2026/16/20260418-op-mlir-plan.md` |
| S2 | S1 | `wt-20260418-op-mlir-dialect-s2` | `agents/codex-multi-agents/log/task_records/2026/16/20260418-op-mlir-plan.md` |
| S3 | S2 | `wt-20260418-op-mlir-lowering-s3` | `agents/codex-multi-agents/log/task_records/2026/16/20260418-op-mlir-plan.md` |
| S4 | S2 | `wt-20260418-op-mlir-codegen-s4` | `agents/codex-multi-agents/log/task_records/2026/16/20260418-op-mlir-plan.md` |
| S5 | S3、S4 | `wt-20260418-op-mlir-verify-s5` | `agents/codex-multi-agents/log/task_records/2026/16/20260418-op-mlir-plan.md` |

## 执行边界

- 执行人不得修改任何 `expectation` 文件；本计划中的 `expectation` 只作为合同真源和验收资产。
- 本计划不再为执行阶段提供“可改文件”白名单；执行人只允许修改与当前任务目标直接相关的实现、测试与必要辅助文件，但禁止修改：
  - [`expectation/pass/lowing`](../../expectation/pass/lowing)
  - [`expectation/dsl/gen_kernel`](../../expectation/dsl/gen_kernel)
  - [`expectation/dsl/mlir_gen`](../../expectation/dsl/mlir_gen)
  - `spec / 计划书 / agents 标准文档 / immutable 内容`
- 若执行阶段发现 expectation 需要改动，必须中止实现任务并回到架构侧重新确认合同，不允许执行人自行回退 expectation。

## 评审摘要

- 评审结论：`通过`
- 评审人：`守护最好的爱莉希雅`、`大闸蟹`
- 结论摘要：`模板阻断项已补齐，普通 operand 重排与 dma.load/dma.cast 建模重构边界清楚，范围已覆盖 dialect / lowering / mlir_gen / gen_kernel，可按当前正文推进。`

## 最终验收结论（2026-04-19 23:59 +0800）

- 验收人：`大闸蟹`
- 验收结论：`不通过`
- 验证基线：
  - 当前主仓执行目录：`/home/lfr/kernelcode_generate`
  - 本轮直接按计划书当前 `S5` 小节列出的脚本 / pytest / 检索入口复跑，不切换旧 worktree。
- 实际复跑结果：
  - `bash script/run-op-mlir-s3-expectation.sh` -> `exit 0`
  - `bash script/run-op-mlir-s4-gen-kernel-expectation.sh` -> `exit 2`
  - `python3 -m pytest -q test/pass/nn_lowering/img2col1d.py test/pass/nn_lowering/img2col2d.py test/pass/nn_lowering/softmax.py test/pass/nn_lowering/reduce_sum.py` -> `exit 4`
  - `python3 -m pytest -q test/dsl/test_expectation_softmax_negative_axis_normalize.py test/dsl/test_gen_kernel.py` -> `1 failed, 58 passed`
  - `python3 -m pytest -q test/script/test_run_op_mlir_s3_expectation.py test/script/test_run_op_mlir_s4_gen_kernel_expectation.py` -> `2 failed, 4 passed`
  - `rg -n '%[^ ]+ = "dma\\.(load|cast)"|DmaCastOp\\([^\\n]*result_type|DmaLoadOp\\([^\\n]*result_type|dma\\.(load|cast)\\([^)]*\\)\\s*->' kernel_gen/dialect/dma.py kernel_gen/dsl/ast kernel_gen/dsl/mlir_gen kernel_gen/dsl/gen_kernel.py kernel_gen/passes/lowering test/dsl test/pass -g '!*.md'` -> `exit 1`
- 最小阻断项：
  - [`script/run-op-mlir-s4-gen-kernel-expectation.sh`](../../script/run-op-mlir-s4-gen-kernel-expectation.sh) 当前把 `MAIN_REPO_ROOT` 算成了 `/home/lfr`，导致 expectation 入口被错误拼成 `/home/lfr/expectation/dsl/gen_kernel/npu_demo_add_barrier`，脚本本身即不可执行。
  - `S5` 验收命令仍点名不存在的 [`test/pass/nn_lowering/softmax.py`](../../test/pass/nn_lowering)；按计划书原文复跑时直接 `file or directory not found`，说明正文验收入口仍未与当前仓库测试布局完全对齐。
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py) 当前仍有 `test_gen_kernel_compiles_npu_demo_tiled_matmul_source` 失败；`g++` 编译生成源码时报 `S_INT` 未声明，说明 `gen_kernel` 产物尚未满足计划完成态。
  - [`test/script/test_run_op_mlir_s3_expectation.py`](../../test/script/test_run_op_mlir_s3_expectation.py) 仍锁定旧 stdout 片段 `[CASE-softmax-static]`，与当前 `script/run-op-mlir-s3-expectation.sh` 实际输出不一致；[`test/script/test_run_op_mlir_s4_gen_kernel_expectation.py`](../../test/script/test_run_op_mlir_s4_gen_kernel_expectation.py) 则被同一 S4 脚本路径错误直接带失败。
- 结论说明：
  - 本计划书在本轮检查前缺少“最终验收结论 / 验证基线”正文回写；本段已按当前主仓现场补回。
  - 当前功能现场与脚本/测试入口仍未全部通过，因此不满足归档前置条件。

## 复核结论（2026-04-20 00:02 +0800）

- 复核人：`大闸蟹`
- 复核结论：`不通过`
- 复核基线：
  - 当前主仓执行目录：`/home/lfr/kernelcode_generate`
  - 复核沿用计划书当前 `S5` 小节入口与现有终验基线，不切换历史 worktree。
- 复核摘要：
  - `bash script/run-op-mlir-s3-expectation.sh` 仍为 `exit 0`。
  - `bash script/run-op-mlir-s4-gen-kernel-expectation.sh` 仍因 expectation 入口路径错误而失败。
  - `test/dsl/test_gen_kernel.py` 仍存在 `g++` compile 失败，`test/script/test_run_op_mlir_s3_expectation.py` 与 `test/script/test_run_op_mlir_s4_gen_kernel_expectation.py` 仍未全绿。
  - 因此当前最小阻断项未消除，本计划仍不满足归档前置条件。

## 复核结论（2026-04-20 00:34:30 +0800）

- 复核人：`守护最好的爱莉希雅`
- 复核结论：`不通过`
- 复核基线：
  - 当前主仓执行目录：`/home/lfr/kernelcode_generate`
  - 当前 `HEAD`：`c44ef67b55cd5675c595094a0ffa6dc4e03bafce`
- 本轮复跑结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. bash script/run-op-mlir-s3-expectation.sh` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. bash script/run-op-mlir-s4-gen-kernel-expectation.sh` -> `exit 2`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_expectation_softmax_negative_axis_normalize.py test/dsl/test_gen_kernel.py` -> `1 failed, 58 passed`
- 最小阻断项：
  - [`script/run-op-mlir-s4-gen-kernel-expectation.sh`](../../script/run-op-mlir-s4-gen-kernel-expectation.sh) 当前仍把 expectation 入口错误拼到 `/home/lfr/expectation/dsl/gen_kernel/npu_demo_add_barrier`，脚本本身仍不可执行。
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py) 的 `test_gen_kernel_compiles_npu_demo_tiled_matmul_source` 仍失败；`g++` 编译生成源码时报 `S_INT` 未声明，说明 `gen_kernel` 产物尚未满足计划完成态。
- 结论说明：
  - 虽然 `TODO.md` 中该计划已回到 `完成待检查`，但当前主仓复核仍未消除最小阻断项，因此本计划当前仍不满足归档前置条件。

## 复核结论（2026-04-20 00:34:34 +0800）

- 复核人：`大闸蟹`
- 复核结论：`不通过`
- 复核基线：
  - 当前主仓执行目录：`/home/lfr/kernelcode_generate`
  - 当前 `HEAD`：`c44ef67b55cd5675c595094a0ffa6dc4e03bafce`
- 本轮复跑结果：
  - `bash script/run-op-mlir-s3-expectation.sh` -> `exit 0`
  - `bash script/run-op-mlir-s4-gen-kernel-expectation.sh` -> `exit 2`
  - `python3 -m pytest -q test/pass/nn_lowering/img2col1d.py test/pass/nn_lowering/img2col2d.py test/pass/nn_lowering/reduce_sum.py test/pass/nn_lowering/test_lowering_nn_lowering.py -k 'img2col or reduce_sum or softmax'` -> `12 passed, 36 deselected`
  - `python3 -m pytest -q test/dsl/test_expectation_softmax_negative_axis_normalize.py test/dsl/test_gen_kernel.py` -> `1 failed, 58 passed`
  - `python3 -m pytest -q test/script/test_run_op_mlir_s3_expectation.py test/script/test_run_op_mlir_s4_gen_kernel_expectation.py` -> `2 failed, 4 passed`
  - `rg -n '%[^ ]+ = "dma\\.(load|cast)"|DmaCastOp\\([^\\n]*result_type|DmaLoadOp\\([^\\n]*result_type|dma\\.(load|cast)\\([^)]*\\)\\s*->' kernel_gen/dialect/dma.py kernel_gen/dsl/ast kernel_gen/dsl/mlir_gen kernel_gen/dsl/gen_kernel.py kernel_gen/passes/lowering test/dsl test/pass -g '!*.md'` -> `exit 1`
- 最小阻断项：
  - [`script/run-op-mlir-s4-gen-kernel-expectation.sh`](../../script/run-op-mlir-s4-gen-kernel-expectation.sh) 仍把 expectation 入口拼成 `/home/lfr/expectation/dsl/gen_kernel/npu_demo_add_barrier`，脚本本身仍不可执行。
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py) 的 `test_gen_kernel_compiles_npu_demo_tiled_matmul_source` 仍失败；生成源码编译时继续报 `S_INT` 未声明。
  - [`test/script/test_run_op_mlir_s3_expectation.py`](../../test/script/test_run_op_mlir_s3_expectation.py) 仍锁定旧 stdout 片段 `[CASE-softmax-static]`；[`test/script/test_run_op_mlir_s4_gen_kernel_expectation.py`](../../test/script/test_run_op_mlir_s4_gen_kernel_expectation.py) 继续被同一 S4 脚本路径错误带失败。
- 结论说明：
  - 计划书正文已具备最终验收结论与验证基线，本段为本轮追加复核。
  - 当前仍不满足归档前置条件。

## 复核结论（2026-04-20 03:18:34 +0800）

- 复核人：`守护最好的爱莉希雅`
- 复核结论：`不通过`
- 复核基线：
  - 当前主仓执行目录：`/home/lfr/kernelcode_generate`
  - 当前 `HEAD`：`4f6dec477176b17a94a984c256a6d525e00aa361`
- 本轮复跑结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. bash script/run-op-mlir-s3-expectation.sh` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. bash script/run-op-mlir-s4-gen-kernel-expectation.sh` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_expectation_softmax_negative_axis_normalize.py test/dsl/test_gen_kernel.py` -> `1 failed, 60 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/script/test_run_op_mlir_s3_expectation.py test/script/test_run_op_mlir_s4_gen_kernel_expectation.py` -> `3 failed, 3 passed`
  - `rg -n '%[^ ]+ = "dma\\.(load|cast)"|DmaCastOp\\([^\\n]*result_type|DmaLoadOp\\([^\\n]*result_type|dma\\.(load|cast)\\([^)]*\\)\\s*->' kernel_gen/dialect/dma.py kernel_gen/dsl/ast kernel_gen/dsl/mlir_gen kernel_gen/dsl/gen_kernel.py kernel_gen/passes/lowering test/dsl test/pass -g '!*.md'` -> `exit 1`
- 最小阻断项：
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py) 的 `test_gen_kernel_emits_npu_demo_dma_alloc_module` 仍失败；当前 `gen_kernel` 对动态 `dma.alloc` 参数签名生成的是 `long long`，而测试仍锁定 `S_INT`。
  - [`test/script/test_run_op_mlir_s3_expectation.py`](../../test/script/test_run_op_mlir_s3_expectation.py) 仍锁定旧 `PYTHONPATH=/home/lfr` 口径；当前脚本实际输出为 `PYTHONPATH=/home/lfr/kernelcode_generate:.`。
  - [`test/script/test_run_op_mlir_s4_gen_kernel_expectation.py`](../../test/script/test_run_op_mlir_s4_gen_kernel_expectation.py) 仍锁定旧 expectation 入口路径 `/home/lfr/expectation/...`；当前脚本实际输出与执行入口均已切到 `/home/lfr/kernelcode_generate/expectation/...`。
- 结论说明：
  - `S3` / `S4` 两个 expectation 脚本入口与旧 `dma.load / dma.cast` result 形态审计均已恢复通过。
  - 当前剩余阻断已收敛到 `gen_kernel` 动态 `dma.alloc` 签名与两条脚本测试断言未同步，因此本计划仍不满足归档前置条件。

## 复核结论（2026-04-20 03:18:35 +0800）

- 复核人：`大闸蟹`
- 复核结论：`不通过`
- 复核基线：
  - 当前主仓分支：`main`
  - 当前主仓 `HEAD`：`4f6dec477176b17a94a984c256a6d525e00aa361`
  - 本轮按计划书 `S5` 当前正文验收项，在最新主线现场直接复跑。
- 本轮复跑结果：
  - `bash script/run-op-mlir-s3-expectation.sh` -> `exit 0`
  - `bash script/run-op-mlir-s4-gen-kernel-expectation.sh` -> `exit 0`
  - `python3 -m pytest -q test/pass/nn_lowering/img2col1d.py test/pass/nn_lowering/img2col2d.py test/pass/nn_lowering/reduce_sum.py test/pass/nn_lowering/test_lowering_nn_lowering.py -k 'img2col or reduce_sum or softmax'` -> `12 passed, 37 deselected`
  - `python3 -m pytest -q test/dsl/test_expectation_softmax_negative_axis_normalize.py test/dsl/test_gen_kernel.py` -> `1 failed, 60 passed`
  - `python3 -m pytest -q test/script/test_run_op_mlir_s3_expectation.py test/script/test_run_op_mlir_s4_gen_kernel_expectation.py` -> `3 failed, 3 passed`
  - `rg -n '%[^ ]+ = "dma\\.(load|cast)"|DmaCastOp\\([^\\n]*result_type|DmaLoadOp\\([^\\n]*result_type|dma\\.(load|cast)\\([^)]*\\)\\s*->' kernel_gen/dialect/dma.py kernel_gen/dsl/ast kernel_gen/dsl/mlir_gen kernel_gen/dsl/gen_kernel.py kernel_gen/passes/lowering test/dsl test/pass -g '!*.md'` -> `exit 1`
- 最小阻断项：
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py) 的 `test_gen_kernel_emits_npu_demo_dma_alloc_module` 仍失败；当前 `gen_kernel` 为动态 `dma.alloc` 生成的是 `long long` 形参，而测试仍锁 `S_INT` 签名。
  - [`test/script/test_run_op_mlir_s3_expectation.py`](../../test/script/test_run_op_mlir_s3_expectation.py) 与 [`test/script/test_run_op_mlir_s4_gen_kernel_expectation.py`](../../test/script/test_run_op_mlir_s4_gen_kernel_expectation.py) 仍未与新脚本口径对齐：`--print-command` 的 `PYTHONPATH` / 入口路径期望仍锁旧值，`S4` 的 fake-python 断言也仍锁旧 expectation 入口。
- 结论说明：
  - 旧的 `S4` 脚本路径错误已在最新主线消除。
  - 当前仍不满足归档前置条件。

## 复核结论（2026-04-20 06:16:53 +0800）

- 复核人：`守护最好的爱莉希雅`
- 复核结论：`不通过`
- 复核基线：
  - 当前主线分支：`main`
  - 当前主线 `HEAD`：`21aacc80fe70cd76d53785f6aeba9a4251b9d0ff`
  - 本轮按计划书 `S5` 当前正文验收项，在最新主线现场直接复跑。
- 本轮复跑结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. bash script/run-op-mlir-s3-expectation.sh` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. bash script/run-op-mlir-s4-gen-kernel-expectation.sh` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/nn_lowering/img2col1d.py test/pass/nn_lowering/img2col2d.py test/pass/nn_lowering/reduce_sum.py test/pass/nn_lowering/test_lowering_nn_lowering.py -k 'img2col or reduce_sum or softmax'` -> `12 passed, 37 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_expectation_softmax_negative_axis_normalize.py test/dsl/test_gen_kernel.py` -> `61 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/script/test_run_op_mlir_s3_expectation.py test/script/test_run_op_mlir_s4_gen_kernel_expectation.py` -> `2 failed, 4 passed`
  - `rg -n '%[^ ]+ = "dma\\.(load|cast)"|DmaCastOp\\([^\\n]*result_type|DmaLoadOp\\([^\\n]*result_type|dma\\.(load|cast)\\([^)]*\\)\\s*->' kernel_gen/dialect/dma.py kernel_gen/dsl/ast kernel_gen/dsl/mlir_gen kernel_gen/dsl/gen_kernel.py kernel_gen/passes/lowering test/dsl test/pass -g '!*.md'` -> `exit 1`
- 最小阻断项：
  - [`test/script/test_run_op_mlir_s4_gen_kernel_expectation.py`](../../test/script/test_run_op_mlir_s4_gen_kernel_expectation.py) 的两条断言仍锁旧的 `PYTHONPATH={REPO_ROOT}:{MAIN_REPO_ROOT}` 双仓拼接口径；当前脚本实际输出和执行环境已经收口为单仓 `PYTHONPATH={REPO_ROOT}`，导致：
    - `test_print_command_uses_worktree_and_main_repo_paths`
    - `test_script_runs_expectation_from_worktree`
    持续失败。
- 结论说明：
  - 当前主线下 `S3/S4` 脚本、`nn_lowering` 子集、`dsl` 子集和旧 `dma.load / dma.cast` result 形态残留扫描均已恢复通过。
  - 归档前置条件仍卡在 [`test/script/test_run_op_mlir_s4_gen_kernel_expectation.py`](../../test/script/test_run_op_mlir_s4_gen_kernel_expectation.py) 对旧 `PYTHONPATH` 口径的两条脚本测试断言未同步收口。

## 当前唯一修复任务（2026-04-20 06:19:02 +0800）

- 任务号：`T-20260420-630cf01b`
- `worktree`：`/home/lfr/kernelcode_generate/wt-20260420-op-mlir-fix-s8`
- 记录文件：`/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/16/20260420-op-mlir-fix-s8.md`
- 最小修复目标：
  - 修复 [`test/script/test_run_op_mlir_s4_gen_kernel_expectation.py`](../../test/script/test_run_op_mlir_s4_gen_kernel_expectation.py) 仍锁旧 `PYTHONPATH={REPO_ROOT}:{MAIN_REPO_ROOT}` 双仓拼接口径的两条断言，使其与当前脚本已收口的单仓 `PYTHONPATH={REPO_ROOT}` 一致。
  - 恢复以下两条脚本测试全绿：
    - `test_print_command_uses_worktree_and_main_repo_paths`
    - `test_script_runs_expectation_from_worktree`
  - 保持 [`script/run-op-mlir-s4-gen-kernel-expectation.sh`](../../script/run-op-mlir-s4-gen-kernel-expectation.sh) 继续 `exit 0`，且不回退已通过的 `S3/S4` 脚本、`dsl` 子集、`nn_lowering` 子集与旧 `dma.load / dma.cast` result 形态残留扫描结果。

## 复核结论（2026-04-20 06:27:30 +0800）

- 复核人：`守护最好的爱莉希雅`
- 复核结论：`不通过`
- 复核基线：
  - 当前主线分支：`main`
  - 当前主线 `HEAD`：`e6bd194b5e9d31b37a6ba4de534d1f97df5c7888`
  - 本轮按计划书 `S5` 当前正文验收项，在最新主线现场直接复跑。
- 本轮复跑结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. bash script/run-op-mlir-s3-expectation.sh` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. bash script/run-op-mlir-s4-gen-kernel-expectation.sh` -> `exit 1`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/nn_lowering/img2col1d.py test/pass/nn_lowering/img2col2d.py test/pass/nn_lowering/reduce_sum.py test/pass/nn_lowering/test_lowering_nn_lowering.py -k 'img2col or reduce_sum or softmax'` -> `12 passed, 37 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_expectation_softmax_negative_axis_normalize.py test/dsl/test_gen_kernel.py` -> `61 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/script/test_run_op_mlir_s3_expectation.py test/script/test_run_op_mlir_s4_gen_kernel_expectation.py` -> `1 failed, 5 passed`
  - `rg -n '%[^ ]+ = "dma\\.(load|cast)"|DmaCastOp\\([^\\n]*result_type|DmaLoadOp\\([^\\n]*result_type|dma\\.(load|cast)\\([^)]*\\)\\s*->' kernel_gen/dialect/dma.py kernel_gen/dsl/ast kernel_gen/dsl/mlir_gen kernel_gen/dsl/gen_kernel.py kernel_gen/passes/lowering test/dsl test/pass -g '!*.md'` -> `exit 1`
- 最小阻断项：
  - [`expectation/dsl/gen_kernel/npu_demo_add_barrier`](../../expectation/dsl/gen_kernel/npu_demo_add_barrier) 当前在真实直跑时仍触发 `assert source == _expected(space_enum)` 失败，导致：
    - [`script/run-op-mlir-s4-gen-kernel-expectation.sh`](../../script/run-op-mlir-s4-gen-kernel-expectation.sh) `exit 1`
    - [`test/script/test_run_op_mlir_s4_gen_kernel_expectation.py`](../../test/script/test_run_op_mlir_s4_gen_kernel_expectation.py) 中 `test_script_runs_real_gen_kernel_expectation` 继续失败。
- 结论说明：
  - 上一轮唯一阻断的双仓 `PYTHONPATH` 脚本断言已在最新主线收口，不再是当前最小阻断项。
  - 当前主线下 `S3` 脚本、`nn_lowering` 子集、`dsl` 子集和旧 `dma.load / dma.cast` result 形态残留扫描均保持通过；归档前置条件现仅卡在 `expectation/dsl/gen_kernel/npu_demo_add_barrier` 的真实源码断言未通过。

## 复核结论（2026-04-20 06:30:12 +0800）

- 复核人：`大闸蟹`
- 复核结论：`不通过`
- 复核基线：
  - 当前主线分支：`main`
  - 当前主线 `HEAD`：`e6bd194b5e9d31b37a6ba4de534d1f97df5c7888`
  - 本轮按计划书 `S5` 当前正文验收项，在最新主线现场直接复跑。
- 本轮复跑结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. bash script/run-op-mlir-s3-expectation.sh` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. bash script/run-op-mlir-s4-gen-kernel-expectation.sh` -> `exit 1`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/nn_lowering/img2col1d.py test/pass/nn_lowering/img2col2d.py test/pass/nn_lowering/reduce_sum.py test/pass/nn_lowering/test_lowering_nn_lowering.py -k 'img2col or reduce_sum or softmax'` -> `12 passed, 37 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_expectation_softmax_negative_axis_normalize.py test/dsl/test_gen_kernel.py` -> `61 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/script/test_run_op_mlir_s3_expectation.py test/script/test_run_op_mlir_s4_gen_kernel_expectation.py` -> `1 failed, 5 passed`
  - `rg -n '%[^ ]+ = "dma\\.(load|cast)"|DmaCastOp\\([^\\n]*result_type|DmaLoadOp\\([^\\n]*result_type|dma\\.(load|cast)\\([^)]*\\)\\s*->' kernel_gen/dialect/dma.py kernel_gen/dsl/ast kernel_gen/dsl/mlir_gen kernel_gen/dsl/gen_kernel.py kernel_gen/passes/lowering test/dsl test/pass -g '!*.md'` -> `exit 1`
- 最小阻断项：
  - [`expectation/dsl/gen_kernel/npu_demo_add_barrier`](../../expectation/dsl/gen_kernel/npu_demo_add_barrier) 的真实 expectation 仍未通过；当前 `gen_kernel(target="npu_demo")` 产出的源码与 expectation 文本只剩缩进空格差异，但因为该文件使用整串源码相等断言，仍导致 [`script/run-op-mlir-s4-gen-kernel-expectation.sh`](../../script/run-op-mlir-s4-gen-kernel-expectation.sh) `exit 1`，并继续带失败 [`test/script/test_run_op_mlir_s4_gen_kernel_expectation.py`](../../test/script/test_run_op_mlir_s4_gen_kernel_expectation.py) 的 `test_script_runs_real_gen_kernel_expectation`。
- 结论说明：
  - 当前主线下 `S3` 脚本、`nn_lowering` 子集、`dsl` 子集、旧 `dma.load / dma.cast` result 形态残留扫描，以及 [`test/script/test_run_op_mlir_s3_expectation.py`](../../test/script/test_run_op_mlir_s3_expectation.py) 均已恢复通过。
  - 归档前置条件当前只剩 `S4` 的真实 `gen_kernel` expectation 文本未收口，因此本计划仍不满足归档前置条件。

## 复核结论（2026-04-20 06:44:18 +0800）

- 复核人：`大闸蟹`
- 复核结论：`通过`
- 复核基线：
  - 最新主线提交：`origin/main@3cd5ef6de5eadb5e41ccc3c5ba3420d72fec0e11`
  - 当前主仓执行目录存在未提交本地改动，且本地 `main` 落后 `origin/main` 一次提交；为避免脏现场污染，本轮实际复验使用同级干净只读 `worktree`：`/home/lfr/kernelcode_generate/wt-20260420-op-mlir-archive-check-temp`
- 本轮复跑结果：
  - `cd /home/lfr/kernelcode_generate/wt-20260420-op-mlir-archive-check-temp && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. bash script/run-op-mlir-s3-expectation.sh` -> `exit 0`
  - `cd /home/lfr/kernelcode_generate/wt-20260420-op-mlir-archive-check-temp && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. bash script/run-op-mlir-s4-gen-kernel-expectation.sh` -> `exit 0`
  - `cd /home/lfr/kernelcode_generate/wt-20260420-op-mlir-archive-check-temp && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/nn_lowering/img2col1d.py test/pass/nn_lowering/img2col2d.py test/pass/nn_lowering/reduce_sum.py test/pass/nn_lowering/test_lowering_nn_lowering.py -k 'img2col or reduce_sum or softmax'` -> `12 passed, 37 deselected`
  - `cd /home/lfr/kernelcode_generate/wt-20260420-op-mlir-archive-check-temp && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_expectation_softmax_negative_axis_normalize.py test/dsl/test_gen_kernel.py` -> `61 passed`
  - `cd /home/lfr/kernelcode_generate/wt-20260420-op-mlir-archive-check-temp && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/script/test_run_op_mlir_s3_expectation.py test/script/test_run_op_mlir_s4_gen_kernel_expectation.py` -> `6 passed`
  - `cd /home/lfr/kernelcode_generate/wt-20260420-op-mlir-archive-check-temp && rg -n '%[^ ]+ = "dma\\.(load|cast)"|DmaCastOp\\([^\\n]*result_type|DmaLoadOp\\([^\\n]*result_type|dma\\.(load|cast)\\([^)]*\\)\\s*->' kernel_gen/dialect/dma.py kernel_gen/dsl/ast kernel_gen/dsl/mlir_gen kernel_gen/dsl/gen_kernel.py kernel_gen/passes/lowering test/dsl test/pass -g '!*.md'` -> `exit 1`
- 必要摘要：
  - `S3` / `S4` 两条 expectation 脚本、`nn_lowering` 子集、`dsl` 子集、脚本测试，以及旧 `dma.load / dma.cast` result 形态残留扫描都已在最新主线干净 task-site 恢复通过。
  - 先前阻断的 `npu_demo_add_barrier` 真实 expectation 已随 `3cd5ef6` 的缩进修复收口，不再阻断归档。
  - 当前已满足归档前置条件，可进入唯一归档任务链。

## 当前唯一修复任务（2026-04-20 06:28:55 +0800）

- 任务号：`T-20260420-491b077b`
- `worktree`：`/home/lfr/kernelcode_generate/wt-20260420-op-mlir-fix-s9`
- 记录文件：`/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/16/20260420-op-mlir-fix-s9.md`
- 最小修复目标：
  - 修复 [`expectation/dsl/gen_kernel/npu_demo_add_barrier`](../../expectation/dsl/gen_kernel/npu_demo_add_barrier) 真实直跑时的源码文本不一致问题，收口 expectation 文本与当前 `gen_kernel(target=\"npu_demo\")` 生成源码的一致性。
  - 恢复以下验收项全绿：
    - [`script/run-op-mlir-s4-gen-kernel-expectation.sh`](../../script/run-op-mlir-s4-gen-kernel-expectation.sh)
    - [`test/script/test_run_op_mlir_s4_gen_kernel_expectation.py`](../../test/script/test_run_op_mlir_s4_gen_kernel_expectation.py) 中 `test_script_runs_real_gen_kernel_expectation`
  - 保持已通过的 `S3` 脚本、`nn_lowering` 子集、`dsl` 子集、[`test/script/test_run_op_mlir_s3_expectation.py`](../../test/script/test_run_op_mlir_s3_expectation.py) 与旧 `dma.load / dma.cast` result 形态残留扫描结果不回退。
- 说明：
  - 上一轮 [`T-20260420-630cf01b`](../../DONE.md) 已完成并收口双仓 `PYTHONPATH` 脚本断言问题；当前仅保留本任务作为新的唯一修复入口。

## 计划目标

- 先把 `dialect / lowering / mlir_gen / gen_kernel` 的公开规范定准，再推动实现对齐，最终让 expectation 全部通过。
- 统一 `kernel` 写入类 op 为 `out-first`，统一 `dma` 写入类 op 为 `target-first`。
- 把 `dma.load / dma.cast` 从 result-op 改成 side-effect op，并同步清理 AST / parser / mlir_gen / lowering / gen_kernel 对旧 result 形态的依赖。
- 收口 `img2col / conv / matmul` 的动态符号语义到 `SymbolDim.get_value()` 基线。
- 收口 `softmax(value)` 默认轴职责：helper 入口先归一化，`mlir_gen / lowering` 只消费规范化后的稳定语义。

## 当前基线

- 当前公开合同：`kernel` 写入类应 `out-first`、`dma` 写入类应 `target-first`、`dma.load / dma.cast` 不再保留 result 形态、`softmax(value)` 默认负轴先在 helper 层归一化、`reduce` 本轮继续只支持单轴。
- 当前公开 API：`kernel.add(out, lhs, rhs)`、`dma.copy(target, source)`、`dma.cast(target, source) -> ()`、`dma.load(target, source, ...) -> ()`、`softmax(value)`。
- 当前实现入口：
  [`kernel_gen/dialect/kernel.py`](../../kernel_gen/dialect/kernel.py)、
  [`kernel_gen/dialect/dma.py`](../../kernel_gen/dialect/dma.py)、
  [`kernel_gen/passes/lowering/nn_lowering`](../../kernel_gen/passes/lowering/nn_lowering)、
  [`kernel_gen/dsl/mlir_gen/emit/core.py`](../../kernel_gen/dsl/mlir_gen/emit/core.py)、
  [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)。
- 当前测试与验收资产：
  [`expectation/pass/lowing`](../../expectation/pass/lowing)、
  [`expectation/dsl/gen_kernel`](../../expectation/dsl/gen_kernel)、
  [`expectation/dsl/mlir_gen/dialect/nn/softmax.py`](../../expectation/dsl/mlir_gen/dialect/nn/softmax.py)、
  [`test/pass/nn_lowering`](../../test/pass/nn_lowering)、
  [`test/dsl/test_expectation_softmax_negative_axis_normalize.py`](../../test/dsl/test_expectation_softmax_negative_axis_normalize.py)、
  [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)。
- 当前缺口或失败点：
  当前入口总数 `26`，通过 `8`，失败 `18`；主因不是 expectation 写错，而是实现仍按旧 operand 顺序或旧 dialect 建模工作。`img2col` 仍依赖裸符号名，合法动态 broadcast 仍被错拒，`softmax(value)` 默认负轴仍未统一上收，`dma.load / dma.cast` 仍残留 result 形态。

## 方案比较与选型

- 不采用方案：`继续按旧 operand 顺序 / 旧 result 建模回退 expectation`
- 不采用原因：`这会把当前已锁定的新合同再次打散，继续造成 dialect / lowering / mlir_gen / gen_kernel 四层分叉。`
- 采用方案：`先定新规范，再按“普通重排”和“建模重构”两条线分开收口实现，最后统一回归 expectation`
- 最小公开接口：`kernel 写入类 out-first；dma 写入类 target-first；dma.load / dma.cast 为 side-effect op；softmax 默认轴先在 helper 层规范化`

## 公开 API 设计

- 公开入口：`kernel` 写入类 op / `dma` 写入类 op / `dma.load` / `dma.cast` / `softmax(value)`
- 参数顺序：`写入目标第一个 operand；softmax 默认轴先归一化`
- 参数类型：`nn.memory / symbol.int / 已规范化 axis`
- 返回值：`普通写入类 op 无 SSA result；dma.load / dma.cast 也不再暴露 result 形态`

```text
kernel.add(out, lhs, rhs)
dma.copy(target, source)
dma.cast(target, source) -> ()
dma.load(target, source, offsets, sizes, strides) -> ()
softmax(value) => helper 层先把 axis=-1 归一化为 rank-1，再交给 mlir_gen / lowering
```

## 完成态定义

- `kernel` 写入类 op 全部 `out-first`，`dma` 写入类 op 全部 `target-first`。
- `dma.load / dma.cast` 不再保留 result 形态，相关 operation / dialect / AST / parser / mlir_gen / lowering / gen_kernel 全部改为消费副作用语义。
- `img2col / conv / matmul` 的动态符号表达式统一以 `SymbolDim` 语义和 `get_value()` 为公开比较基线。
- `softmax(value)` 默认负轴在 operation/helper 入口即被规范化，`mlir_gen / lowering` 不再各自兜底。
- [`expectation/pass/lowing`](../../expectation/pass/lowing) 与 [`expectation/dsl/gen_kernel`](../../expectation/dsl/gen_kernel) 中本轮覆盖 case 全部通过，且 expectation 不因实现妥协回退。

## 验收设计

- 验收资产：
  [`expectation/pass/lowing`](../../expectation/pass/lowing)、
  [`expectation/dsl/gen_kernel`](../../expectation/dsl/gen_kernel)、
  [`expectation/dsl/mlir_gen/dialect/nn/softmax.py`](../../expectation/dsl/mlir_gen/dialect/nn/softmax.py)
- 输入样例：
  `kernel.add(out, lhs, rhs)`、
  `dma.copy(target, source)`、
  `dma.cast(target, source)`、
  `softmax(value)`、
  `img2col` 动态符号输入、
  `broadcast([1, N] -> [M, N])`
- 锁定输出：
  `写入目标首 operand`、
  `dma.load / dma.cast 无 result`、
  `softmax` 轴为正轴、
  `img2col` 不再依赖裸符号名、
  `合法动态 broadcast 可 lower`
- 必过命令：
  `python3 -m expectation.pass.lowing`
  `python3 -m expectation.dsl.gen_kernel`
  `pytest -q test/pass/nn_lowering/test_expectation_img2col.py`
  `pytest -q test/pass/nn_lowering/test_expectation_broadcast_new_symbol_dim.py`
  `pytest -q test/dsl/test_expectation_softmax_negative_axis_normalize.py`
  `pytest -q test/dsl/test_gen_kernel.py`

## 本轮定稿规范

- `kernel / dma` dialect 中，凡是显式写入类 op，`out / target / dst` 默认放第一个 operand。
- `kernel.binary_elewise` 也必须遵守 `(%out, %lhs, %rhs)`；若实现仍为 `(%lhs, %rhs, %out)`，应修实现，不回退 expectation。
- `dma.load / dma.cast` 不再保留 result 形态；它们属于 dialect 建模重构，不是普通 operand 顺序调整。
- `softmax(value)` 的默认 `axis=-1` 规范化职责放在 operation / helper 入口层；`mlir_gen / lowering` 只消费规范化后的稳定语义。
- `reduce` 多轴当前不算缺陷；本轮口径仍然是“只支持 reduce dim 为一个”。
- expectation 不因当前实现而回退；本轮通过修改实现对齐 expectation。

## 缺口映射

1. `img2col` 动态维度推导硬编码依赖裸符号名，合法语义前缀随机符号会被错拒。
   - 文件：
     [`kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py)
2. 合法的动态 broadcast，如 `[1, N] -> [M, N]`，仍被 lowering 错拒。
   - 文件：
     [`kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py)
3. `mlir_gen` 没有消费 helper 层已规范化的 `softmax` 正轴语义。
   - 文件：
     [`kernel_gen/dsl/mlir_gen/emit/core.py`](../../kernel_gen/dsl/mlir_gen/emit/core.py)
4. `nn.cast lowering` 与 `dma.cast dialect` 建模不一致。
   - 文件：
     [`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)、
     [`kernel_gen/dialect/dma.py`](../../kernel_gen/dialect/dma.py)
5. `dma.load` 属于同类建模问题。
   - 文件：
     [`kernel_gen/dialect/dma.py`](../../kernel_gen/dialect/dma.py)
6. `kernel.binary_elewise` 的 operand 顺序当前实现仍与合同不一致。
   - 文件：
     [`kernel_gen/dialect/kernel.py`](../../kernel_gen/dialect/kernel.py)、
     [`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py)
   - 合同：
     `kernel.binary_elewise(%out, %lhs, %rhs)`
   - 现状：
     当前 dialect 定义与 lowering 构造仍按 `(%lhs, %rhs, %out)` 工作；这属于实现缺口，不允许通过回退 expectation 解决。
7. `gen_kernel` 与 `emit_c` 还需要吃进新规范的 dialect 结果。
   - 文件：
     [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)、
     [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
8. `img2col / conv / matmul` 的动态符号表达式缺少统一规整与公开值序列化口径。
   - 结论：
     这几组不应继续在 helper / spec / IR 三侧各维护一份符号名判定逻辑，而应统一以 `SymbolDim` 语义和 `get_value()` 公开值比较为准。
9. `dsl/mlir_gen` 与 helper call lowering 仍保留旧的调用接口假设。
   - 结论：
     需要同步完成 helper call 参数重排、返回值/无返回分流、`symbol / memory` 类型映射，以及 `dma.load / dma.cast` 旧 result 形态分支清理。

## 阶段拆分

### S1：规范定稿与影响面冻结

#### 阶段目标

- 冻结本轮公开合同、职责边界与“普通重排 / 建模重构”的分界线。

#### 目标 spec / API

- [`spec/dialect/kernel.md`](../../spec/dialect/kernel.md)
- [`spec/dialect/dma.md`](../../spec/dialect/dma.md)
- [`spec/pass/lowering/nn_lowering/spec.md`](../../spec/pass/lowering/nn_lowering/spec.md)
- [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- `公开 API：kernel 写入类 out-first；dma 写入类 target-first；dma.load / dma.cast 为 side-effect op；softmax 默认轴先在 helper 层归一化`

#### 预期示例代码

```text
kernel.add(out, lhs, rhs)
kernel.binary_elewise(out, lhs, rhs, kind="add")
dma.copy(target, source)
dma.cast(target, source) -> ()
softmax(value) -> helper 层先把 axis=-1 规整成正轴
```

#### 预期输出

```text
spec 和计划书同时写清：哪些 op 只是重排，哪些 op 是建模重构；lowering/mlir_gen/gen_kernel 只消费规范化后的稳定语义
```

#### 目标验收资产

- [`ARCHITECTURE/plan/operation_mlir_gen_expectation_green_plan.md`](./operation_mlir_gen_expectation_green_plan.md)
- `rg -n "out-first|target-first|side-effect op|softmax\\(value\\)|只支持 reduce dim 为一个" ARCHITECTURE/plan/operation_mlir_gen_expectation_green_plan.md spec/dialect/kernel.md spec/dialect/dma.md spec/pass/lowering/nn_lowering/spec.md spec/dsl/mlir_gen.md spec/dsl/gen_kernel.md`

#### 验收必过项目

- `rg -n "out-first|target-first|side-effect op" ARCHITECTURE/plan/operation_mlir_gen_expectation_green_plan.md`
- `rg -n "softmax\\(value\\).*helper|只支持 reduce dim 为一个" ARCHITECTURE/plan/operation_mlir_gen_expectation_green_plan.md spec/pass/lowering/nn_lowering/spec.md`

#### 任务新建建议

- `任务类型：spec`
- `任务目标：冻结新 operand 顺序、dma.load/dma.cast 建模与 softmax 默认轴职责边界`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260418-op-mlir-plan.md`

### S2：Dialect 重排与建模重构

#### 阶段目标

- 完成 kernel/dma 写入类 op 的顺序统一，并把 `dma.load / dma.cast` 重构为 target-first side-effect op。

#### 目标 spec / API

- [`spec/dialect/kernel.md`](../../spec/dialect/kernel.md)
- [`spec/dialect/dma.md`](../../spec/dialect/dma.md)
- `公开 API：kernel 写入类 out-first；dma 写入类 target-first；dma.load / dma.cast 无 SSA result`

#### 预期示例代码

```text
"kernel.select"(%out, %cond, %lhs, %rhs) -> ()
"kernel.binary_elewise"(%out, %lhs, %rhs) -> ()
"dma.copy"(%target, %source) -> ()
"dma.cast"(%target, %source) -> ()
"dma.load"(%target, %source, ...) -> ()
```

#### 预期输出

```text
dialect verifier / builder / printer 与 AST/parser 一起切到新顺序；dma.load / dma.cast 不再暴露 result/result_type
```

#### 目标验收资产

- [`test/dialect/test_kernel_dialect.py`](../../test/dialect/test_kernel_dialect.py)
- [`test/dialect/test_dma_dialect.py`](../../test/dialect/test_dma_dialect.py)
- `rg -n 'result_type|\\.result\\b' kernel_gen/dialect kernel_gen/dsl/ast`
- `python3 -m expectation.pass.lowing.nn_lowering.element_binary`
- `python3 -m pytest -q test/pass/nn_lowering/element_binary_add.py test/pass/nn_lowering/element_binary_sub.py test/pass/nn_lowering/element_binary_mul.py test/pass/nn_lowering/element_binary_div.py test/pass/nn_lowering/element_binary_truediv.py`

#### 验收必过项目

- `pytest -q test/dialect/test_kernel_dialect.py`
- `pytest -q test/dialect/test_dma_dialect.py`
- `script/run-op-mlir-s3-expectation.sh`
- `python3 -m pytest -q test/pass/nn_lowering/element_binary_add.py test/pass/nn_lowering/element_binary_sub.py test/pass/nn_lowering/element_binary_mul.py test/pass/nn_lowering/element_binary_div.py test/pass/nn_lowering/element_binary_truediv.py`
- `rg -n 'result_type|\\.result\\b' kernel_gen/dialect/dma.py kernel_gen/dsl/ast/nodes.py kernel_gen/dsl/ast/parser.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：完成 kernel/dma 写入类顺序统一，并把 dma.load/dma.cast 重构为副作用 op`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260418-op-mlir-plan.md`

### S3：Lowering 对齐

#### 阶段目标

- 让 `nn_lowering` 全面消费新 dialect，并收口 `img2col / broadcast / cast / reduce_softmax / matmul` 缺口。

#### 目标 spec / API

- [`spec/pass/lowering/nn_lowering/spec.md`](../../spec/pass/lowering/nn_lowering/spec.md)
- `公开 API：lowering 只消费规范化后的稳定语义，不再依赖旧顺序或裸符号名`

#### 预期示例代码

```text
img2col 动态参数比较统一按 SymbolDim.get_value()
broadcast([1, N] -> [M, N]) 合法 lower
nn.cast lower 为 target-first、no-result 风格
kernel.binary_elewise lower 为 (%out, %lhs, %rhs)
```

#### 预期输出

```text
lower-nn 输出不再依赖裸符号名；合法动态 broadcast 可过；旧顺序和旧 result 形态不再残留
```

#### 目标验收资产

- [`expectation/pass/lowing/nn_lowering/select.py`](../../expectation/pass/lowing/nn_lowering/select.py)
- [`expectation/pass/lowing/nn_lowering/element_binary`](../../expectation/pass/lowing/nn_lowering/element_binary)
- [`expectation/pass/lowing/nn_lowering/softmax.py`](../../expectation/pass/lowing/nn_lowering/softmax.py)
- [`expectation/pass/lowing/nn_lowering/matmul.py`](../../expectation/pass/lowing/nn_lowering/matmul.py)
- [`expectation/pass/lowing/nn_lowering/reduce/reduce_sum.py`](../../expectation/pass/lowing/nn_lowering/reduce/reduce_sum.py)
- [`expectation/pass/lowing/nn_lowering/img2col/img2col1d.py`](../../expectation/pass/lowing/nn_lowering/img2col/img2col1d.py)
- [`expectation/pass/lowing/nn_lowering/img2col/img2col2d.py`](../../expectation/pass/lowing/nn_lowering/img2col/img2col2d.py)
- [`expectation/pass/lowing/nn_lowering/broadcast_new_symbol_dim.py`](../../expectation/pass/lowing/nn_lowering/broadcast_new_symbol_dim.py)

#### 验收必过项目

- `script/run-op-mlir-s3-expectation.sh`
- `pytest -q test/pass/nn_lowering/img2col1d.py test/pass/nn_lowering/img2col2d.py`
- `pytest -q test/pass/nn_lowering/reduce_sum.py test/pass/nn_lowering/test_lowering_nn_lowering.py -k 'reduce_sum or softmax'`
- `pytest -q test/script/test_run_op_mlir_s3_expectation.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：修正 nn_lowering 以消费新 dialect，并收口 img2col/broadcast/cast 相关缺口`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260418-op-mlir-plan.md`

### S4：MLIR Gen / Gen Kernel 对齐

#### 阶段目标

- 让 `mlir_gen / gen_kernel / helper call lowering` 一起消费新合同，去掉旧 result 和旧顺序假设。

#### 目标 spec / API

- [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- `公开 API：上层 helper 负责默认值归一化；mlir_gen 负责语法映射与 operand/type 排布；gen_kernel 消费新 IR 直接生成源码`

#### 预期示例代码

```text
softmax(value) -> helper 层已给出正轴
mlir_gen 发出 target-first / out-first IR
gen_kernel(target="npu_demo") 直接消费新 IR，不再依赖旧 helper 签名
```

#### 预期输出

```text
softmax 负轴 expectation 通过；helper call 参数重排与返回值/无返回分流完成；旧 result 分支清理干净
```

#### 目标验收资产

- [`expectation/dsl/mlir_gen/dialect/nn/softmax.py`](../../expectation/dsl/mlir_gen/dialect/nn/softmax.py)
- [`expectation/dsl/gen_kernel/npu_demo_add_barrier`](../../expectation/dsl/gen_kernel/npu_demo_add_barrier)
- [`test/dsl/test_expectation_softmax_negative_axis_normalize.py`](../../test/dsl/test_expectation_softmax_negative_axis_normalize.py)
- [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)

#### 验收必过项目

- `pytest -q test/dsl/test_expectation_softmax_negative_axis_normalize.py`
- `script/run-op-mlir-s4-gen-kernel-expectation.sh`
- `pytest -q test/dsl/test_gen_kernel.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：修正 mlir_gen/gen_kernel/helper call lowering 以消费新顺序和新建模`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260418-op-mlir-plan.md`

### S5：Expectation 回收与验收

#### 阶段目标

- 重新跑 expectation 与 pytest，确认新规范覆盖的 case 全部通过，且旧签名/旧顺序已清干净。

#### 目标 spec / API

- [`expectation/pass/lowing`](../../expectation/pass/lowing)
- [`expectation/dsl/gen_kernel`](../../expectation/dsl/gen_kernel)
- [`expectation/dsl/mlir_gen/dialect/nn/softmax.py`](../../expectation/dsl/mlir_gen/dialect/nn/softmax.py)
- `公开 API：expectation 作为合同真源，不因实现妥协回退`

#### 预期示例代码

```text
新顺序正例通过
旧顺序负例失败
result 数与 SSA use-def 符合无 result 建模
```

#### 预期输出

```text
script/run-op-mlir-s3-expectation.sh -> exit 0
script/run-op-mlir-s4-gen-kernel-expectation.sh -> exit 0
pytest 通过，且旧 `dma.load/dma.cast` result 形态检索为空
```

#### 目标验收资产

- [`expectation/pass/lowing`](../../expectation/pass/lowing)
- [`expectation/dsl/gen_kernel`](../../expectation/dsl/gen_kernel)
- [`expectation/dsl/mlir_gen/dialect/nn/softmax.py`](../../expectation/dsl/mlir_gen/dialect/nn/softmax.py)
- `rg -n '%[^ ]+ = "dma\\.(load|cast)"|DmaCastOp\\([^\\n]*result_type|DmaLoadOp\\([^\\n]*result_type|dma\\.(load|cast)\\([^)]*\\)\\s*->' kernel_gen/dialect/dma.py kernel_gen/dsl/ast kernel_gen/dsl/mlir_gen kernel_gen/dsl/gen_kernel.py kernel_gen/passes/lowering test/dsl test/pass -g '!*.md'`

#### 验收必过项目

- `script/run-op-mlir-s3-expectation.sh`
- `script/run-op-mlir-s4-gen-kernel-expectation.sh`
- `pytest -q test/pass/nn_lowering/img2col1d.py test/pass/nn_lowering/img2col2d.py test/pass/nn_lowering/reduce_sum.py test/pass/nn_lowering/test_lowering_nn_lowering.py -k 'img2col or reduce_sum or softmax'`
- `pytest -q test/dsl/test_expectation_softmax_negative_axis_normalize.py test/dsl/test_gen_kernel.py`
- `pytest -q test/script/test_run_op_mlir_s3_expectation.py test/script/test_run_op_mlir_s4_gen_kernel_expectation.py`
- `rg -n '%[^ ]+ = "dma\\.(load|cast)"|DmaCastOp\\([^\\n]*result_type|DmaLoadOp\\([^\\n]*result_type|dma\\.(load|cast)\\([^)]*\\)\\s*->' kernel_gen/dialect/dma.py kernel_gen/dsl/ast kernel_gen/dsl/mlir_gen kernel_gen/dsl/gen_kernel.py kernel_gen/passes/lowering test/dsl test/pass -g '!*.md'`

#### 任务新建建议

- `任务类型：review`
- `任务目标：复核 expectation 与 pytest 是否按新合同全量通过，并清除旧签名残留`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260418-op-mlir-plan.md`

## 待确认项

- 问题：`当前无新的用户待确认项`
- 可选项：`无`
- 差异：`无`
- 推荐项：`按当前已确认口径继续推进，并等待大闸蟹给出最终通过/不通过结论`

## 用户确认与协同约束

- `用户确认状态：已确认`
- `未确认事项：无`
- `用户确认结论：kernel 写入类 out-first；dma 写入类 target-first；dma.load / dma.cast 单列为 side-effect op 重构；softmax(value) 默认 axis=-1 在 operation/helper 入口先规范化；reduce 多轴本轮不写成缺陷`
- `执行边界补充：执行人不得修改 expectation 文件，且本计划取消“可改文件”白名单段，统一按禁止修改面管理`
- `未确认前处理要求：不得自行补假设`
- `若用户要求至少询问 3 人：已要求并完成，且所有对象需直接用 -talk 回复`
- `询问记录 1：小李飞刀 / agents/codex-multi-agents/log/talk.log / 已回复`
- `询问记录 2：提莫炖蘑菇 / agents/codex-multi-agents/log/talk.log / 已回复`
- `询问记录 3：不要啊教练 / agents/codex-multi-agents/log/talk.log / 已回复`
- `询问记录 4：大闸蟹 / agents/codex-multi-agents/log/talk.log / 已给出“不通过”结论与阻断项`
- `询问记录 4：大闸蟹 / agents/codex-multi-agents/log/talk.log / 已复评通过`
- `询问记录 5：jcc你莫辜负 / agents/codex-multi-agents/log/talk.log / 已回复`
- `询问记录 6：金铲铲大作战 / agents/codex-multi-agents/log/talk.log / 已回复`

## 参考资料

- [`agents/standard/计划书标准.md`](../../agents/standard/计划书标准.md)
- [`agents/standard/计划书模板.md`](../../agents/standard/计划书模板.md)
- [`agents/standard/计划书完成样板.md`](../../agents/standard/计划书完成样板.md)
- [`agents/codex-multi-agents/log/talk.log`](../../agents/codex-multi-agents/log/talk.log)
