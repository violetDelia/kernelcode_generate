# T-20260424-3c0b1a41

时间：2026-04-24 22:22 +0800
经办人：守护最好的爱莉希雅
任务：T-20260424-3c0b1a41 / main_npu_demo_pipeline_fold_cse 复验修复

## 任务信息

- 计划书：[`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md)
- worktree：`/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6`
- 任务类型：`build`
- 当前基线：`origin/main@7c63c3bc18b4d0d69dedc336e2cacdcfcb8bae99`

## 最小目标

- 收口 `spec/dialect/arch.md` 中剩余的旧直调用 `launch_kernel(callee, block, thread, subthread, shared_memory_size)` 公开口径。
- 收口 `kernel_gen/operation/arch.py` 中仍保留并公开描述的直调用 `launch_kernel(callee, block, thread, subthread, shared_memory_size, *args)` 兼容入口与对应说明。
- 只处理以上两处及其直接关联的实现 / spec / test。

## 执行要求

- 不得改动任何 `[immutable-file]`。
- 执行记录必须写真实自检。
- 执行记录必须写 `Diff 反推自测`。
- `expectation` 只单列为合同验收资产，不替代对应测试。

时间：2026-04-24 22:26 +0800
经办人：小李飞刀
任务：T-20260424-3c0b1a41
任务目标：收口 `spec/dialect/arch.md` 与 `kernel_gen/operation/arch.py` 中剩余的旧直调用 `launch_kernel` 公开口径，并同步最小关联测试到下标式公开入口。
执行前阅读记录：已读 [`TODO.md`](../../../../../TODO.md) 当前任务行、[`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 当前正文与终验补充、当前记录前序内容；已核对 [`spec/dialect/arch.md`](../../../../../spec/dialect/arch.md)、[`kernel_gen/operation/arch.py`](../../../../../kernel_gen/operation/arch.py)、[`spec/operation/arch.md`](../../../../../spec/operation/arch.md)、[`test/operation/test_operation_arch.py`](../../../../../test/operation/test_operation_arch.py) 的现有口径与测试分布。
最小功能闭环：`launch_kernel` 的 operation 公开入口只保留 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`；`spec/dialect/arch.md` 的 API 映射不再写旧直调用；`kernel_gen/operation/arch.py` 的 builder 直调用在调用边界直接报 `TypeError`；`test/operation/test_operation_arch.py` 的正向、参数校验、launch 上下文与 target 不支持路径全部改为下标式入口，直调用只保留为负例。
改动：
- 更新 [`spec/dialect/arch.md`](../../../../../spec/dialect/arch.md)：`operation API 映射` 中的 `launch_kernel` 行改为 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`。
- 更新 [`kernel_gen/operation/arch.py`](../../../../../kernel_gen/operation/arch.py)：将 `_resolve_launch_context_symbol(...)`、`_launch_context(...)` 与 `_LaunchKernelBuilder` 的说明统一到下标式公开入口；`_LaunchKernelBuilder.__call__` 不再兼容旧直调用，统一抛出提示使用 `launch_kernel[...]` 的 `TypeError`。
- 更新 [`test/operation/test_operation_arch.py`](../../../../../test/operation/test_operation_arch.py)：正向 case、非法 extent/callee、launch 上下文与 target 不支持路径切到 `launch_kernel[...]`；新增对旧直调用与错误下标字段个数的边界断言。
- 核对 [`spec/operation/arch.md`](../../../../../spec/operation/arch.md)：当前已与本轮实现一致，无需改写。
验证：
- `pytest -q /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6/test/operation/test_operation_arch.py -ra` -> `19 passed, 1 warning`
- `pytest -q /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6/test/dialect/test_arch_dialect.py -ra` -> `17 passed, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6/kernel_gen/operation/arch.py /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6/test/operation/test_operation_arch.py` -> 通过
- `rg -n "launch_kernel\\(callee, block, thread, subthread, shared_memory_size|兼容直调用" /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6/spec/dialect/arch.md /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6/kernel_gen/operation/arch.py` -> 无命中
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6 diff --check` -> 通过
Diff 反推自测：
- 实际改动文件：[`spec/dialect/arch.md`](../../../../../spec/dialect/arch.md)、[`kernel_gen/operation/arch.py`](../../../../../kernel_gen/operation/arch.py)、[`test/operation/test_operation_arch.py`](../../../../../test/operation/test_operation_arch.py)。
- 反推测试命令：`pytest -q test/operation/test_operation_arch.py -ra`、`pytest -q test/dialect/test_arch_dialect.py -ra`、`python3 -m py_compile kernel_gen/operation/arch.py test/operation/test_operation_arch.py`、`rg -n "launch_kernel\\(callee, block, thread, subthread, shared_memory_size|兼容直调用" spec/dialect/arch.md kernel_gen/operation/arch.py`。
- 结果：全部通过；当前目标文件内已无旧直调用公开口径文本，直调用行为只保留为负例测试。
合同验收：未执行；原因：本轮未触达当前保留的 expectation 合同入口，且任务边界只覆盖 operation/spec/test 文本与调用边界。
自检：已按任务边界只修改点名的 spec、实现与直接关联测试，未动 `[immutable-file]`、未顺手扩到 parser 或其他专题文件；实现没有保留双入口并行状态，公开调用形态、错误路径与测试说明已经一致；`TypeError` 文本会让旧直调用在调用边界直接失败，测试断言在入口回流时会立即暴露问题；本轮验证覆盖了 operation helper 主路径、非法输入、launch 上下文、target 不支持路径与 dialect 侧回归，未发现新的遗漏或已知逻辑问题。
结论：本轮 build 已完成，任务日志已写入当前 worktree；下一步按 `-next -auto -type review` 回流审查，并通知管理员。

时间：2026-04-24 22:28 CST
经办人：提莫炖蘑菇
任务：T-20260424-3c0b1a41
任务目标：复核 `spec/dialect/arch.md` 与 `kernel_gen/operation/arch.py` 剩余旧直调用 `launch_kernel` 公开口径是否已收口，并检查相关测试与日志。
执行前阅读记录：已读 [`TODO.md`](../../../../../TODO.md) 当前任务行、[`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 最新正文、全局完成态与验收设计、当前任务记录前序 build 内容；已核对 [`spec/dialect/arch.md`](../../../../../spec/dialect/arch.md)、[`kernel_gen/operation/arch.py`](../../../../../kernel_gen/operation/arch.py)、[`test/operation/test_operation_arch.py`](../../../../../test/operation/test_operation_arch.py)、[`test/dialect/test_arch_dialect.py`](../../../../../test/dialect/test_arch_dialect.py) 当前现场口径。
真实审查：
- [`spec/dialect/arch.md`](../../../../../spec/dialect/arch.md) 的 `operation API 映射` 已统一为 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`，没有保留旧直调用公开示例。
- [`kernel_gen/operation/arch.py`](../../../../../kernel_gen/operation/arch.py) 顶部示例、`_LaunchKernelInvocation` 说明、`_LaunchKernelBuilder` 说明已经统一到下标式公开入口；旧直调用 `launch_kernel(...)` 只保留为失败边界。
- [`kernel_gen/operation/arch.py`](../../../../../kernel_gen/operation/arch.py) 的 `_LaunchKernelBuilder.__call__` 现在直接抛出 `TypeError`，错误文本固定要求使用 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`。
- [`test/operation/test_operation_arch.py`](../../../../../test/operation/test_operation_arch.py) 正向与参数校验路径已切到下标式入口，旧直调用仅保留为负例；[`test/dialect/test_arch_dialect.py`](../../../../../test/dialect/test_arch_dialect.py) 继续覆盖 dialect 侧打印/解析与 verifier 口径，没有发现与本轮公开入口冲突的残留文本。
Diff 反推审查：
- 实际改动文件：[`spec/dialect/arch.md`](../../../../../spec/dialect/arch.md)、[`kernel_gen/operation/arch.py`](../../../../../kernel_gen/operation/arch.py)、[`test/operation/test_operation_arch.py`](../../../../../test/operation/test_operation_arch.py)。
- 反推测试命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6 pytest -q /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6/test/operation/test_operation_arch.py -ra`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6 pytest -q /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6/test/dialect/test_arch_dialect.py -ra`
  - `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6/kernel_gen/operation/arch.py /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6/test/operation/test_operation_arch.py`
  - `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6 diff --check`
- 结果：
  - `test/operation/test_operation_arch.py` -> `19 passed, 1 warning`
  - `test/dialect/test_arch_dialect.py` -> `17 passed, 1 warning`
  - `py_compile` -> 通过
  - `git diff --check` -> 通过
合同验收：未执行。本轮改动不涉及当前保留 expectation 入口，`expectation` 仅作为合同验收资产单列，不计入本轮 diff 反推测试。
自检：已按任务边界核对 spec、实现、operation 测试与 dialect 测试的一致性；当前现场没有继续把旧直调用当作公开 API 的文本或行为残留，错误边界和测试证据闭合。
可改进点：当前切片内未发现可直接执行的一线改进点；剩余 warning 为 xDSL 上游弃用告警，不属于本仓本轮 diff 可处理范围。
结论：通过；`spec/dialect/arch.md` 与 `kernel_gen/operation/arch.py` 的旧直调用 `launch_kernel` 公开口径已收口到下标式入口，相关测试与日志一致，可进入 `merge`。

---
时间：2026-04-25 00:04 +0800
经办人：李白
任务：T-20260424-3c0b1a41
任务目标：按当前 `TODO.md` 在指定 worktree 内完成 `spec/dialect/arch.md`、`kernel_gen/operation/arch.py` 与直接关联 pytest 的 merge 收口，并同步主仓状态。
执行前阅读记录：已读 [`TODO.md`](../../../../../TODO.md) 当前任务行；已读共享计划书 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 中 `T-20260424-3c0b1a41` 的阻断说明、`S3` / 全局完成态与验收设计；已回读本记录中的 build / review 结论，确认当前 residual diff 只涉及 [`spec/dialect/arch.md`](../../../../../wt-20260424-main-npu-demo-final-repair-s6/spec/dialect/arch.md)、[`kernel_gen/operation/arch.py`](../../../../../wt-20260424-main-npu-demo-final-repair-s6/kernel_gen/operation/arch.py) 与 [`test/operation/test_operation_arch.py`](../../../../../wt-20260424-main-npu-demo-final-repair-s6/test/operation/test_operation_arch.py)。
真实收口过程：
- 在任务 worktree 执行 `git fetch origin && git rebase --autostash origin/main`，结果：`HEAD is up to date.`，说明当前收口基线已对齐最新远端主线。
- 现场复核 `git status --short`，确认 tracked diff 仅为：
  - [`kernel_gen/operation/arch.py`](../../../../../wt-20260424-main-npu-demo-final-repair-s6/kernel_gen/operation/arch.py)
  - [`spec/dialect/arch.md`](../../../../../wt-20260424-main-npu-demo-final-repair-s6/spec/dialect/arch.md)
  - [`test/operation/test_operation_arch.py`](../../../../../wt-20260424-main-npu-demo-final-repair-s6/test/operation/test_operation_arch.py)
- merge 前按当前最终差异复跑直接关联验证，确认 review 通过项没有回退后再提交。
Diff 反推自测：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6 pytest -q /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6/test/operation/test_operation_arch.py /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6/test/dialect/test_arch_dialect.py -ra` -> `36 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6 python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6/kernel_gen/operation/arch.py /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6/test/operation/test_operation_arch.py` -> 通过
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6 diff --check` -> 通过
- `rg -n "launch_kernel\\(callee, block, thread, subthread, shared_memory_size|兼容直调用" /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6/spec/dialect/arch.md /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6/kernel_gen/operation/arch.py` -> 无命中，exit 1
合同验收（如适用）：
- 本轮不新增 expectation 合同验收；该任务收口范围只涉及 operation / dialect 公开口径和直接 pytest。
自检：
- 本轮 merge 没有扩大到无关 spec / parser / main.py 或 expectation 资产。
- 旧直调用 `launch_kernel(...)` 只保留为失败边界，不再作为公开口径出现在 `spec/dialect/arch.md` 或 `kernel_gen/operation/arch.py` 的公开说明中。
- 当前切片内未发现新的可直接执行阻断项。
结论：本任务已在指定 worktree 完成 merge 收口，可提交、推送并执行 `-done`。
