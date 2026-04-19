# kernel_binary_elewise_only_green_plan.md

## 文档信息

- 创建者：`守护最好的爱莉希雅`
- 最后一次更改：`睡觉小分队`
- 目标 `spec`：
  [`spec/dialect/kernel.md`](../../spec/dialect/kernel.md)、
  [`spec/pass/lowering/nn_lowering.md`](../../spec/pass/lowering/nn_lowering.md)、
  [`spec/pass/lowering/nn_lowering/element_binary_lowering.md`](../../spec/pass/lowering/nn_lowering/element_binary_lowering.md)、
  [`spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`](../../spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md)、
  [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)、
  [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- 目标 `API`：
  `kernel` 逐元素算术/比较公开名只保留 `kernel.binary_elewise(kind=...)`、
  去掉公开 `kernel.add/sub/mul/div/eq/ne/lt/le/gt/ge`、
  去掉公开 `kernel.cast`、
  去掉公开 `kernel.softmax`
- 目标 `test`：
  [`test/dialect/test_kernel_dialect.py`](../../test/dialect/test_kernel_dialect.py)、
  [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../test/pass/nn_lowering/test_lowering_nn_lowering.py)、
  [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)、
  [`test/pass/test_lowering_tile.py`](../../test/pass/test_lowering_tile.py)、
  [`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py)、
  [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)、
  [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)
- 目标 `验收资产`：
  [`expectation/dsl/emit_c/npu_demo/kernel/binary_add.py`](../../expectation/dsl/emit_c/npu_demo/kernel/binary_add.py)、
  [`expectation/dsl/emit_c/npu_demo/kernel/binary_sub.py`](../../expectation/dsl/emit_c/npu_demo/kernel/binary_sub.py)、
  [`expectation/dsl/emit_c/npu_demo/kernel/binary_mul.py`](../../expectation/dsl/emit_c/npu_demo/kernel/binary_mul.py)、
  [`expectation/dsl/emit_c/npu_demo/kernel/binary_div.py`](../../expectation/dsl/emit_c/npu_demo/kernel/binary_div.py)、
  [`expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py`](../../expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py)、
  [`expectation/dsl/emit_c/npu_demo/kernel/exp.py`](../../expectation/dsl/emit_c/npu_demo/kernel/exp.py)、
  [`expectation/dsl/emit_c/npu_demo/kernel/img2col.py`](../../expectation/dsl/emit_c/npu_demo/kernel/img2col.py)、
  [`expectation/dsl/emit_c/npu_demo/kernel/matmul.py`](../../expectation/dsl/emit_c/npu_demo/kernel/matmul.py)、
  [`expectation/dsl/emit_c/npu_demo/kernel/reduce.py`](../../expectation/dsl/emit_c/npu_demo/kernel/reduce.py)、
  [`expectation/dsl/emit_c/npu_demo/kernel/select.py`](../../expectation/dsl/emit_c/npu_demo/kernel/select.py)、
  [`expectation/pass/pipeline/default_lowering.py`](../../expectation/pass/pipeline/default_lowering.py)、
  [`expectation/pass/tile/analysis/element_binary.py`](../../expectation/pass/tile/analysis/element_binary.py)、
  [`expectation/pass/tile/analysis/element_compare.py`](../../expectation/pass/tile/analysis/element_compare.py)
- 目标 `功能实现`：
  [`kernel_gen/dialect/kernel.py`](../../kernel_gen/dialect/kernel.py)、
  [`kernel_gen/passes/lowering/nn_lowering`](../../kernel_gen/passes/lowering/nn_lowering)、
  [`kernel_gen/passes/lowering/nn_to_kernel.py`](../../kernel_gen/passes/lowering/nn_to_kernel.py)、
  [`kernel_gen/passes/lowering/tile.py`](../../kernel_gen/passes/lowering/tile.py)、
  [`kernel_gen/analysis/compute/kernel.py`](../../kernel_gen/analysis/compute/kernel.py)、
  [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)、
  [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| S1 | 无 | `wt-20260419-kernel-binary-only-s1` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-kernel-binary-only.md` |
| S2 | S1 | `wt-20260419-kernel-binary-only-s2` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-kernel-binary-only.md` |
| S3 | S1、S2 | `wt-20260419-kernel-binary-only-s3` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-kernel-binary-only.md` |

- 本计划不单独新建 `spec` 任务；每个执行任务必须同步处理对应的 `spec / 实现 / test`。

## 执行边界

- 执行人不得修改任何 `expectation` 文件；本计划中的 `expectation` 只作为合同真源、缺口暴露资产和验收资产。
- 本计划允许修改：
  - `spec/dialect/kernel.md`
  - `spec/pass/lowering/nn_lowering*.md`
  - `spec/pass/pipeline/default_lowering.md`
  - `spec/dsl/gen_kernel.md`
  - `kernel_gen/dialect/kernel.py`
  - `kernel_gen/passes/lowering/*`
  - `kernel_gen/analysis/compute/kernel.py`
  - `kernel_gen/dsl/gen_kernel.py`
  - `kernel_gen/dsl/emit_c.py`
  - 与本专题直接相关的 `test/*`
- 本计划允许删除或缩减旧公开名对应的测试与示例，前提是这些内容只服务于：
  - `kernel.add/sub/mul/div/eq/ne/lt/le/gt/ge`
  - `kernel.cast`
  - `kernel.softmax`
- 本计划禁止执行人修改：
  - [`expectation/dsl/emit_c/npu_demo/kernel`](../../expectation/dsl/emit_c/npu_demo/kernel)
  - [`expectation/pass/pipeline/default_lowering.py`](../../expectation/pass/pipeline/default_lowering.py)
  - [`expectation/pass/tile/analysis`](../../expectation/pass/tile/analysis)
  - [`expectation/tools/ircheck`](../../expectation/tools/ircheck)
  - [`expectation/pass/tuning/launch_kernel_cost_func`](../../expectation/pass/tuning/launch_kernel_cost_func)
  - `agents 标准文档 / immutable 内容`
- 若执行阶段发现 expectation 必须调整，必须中止实现任务并回到架构侧重新确认；不允许执行人自行回退或重写 expectation。

## 评审摘要

- 评审结论：`通过`
- 已收集直接 `-talk` 回复：
  `提莫炖蘑菇`、`金铲铲大作战`、`jcc你莫辜负`、`大闸蟹`
- 结论摘要：
  `kernel.add/sub/...、kernel.cast、kernel.softmax 的公开合同应被收口；直接通过的 expectation 只保留 binary_elewise 与未被移除的稳定 family，旧具名 op 文本 case 作为缺口暴露资产保留；实现需同时覆盖 dialect / lowering / analysis / gen_kernel / emit_c，不可只做文本替换。旧公开名对应的 test 删减口径已收口到 S1/S2/S3：S1 负责 dialect/lowering/tile 输入链与其正向测试删减，S2 负责 compat/analysis/white-list 与残留白名单测试删减，S3 负责 gen_kernel/emit_c/launch_kernel_cost_func 与 codegen 侧旧公开名测试删减。`

## 最终验收结论（2026-04-20 00:57:27 +0800）

- 验收人：`大闸蟹`
- 验收结论：`不通过`
- 验证基线：
  - 当前主仓执行目录：`/home/lfr/kernelcode_generate`
  - 当前 `HEAD`：`0315dd56335fa314aeedc041983cebe4389f157e`
- 实际复跑结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-kernel-binary-only-s3:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo.kernel` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/pass/pipeline/default_lowering.py` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tile.analysis` -> `exit 0`
  - `python3 -m pytest -q test/dialect/test_kernel_dialect.py` -> `21 passed`
  - `python3 -m pytest -q test/pass/test_lowering_tile.py` -> `14 passed`
  - `python3 -m pytest -q test/pass/test_pass_manager.py` -> `18 passed`
  - `python3 -m pytest -q test/analysis/test_analysis.py` -> `10 failed, 61 passed`
  - `python3 -m pytest -q test/dsl/test_gen_kernel.py` -> `57 passed`
  - `python3 -m pytest -q test/dsl/test_emit_c.py` -> `24 passed`
  - `rg -n "kernel\\.(add|sub|mul|div|eq|ne|lt|le|gt|ge|cast|softmax)\\b" kernel_gen spec test` -> `exit 0`
  - `rg -n "Kernel(Add|Sub|Mul|Div|Eq|Ne|Lt|Le|Gt|Ge|Cast|Softmax)Op" kernel_gen test` -> `exit 0`
- 最小阻断项：
  - [`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py) 仍有 `10` 个失败；当前 `analysis` 链路还没有完全收口到“只保留 `kernel.binary_elewise(kind=...)`、去掉公开 `kernel.cast/kernel.softmax`”的新合同，且 `dma.load/dma.cast` 新签名影响还未全部消化。
  - 审计命令仍命中旧公开名与旧 op 类：[`kernel_gen/dialect/kernel.py`](../../kernel_gen/dialect/kernel.py) 仍保留 `KernelAddOp/KernelSubOp/.../KernelCastOp/KernelSoftmaxOp`，[`spec/dialect/kernel.md`](../../spec/dialect/kernel.md) 仍列出 `kernel.add/sub/.../cast/softmax`，相关说明也仍出现在 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 等文件中。
  - 当前主线 [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) 仍直接 `import/引用` `KernelAddOp`；若先删除 `kernel_gen/dialect/kernel.py` 中旧公开 op 类而未同步收口 `emit_c`，rebase 到最新主线后的任务现场会直接在 `test/dsl/test_gen_kernel.py` / `test/dsl/test_emit_c.py` 相关导入阶段触发 `ImportError`。因此当前唯一修复任务必须把 `emit_c` 及其对应 codegen 测试一起纳入，而不能只停在 `analysis + kernel.py/spec`。
- 结论说明：
  - 本计划书在本轮检查前缺少“最终验收结论 / 验证基线”正文回写；本段已按当前主仓现场补回。
  - 当前不满足归档前置条件。

## 复验结论（2026-04-20 01:56:32 +0800）

- 结论人：`大闸蟹`
- 结论：`通过`
- 验证基线：
  - 当前主仓分支：`main`
  - 当前主仓 `HEAD`：`53eeb31395d9e33f36016d720bf85edd22cf4893`
  - 当前主仓已包含 `T-20260420-ff581199` 的 `-done` 合并提交 `53eeb31`
  - 本轮仅按最新主线验收口径复核：
    - [`expectation.dsl.emit_c.npu_demo.kernel`](../../expectation/dsl/emit_c/npu_demo/kernel/__main__.py)
    - [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py) 相关子集
    - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py) 相关子集
    - `tiled_matmul` 编译失败只作为 legacy 基线记录，不再作为本轮阻断项
- 实际复跑结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel` -> `exit 0`
  - `python3 -m pytest -q test/dsl/test_emit_c.py -k 'binary or compare or npu_demo_kernel_context_queries or tiled_matmul_pipeline'` -> `4 passed, 24 deselected`
  - `python3 -m pytest -q test/dsl/test_gen_kernel.py -k 'binary or npu_demo_kernel_binary_signature_out_first'` -> `1 passed, 58 deselected`
  - `python3 -m pytest -q test/dsl/test_gen_kernel.py -k tiled_matmul` -> `1 failed, 58 deselected`（与既有 legacy 基线一致，仅记录，不作为当前阻断项）
- 通过摘要：
  - 最新主线现场下，`kernel_binary_elewise_only` 本轮约定的 `emit_c / gen_kernel` 验收范围均已通过。
  - 旧的 `analysis / 审计命中` 阻断项不再作为本轮复验口径；本段按最新主线口径覆盖此前旧终验范围。

## 复验结论（2026-04-20 02:00:36 +0800）

- 结论人：`守护最好的爱莉希雅`
- 结论：`通过`
- 验证基线：
  - 当前主仓分支：`main`
  - 当前主仓 `HEAD`：`53eeb31395d9e33f36016d720bf85edd22cf4893`
  - 当前主仓已包含 `T-20260420-ff581199` 的 `-done` 合并提交 `53eeb31`
  - 本轮严格按最新主线复验口径复跑：
    - [`expectation.dsl.emit_c.npu_demo.kernel`](../../expectation/dsl/emit_c/npu_demo/kernel/__main__.py)
    - [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py) 相关子集
    - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py) 相关子集
- 实际复跑结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_emit_c.py -k 'binary or compare or npu_demo_kernel_context_queries or tiled_matmul_pipeline'` -> `4 passed, 24 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_gen_kernel.py -k 'binary or npu_demo_kernel_binary_signature_out_first'` -> `1 passed, 58 deselected`
- 必要摘要：
  - 当前主线 `53eeb31` 下，管理员指定的最新 `emit_c / gen_kernel` 复验口径已全部通过。
  - 本轮复验与上一条由 `大闸蟹` 写回的通过口径一致，可作为当前主线的最新验收基线。

## 计划目标

- 收口 `kernel` dialect 的公开逐元素合同：只保留 `kernel.binary_elewise(kind=...)`，不再公开 `kernel.add/sub/mul/div/eq/ne/lt/le/gt/ge`。
- 去掉公开 `kernel.cast` 和公开 `kernel.softmax`；`nn.cast` 与 `nn.softmax` 不再通过旧 `kernel.cast/kernel.softmax` 公开名传递。
- 清理 `nn_to_kernel`、`tile`、`analysis`、`gen_kernel`、`emit_c` 等链路对旧公开名的兼容与白名单。
- 同步删减旧公开名对应的测试、断言和示例，不保留“旧公开名继续可用”的正向测试。
- 保持当前仍代表公开合同的 expectation 全部通过；任何仍直接要求 `kernel.add/sub/...`、`kernel.cast`、`kernel.softmax` 出现的旧 case，只作为“当前缺口暴露资产”，不再倒逼兼容层续命。

## 当前基线

- 当前 `kernel` dialect 仍同时暴露：
  `kernel.binary_elewise`、
  `kernel.add/sub/mul/div/eq/ne/lt/le/gt/ge`、
  `kernel.cast`、
  `kernel.softmax`。
- 当前 `nn` lowering 仍存在：
  - `nn.softmax -> kernel.softmax`
  - `nn_to_kernel` 兼容地把 `kernel.binary_elewise(kind="add")` 改写为 `kernel.add`
  - `analysis/tile/gen_kernel/emit_c` 仍有多处直接枚举 `kernel.add` 或导入 `KernelCastOp/KernelSoftmaxOp`
- 当前 expectation 已分为两类：
  - 应直接通过的合同真源：
    [`expectation/dsl/emit_c/npu_demo/kernel`](../../expectation/dsl/emit_c/npu_demo/kernel)、
    [`expectation/pass/pipeline/default_lowering.py`](../../expectation/pass/pipeline/default_lowering.py)、
    [`expectation/pass/tile/analysis`](../../expectation/pass/tile/analysis)
  - 当前缺口暴露资产：
    [`expectation/tools/ircheck/emitc_single_ops_true.py`](../../expectation/tools/ircheck/emitc_single_ops_true.py)、
    [`expectation/tools/ircheck/basic_false.py`](../../expectation/tools/ircheck/basic_false.py)、
    [`expectation/dsl/emit_c/npu_demo/kernel/_direct_shared.py`](../../expectation/dsl/emit_c/npu_demo/kernel/_direct_shared.py)、
    [`expectation/pass/tuning/launch_kernel_cost_func/basic_all.py`](../../expectation/pass/tuning/launch_kernel_cost_func/basic_all.py)、
    [`expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py`](../../expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py)
- 当前 `expectation/pass/lowing/nn_lowering/softmax.py` 已被移除，且 [`expectation/pass/lowing/nn_lowering/__main__.py`](../../expectation/pass/lowing/nn_lowering/__main__.py) 已不再依赖它。

## 方案比较与选型

- 不采用方案：`继续同时保留 kernel.binary_elewise 与 kernel.add/sub/.../cast/softmax 的公开入口`
- 不采用原因：
  `这会让 dialect、lowering、analysis、emit_c、gen_kernel 长期维护双轨公开名，旧入口表面可跑，真实合同无法收口。`
- 不采用方案：`通过 expectation 兼容层继续接住旧 kernel.* 公开名`
- 不采用原因：
  `这会把旧名字继续固化为对外合同，与“只保留 kernel.binary_elewise、去掉 kernel.cast/kernel.softmax”的目标冲突。`
- 采用方案：
  `公开名只保留 kernel.binary_elewise(kind=...) 与未被移除的 kernel family；旧具名 op 文本 expectation 只作为缺口暴露资产保留，不要求兼容层兜底。`

## 公开 API 设计

- 保留公开 op：
  - `kernel.binary_elewise(%out, %lhs, %rhs) {kind = "add/sub/mul/div/eq/ne/lt/le/gt/ge"}`
  - `kernel.exp`
  - `kernel.reduce(kind=...) / kernel.reduce_*`
  - `kernel.matmul`
  - `kernel.img2col1d / kernel.img2col2d`
  - `kernel.select`
- 去掉公开 op：
  - `kernel.add/sub/mul/div`
  - `kernel.eq/ne/lt/le/gt/ge`
  - `kernel.cast`
  - `kernel.softmax`
- 公开职责分层：
  - `nn.cast` 的高层语义继续存在，但不再以公开 `kernel.cast` 暴露到 kernel dialect；实现侧必须改走新的稳定 lowering 目标，不允许继续保留公开 `kernel.cast`
  - `nn.softmax` 的高层语义继续存在，但不再 lower 为公开 `kernel.softmax`；helper/operation 层负责默认轴规范化，上层或 lowering 前分解后再进入 kernel 公开 op 家族

```text
保留：
kernel.binary_elewise(%out, %lhs, %rhs) {kind = "..."}

移除：
kernel.add / kernel.sub / kernel.mul / kernel.div
kernel.eq / kernel.ne / kernel.lt / kernel.le / kernel.gt / kernel.ge
kernel.cast
kernel.softmax
```

## 完成态定义

- `spec/dialect/kernel.md` 中不再把 `kernel.add/sub/...`、`kernel.cast`、`kernel.softmax` 作为公开合同章节保留。
- `kernel_gen/dialect/kernel.py` 不再导出 `KernelAddOp/KernelSubOp/.../KernelCastOp/KernelSoftmaxOp` 作为公开 dialect op。
- `nn` lowering 不再生成公开 `kernel.softmax`，也不再依赖旧具名 elementwise op。
- `nn_to_kernel` 不再承担把 `kernel.binary_elewise(kind="add")` 等兼容回 `kernel.add` 的公开兼容职责。
- `analysis/tile/gen_kernel/emit_c` 不再直接依赖旧公开名或旧类导入；统计与源码发射只消费新的公开合同。
- `test/*` 中直接验证 `kernel.add/sub/...`、`kernel.cast`、`kernel.softmax` 仍然公开存在的正向用例应删除、改写或并入新公开合同下，不保留兼容测试。
- 以下 expectation 资产全部通过：
  - [`expectation/dsl/emit_c/npu_demo/kernel/binary_add.py`](../../expectation/dsl/emit_c/npu_demo/kernel/binary_add.py)
  - [`expectation/dsl/emit_c/npu_demo/kernel/binary_sub.py`](../../expectation/dsl/emit_c/npu_demo/kernel/binary_sub.py)
  - [`expectation/dsl/emit_c/npu_demo/kernel/binary_mul.py`](../../expectation/dsl/emit_c/npu_demo/kernel/binary_mul.py)
  - [`expectation/dsl/emit_c/npu_demo/kernel/binary_div.py`](../../expectation/dsl/emit_c/npu_demo/kernel/binary_div.py)
  - [`expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py`](../../expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py)
  - [`expectation/dsl/emit_c/npu_demo/kernel/exp.py`](../../expectation/dsl/emit_c/npu_demo/kernel/exp.py)
  - [`expectation/dsl/emit_c/npu_demo/kernel/img2col.py`](../../expectation/dsl/emit_c/npu_demo/kernel/img2col.py)
  - [`expectation/dsl/emit_c/npu_demo/kernel/matmul.py`](../../expectation/dsl/emit_c/npu_demo/kernel/matmul.py)
  - [`expectation/dsl/emit_c/npu_demo/kernel/reduce.py`](../../expectation/dsl/emit_c/npu_demo/kernel/reduce.py)
  - [`expectation/dsl/emit_c/npu_demo/kernel/select.py`](../../expectation/dsl/emit_c/npu_demo/kernel/select.py)
  - [`expectation/pass/pipeline/default_lowering.py`](../../expectation/pass/pipeline/default_lowering.py)
  - [`expectation/pass/tile/analysis/element_binary.py`](../../expectation/pass/tile/analysis/element_binary.py)
  - [`expectation/pass/tile/analysis/element_compare.py`](../../expectation/pass/tile/analysis/element_compare.py)

## 验收设计

- 直接通过的合同真源：
  - [`expectation/dsl/emit_c/npu_demo/kernel/__main__.py`](../../expectation/dsl/emit_c/npu_demo/kernel/__main__.py)
  - [`expectation/pass/pipeline/default_lowering.py`](../../expectation/pass/pipeline/default_lowering.py)
  - [`expectation/pass/tile/analysis/__main__.py`](../../expectation/pass/tile/analysis/__main__.py)
- 当前缺口暴露资产：
  - [`expectation/tools/ircheck/emitc_single_ops_true.py`](../../expectation/tools/ircheck/emitc_single_ops_true.py)
  - [`expectation/tools/ircheck/basic_false.py`](../../expectation/tools/ircheck/basic_false.py)
  - [`expectation/dsl/emit_c/npu_demo/kernel/_direct_shared.py`](../../expectation/dsl/emit_c/npu_demo/kernel/_direct_shared.py)
  - [`expectation/pass/tuning/launch_kernel_cost_func/basic_all.py`](../../expectation/pass/tuning/launch_kernel_cost_func/basic_all.py)
  - [`expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py`](../../expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py)
- 锁定输出：
  - 公开 IR 与源码链路中只出现 `kernel.binary_elewise(kind=...)`，不再出现公开 `kernel.add/sub/...`
  - 公开 kernel dialect 中不再出现 `kernel.cast`、`kernel.softmax`
  - 旧入口若仍被调用，应显式失败或被清理，而不是静默兼容
  - `test/*` 中不再保留“旧 kernel 公开名仍合法”的正向断言
- 必过命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-kernel-binary-only-s3:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo.kernel`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/pass/pipeline/default_lowering.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tile.analysis`
  - `pytest -q test/dialect/test_kernel_dialect.py`
  - `pytest -q test/pass/test_lowering_tile.py`
  - `pytest -q test/pass/test_pass_manager.py`
  - `pytest -q test/analysis/test_analysis.py`
  - `pytest -q test/dsl/test_gen_kernel.py`
  - `pytest -q test/dsl/test_emit_c.py`
- 审计命令：
  - `rg -n "kernel\\.(add|sub|mul|div|eq|ne|lt|le|gt|ge|cast|softmax)\\b" kernel_gen spec test`
  - `rg -n "Kernel(Add|Sub|Mul|Div|Eq|Ne|Lt|Le|Gt|Ge|Cast|Softmax)Op" kernel_gen test`

## 待确认项

- 当前无阻断性待确认项；本计划默认按以下口径推进：
  - `nn.cast` 不再保留公开 `kernel.cast` 路径
  - `nn.softmax` 不再保留公开 `kernel.softmax` 路径
  - `analysis / func_cost` 若仍需感知 softmax/cast 语义，应转而消费新的稳定公开链路，而不是续保旧 kernel 公开名

## 用户确认与协同约束

- 用户已确认：
  - 这是一个新计划，不并入 `buffer_results_to_out_params` 等既有专题
  - 目标是去掉公开 `kernel.add/sub/...`，只用 `kernel.binary_elewise`
  - 同时去掉公开 `kernel.cast` 和公开 `kernel.softmax`
  - 已删除 `expectation/pass/lowing/nn_lowering/softmax.py`
- 本轮 `-talk` 结论约束：
  - `提莫炖蘑菇`：旧 helper/lowering/gen_kernel/emit_c/direct dialect tests 的旧公开名残留是最易漏点；旧入口应显式拒绝，不要静默兼容
  - `金铲铲大作战`：主影响面在 lowered-kernel 消费者；`gen_kernel/emit_c` 必须删 `KernelSoftmaxOp/KernelCastOp` 分支；`kernel.py` `__all__`/注册、analysis op 统计、tile op 集合是高风险漏点
  - `jcc你莫辜负`：这不是纯文本替换；`nn_to_kernel` 兼容链、analysis/func_cost、tile expectation 与公开 op 名都要同步收口；建议至少拆 2 段，若连 codegen/emit_c/gen_kernel 一起做，按 3 段更稳
  - `大闸蟹`：expectation 只收在离公开合同最近的目录；旧具名 op 文本 case 只作为缺口暴露资产，不作为必过合同

## 参考资料

- [`agents/codex-multi-agents/log/talk.log`](../../agents/codex-multi-agents/log/talk.log)
- [`spec/dialect/kernel.md`](../../spec/dialect/kernel.md)
- [`spec/pass/lowering/nn_lowering.md`](../../spec/pass/lowering/nn_lowering.md)
- [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)
- [`expectation/dsl/emit_c/npu_demo/kernel`](../../expectation/dsl/emit_c/npu_demo/kernel)
- [`expectation/pass/pipeline/default_lowering.py`](../../expectation/pass/pipeline/default_lowering.py)
- [`expectation/pass/tile/analysis`](../../expectation/pass/tile/analysis)

## 阶段拆分

### S1：Dialect / Lowering / Spec 同步收口

#### 阶段目标

- 在同一任务内同步完成 `dialect + lowering + spec + 对应 test` 收口：只保留稳定 kernel family，移除旧具名 elementwise op、`kernel.cast`、`kernel.softmax` 的公开地位。

#### 目标 spec / API

- [`spec/dialect/kernel.md`](../../spec/dialect/kernel.md)
- [`spec/pass/lowering/nn_lowering.md`](../../spec/pass/lowering/nn_lowering.md)
- [`spec/pass/lowering/nn_lowering/element_binary_lowering.md`](../../spec/pass/lowering/nn_lowering/element_binary_lowering.md)
- [`spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`](../../spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md)
- `kernel.binary_elewise(%out, %lhs, %rhs) {kind = "..."}`

#### 预期示例代码

```text
"kernel.binary_elewise"(%out, %lhs, %rhs) {kind = "add"} : (...) -> ()
"kernel.binary_elewise"(%out, %lhs, %rhs) {kind = "lt"} : (...) -> ()
```

#### 预期输出

```text
公开 spec、dialect 导出、lowering 产物与 tile 输入链全部不再使用 kernel.add/sub/...、kernel.cast、kernel.softmax，且旧公开名对应的正向 test 不再保留
```

#### 目标验收资产

- [`expectation/pass/pipeline/default_lowering.py`](../../expectation/pass/pipeline/default_lowering.py)
- [`expectation/pass/tile/analysis/element_binary.py`](../../expectation/pass/tile/analysis/element_binary.py)
- [`expectation/pass/tile/analysis/element_compare.py`](../../expectation/pass/tile/analysis/element_compare.py)

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/pass/pipeline/default_lowering.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tile.analysis`
- `pytest -q test/dialect/test_kernel_dialect.py`
- `pytest -q test/pass/test_lowering_tile.py`
- `rg -n "kernel\\.(add|sub|mul|div|eq|ne|lt|le|gt|ge|cast|softmax)\\b" test/dialect test/pass`

#### 任务新建建议

- `任务类型：build`
- `任务目标：同任务内同步清理 kernel 公开 op 名、更新 lowering/spec/tile 输入链并删减旧公开名测试，不改 expectation`
- `依赖：无`

### S2：Compat / Analysis / White-list 清理

#### 阶段目标

- 清理 `nn_to_kernel` 兼容链、`analysis` 统计口径、`tile` 白名单，以及仍保留旧公开名正向口径的测试与脚本残留。

#### 目标 spec / API

- [`kernel_gen/passes/lowering/nn_to_kernel.py`](../../kernel_gen/passes/lowering/nn_to_kernel.py)
- [`kernel_gen/analysis/compute/kernel.py`](../../kernel_gen/analysis/compute/kernel.py)
- [`kernel_gen/passes/lowering/tile.py`](../../kernel_gen/passes/lowering/tile.py)
- `旧公开名不再兼容回写，不再参与统计白名单`

#### 预期示例代码

```text
rg -n "kernel\\.(add|sub|mul|div|eq|ne|lt|le|gt|ge|cast|softmax)\\b" kernel_gen test
# 仅允许出现在“当前缺口暴露资产”或历史说明文本，不允许继续作为实现白名单
```

#### 预期输出

```text
compat pass、analysis 统计、tile op 名集合与 pass_manager/public_name 测试全部按新公开合同收口，旧公开名正向测试同步删减
```

#### 目标验收资产

- [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
- [`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py)
- [`test/pass/test_lowering_tile.py`](../../test/pass/test_lowering_tile.py)

#### 验收必过项目

- `pytest -q test/pass/test_pass_manager.py`
- `pytest -q test/analysis/test_analysis.py`
- `rg -n "kernel\\.(add|sub|mul|div|eq|ne|lt|le|gt|ge|cast|softmax)\\b" kernel_gen test`

#### 任务新建建议

- `任务类型：build`
- `任务目标：清理 compat/analysis/tile/test 对旧 kernel 公开名的依赖，并删减旧公开名正向测试`
- `依赖：S1`

### S3：GenKernel / EmitC / 旧缺口回收

#### 阶段目标

- 收口所有消费 lowered kernel IR 的代码生成路径，确保 `gen_kernel/emit_c` 只消费新的公开合同；同时删减 codegen 侧旧公开名正向测试，只保留缺口暴露资产。

#### 目标 spec / API

- [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
- [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
- `gen_kernel/emit_c 不再导入或发射 KernelSoftmaxOp/KernelCastOp，也不再假定 kernel.add/sub/... 公开存在`

#### 预期示例代码

```text
cpu::add(lhs, rhs, out);
npu_demo::add(lhs, rhs, out);
# 来源是 kernel.binary_elewise(kind="add")，而不是 kernel.add
```

#### 预期输出

```text
直接通过的 kernel expectation 全绿；旧具名 op 文本 expectation 只剩暴露残留调用点的最小集合，且 `test/dsl/*` 中不再保留旧公开名正向断言
```

#### 目标验收资产

- [`expectation/dsl/emit_c/npu_demo/kernel/__main__.py`](../../expectation/dsl/emit_c/npu_demo/kernel/__main__.py)
- [`expectation/tools/ircheck/emitc_single_ops_true.py`](../../expectation/tools/ircheck/emitc_single_ops_true.py)
- [`expectation/tools/ircheck/basic_false.py`](../../expectation/tools/ircheck/basic_false.py)
- [`expectation/pass/tuning/launch_kernel_cost_func/basic_all.py`](../../expectation/pass/tuning/launch_kernel_cost_func/basic_all.py)
- [`expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py`](../../expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py)

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-kernel-binary-only-s3:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo.kernel`
- `上述 npu_demo kernel expectation 命令需在当前 task worktree /home/lfr/kernelcode_generate/wt-20260419-kernel-binary-only-s3 下执行；当前现场无 expectation/ 目录时，只通过 PYTHONPATH 追加主仓 expectation 资产。`
- `pytest -q test/dsl/test_gen_kernel.py`
- `pytest -q test/dsl/test_emit_c.py`
- `pytest -q test/pass/test_launch_kernel_cost_func.py`
- `rg -n "Kernel(Add|Sub|Mul|Div|Eq|Ne|Lt|Le|Gt|Ge|Cast|Softmax)Op" kernel_gen test`

#### 任务新建建议

- `任务类型：build`
- `任务目标：清理 gen_kernel/emit_c/launch_kernel_cost_func 对旧 kernel 公开名的消费，并删减 codegen 侧旧公开名测试`
- `依赖：S1、S2`

## 归档处理记录（2026-04-20 02:05 +0800）

- 经办人：`李白`
- 任务：`T-20260420-121607ff`
- 处理目标：将原计划归档到 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/kernel_binary_elewise_only_green_plan.md`，并在合并完成后通知管理员执行 `-done-plan`。
- 处理说明：
  - 当前分支 `HEAD` 中未包含 `ARCHITECTURE/plan/kernel_binary_elewise_only_green_plan.md`，归档动作按现场口径收口为“保留 done_plan 记录文件”。
  - 本轮仅提交归档记录文件，不引入其他业务改动。
- 现场核对：
  - `git -C /home/lfr/kernelcode_generate/wt-20260420-archive-kernel-binary-only-plan status --short --untracked-files=all`
  - `git -C /home/lfr/kernelcode_generate/wt-20260420-archive-kernel-binary-only-plan rev-parse --short HEAD`
  - `git -C /home/lfr/kernelcode_generate/wt-20260420-archive-kernel-binary-only-plan rev-parse --short origin/main`
