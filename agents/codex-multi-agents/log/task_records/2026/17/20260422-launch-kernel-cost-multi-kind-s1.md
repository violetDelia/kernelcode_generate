时间：2026-04-23 10:09 CST
经办人：金铲铲大作战
任务：T-20260423-9c23217c
任务目标：按最新 spec 实现 launch-kernel-cost-func 多 cost_kind 合同并补齐验收资产
执行前阅读记录：
- 已读 `TODO.md` 当前任务行，确认 worktree、计划书、任务链记录与当前状态均指向本轮 build。
- 已读 `ARCHITECTURE/plan/launch_kernel_cost_func_multi_kind_green_plan.md` 的 S1 正文、全局完成态 / 验收设计，以及 `T-20260422-f94ed233` 的前序 spec / build / review 记录。
- 已只读核对 worktree 内的 `spec/pass/tuning/launch_kernel_cost_func.md`、`spec/dialect/tuner.md`、`spec/pass/registry.md`，确认公开合同已收口到 `compute|memory|kind2|kind3` 的多 kind 列表语义。
- 已核对 expectation 合同资产目录 `expectation/pass/tuning/launch_kernel_cost_func/`，其中 `basic_all.py` 与 `invalid_kind.py` 为 `[immutable-file]`，仅作合同验收资产，不作为 diff 反推测试替代。
最小功能闭环：
- `launch-kernel-cost-func` 从单一 `cost_kind` 收口为有序多值字符串合同，pass / dialect / registry / spec / test 三处口径一致。
- `LaunchKernelCostFuncPass` 能按 `compute|memory|kind2|kind3` 生成 4 个 sibling cost function，且顺序与列表一致。
- `tuner.cost` verifier 与 registry 透传口径同步扩展到四种合法 kind，非法 / 空段 / 重复段必须稳定失败。
- expectation 仅作为合同验收资产单列，不能替代改动文件对应测试。
改动：
- 更新 [`kernel_gen/passes/tuning/launch_kernel_cost_func.py`](kernel_gen/passes/tuning/launch_kernel_cost_func.py)：
  - 新增 `_normalize_cost_kinds(...)`，支持多段 `cost_kind` 规整与校验。
  - 保留 `_normalize_cost_kind(...)` 兼容包装，公开属性 `cost_kind` 仍返回规范化字符串，内部另存 `cost_kinds`。
  - `run()` 改为对每个 device callee 逐 kind 生成 sibling cost function，并保持插入顺序稳定。
  - 同步稳定错误短语到四值集合。
- 更新 [`kernel_gen/dialect/tuner.py`](kernel_gen/dialect/tuner.py)：
  - `TunerCostOp.verify_` 扩展到 `compute / memory / kind2 / kind3`。
  - 保持 `tuner.cost` 的结果类型和公开 metadata 规则不变。
- 更新 [`spec/pass/tuning/launch_kernel_cost_func.md`](spec/pass/tuning/launch_kernel_cost_func.md)、[`spec/dialect/tuner.md`](spec/dialect/tuner.md)、[`spec/pass/registry.md`](spec/pass/registry.md)：
  - 收口公开合同为 `compute|memory|kind2|kind3`。
  - 补齐多 kind 示例、注册透传口径与验收资产链接。
- 更新 [`test/pass/test_launch_kernel_cost_func.py`](test/pass/test_launch_kernel_cost_func.py)、[`test/pass/test_pass_registry.py`](test/pass/test_pass_registry.py)、[`test/dialect/test_tuner_dialect.py`](test/dialect/test_tuner_dialect.py)：
  - 新增 multi-kind 顺序与计数回归。
  - 更新非法 kind 的稳定失败短语。
  - 补足 `tuner.cost` 四种合法 kind 的直测。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-launch-kernel-cost-multi-kind-s1:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260422-launch-kernel-cost-multi-kind-s1/test/pass/test_launch_kernel_cost_func.py /home/lfr/kernelcode_generate/wt-20260422-launch-kernel-cost-multi-kind-s1/test/pass/test_pass_registry.py -k 'launch_kernel_cost_func or pass_registry'` -> `45 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-launch-kernel-cost-multi-kind-s1:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260422-launch-kernel-cost-multi-kind-s1/test/dialect/test_tuner_dialect.py` -> `7 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-launch-kernel-cost-multi-kind-s1:/home/lfr/kernelcode_generate python3 -m expectation.pass.tuning.launch_kernel_cost_func` -> `[OK] launch-kernel-cost-func expectation passed`
- `rg -n "compute\\|memory\\|kind2\\|kind3|LaunchKernelCostFuncPass|tuner.cost cost_kind" spec/pass/tuning/launch_kernel_cost_func.md spec/dialect/tuner.md spec/pass/registry.md` -> 命中预期的四值合同与注册透传口径
- `git -C /home/lfr/kernelcode_generate/wt-20260422-launch-kernel-cost-multi-kind-s1 diff --check` -> 通过
Diff 反推自测：
- 本轮按实际 diff 反推的测试仅包含 `pytest` 与可执行 expectation 合同验收；未将 expectation 当作测试替代。
- 重点验证了多 kind 顺序、重复/空段/非法值拒绝、registry 透传、tuner verifier、以及 launch helper 在当前四字段 ABI 下的可执行性。
合同验收：
- `python3 -m expectation.pass.tuning.launch_kernel_cost_func` -> 通过（仅作合同验收资产单列）
- `expectation/pass/tuning/launch_kernel_cost_func/basic_all.py`
- `expectation/pass/tuning/launch_kernel_cost_func/multi_kind.py`
- `expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py`
- `expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py`
自检：
- 已读完整阶段与前序记录，未越权扩范围，闭环已完成，测试已按实际 diff 反推。
- API 边界已统一：pass 构造、registry 选项、dialect verifier、spec 文案对同一四值集合保持一致。
- 异常边界已收紧：非法值、空段、重复段都会稳定失败，错误短语可机械匹配。
- 兼容性已保留：单值与多值输入都按规范化字符串保存，旧公开属性名不需要调用方改造。
- 测试有效性已确认：多 kind 输出顺序、计数与错误路径都被回归锁住，后续若实现坏掉会直接失败。
结论：build 已完成，真实自检与 Diff 反推自测已写入记录；已执行 `-next -auto -type review`，当前任务进入 review。

时间：2026-04-23 10:12 CST
经办人：提莫炖蘑菇
任务：T-20260423-9c23217c
任务目标：复核 launch-kernel-cost-func 多 cost_kind 合同收口、真实自检与 Diff 反推自测结果
执行前阅读记录：
- 已读 `TODO.md` 当前任务行，确认 worktree、计划书、任务链记录与当前状态均指向本轮 review。
- 已读 `ARCHITECTURE/plan/launch_kernel_cost_func_multi_kind_green_plan.md` 的 S1 正文、全局完成态 / 验收设计，以及前序 build 记录，确认本轮目标是把 `compute|memory|kind2|kind3` 的公开合同、注册、dialect verifier 与 pytest 统一收口。
- 已只读核对 worktree 内的 [`kernel_gen/passes/tuning/launch_kernel_cost_func.py`](../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)、[`kernel_gen/dialect/tuner.py`](../../../../kernel_gen/dialect/tuner.py)、[`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../spec/pass/tuning/launch_kernel_cost_func.md)、[`spec/dialect/tuner.md`](../../../../spec/dialect/tuner.md)、[`spec/pass/registry.md`](../../../../spec/pass/registry.md)，以及对应 `test/` 与 expectation 合同资产目录。
- 已核对 expectation 合同资产 `expectation/pass/tuning/launch_kernel_cost_func/`，其中 [`basic_all.py`](../../../../expectation/pass/tuning/launch_kernel_cost_func/basic_all.py)、[`multi_kind.py`](../../../../expectation/pass/tuning/launch_kernel_cost_func/multi_kind.py)、[`shared_callee_once.py`](../../../../expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py)、[`invalid_kind.py`](../../../../expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py) 仍为合同验收资产，不作为 diff 反推测试替代。
最小功能闭环：
- 本轮仅做 review，不修改实现代码；闭环是把 build 阶段产物与实际 diff 做机械对照，确认 `launch-kernel-cost-func` 的多 kind 合同、registry 透传、dialect verifier、spec 文案与 pytest 口径一致。
- 关键实现链路是：`LaunchKernelCostFuncPass(cost_kind="compute|memory|kind2|kind3")` -> registry -> `tuner.cost` verifier -> `symbol.add` 累计 -> sibling cost function 输出。
- 失败边界包括：非法 / 空段 / 重复 kind、callee 缺失、重名 cost function、metadata attr 冲突与非支持 op；这些边界必须由 pytest 直接锁住。
改动：
- 本轮未改业务代码，仅回填 review 结论与任务记录。
- 按实际 diff 复核 [`kernel_gen/passes/tuning/launch_kernel_cost_func.py`](../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py) 的 `_normalize_cost_kinds(...)`、`_normalize_cost_kind(...)` 兼容包装、`run()` 的 sibling cost function 生成顺序，以及 [`kernel_gen/dialect/tuner.py`](../../../../kernel_gen/dialect/tuner.py) 对 `compute / memory / kind2 / kind3` 的 verifier 收口。
- 按实际 diff 复核 [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../spec/pass/tuning/launch_kernel_cost_func.md)、[`spec/dialect/tuner.md`](../../../../spec/dialect/tuner.md)、[`spec/pass/registry.md`](../../../../spec/pass/registry.md) 与 [`test/pass/test_launch_kernel_cost_func.py`](../../../../test/pass/test_launch_kernel_cost_func.py)、[`test/pass/test_pass_registry.py`](../../../../test/pass/test_pass_registry.py)、[`test/dialect/test_tuner_dialect.py`](../../../../test/dialect/test_tuner_dialect.py) 的一致性。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-launch-kernel-cost-multi-kind-s1:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260422-launch-kernel-cost-multi-kind-s1/test/pass/test_launch_kernel_cost_func.py /home/lfr/kernelcode_generate/wt-20260422-launch-kernel-cost-multi-kind-s1/test/pass/test_pass_registry.py -k 'launch_kernel_cost_func or pass_registry'` -> `45 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-launch-kernel-cost-multi-kind-s1:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260422-launch-kernel-cost-multi-kind-s1/test/dialect/test_tuner_dialect.py` -> `7 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-launch-kernel-cost-multi-kind-s1:/home/lfr/kernelcode_generate:/home/lfr/kernelcode_generate/wt-20260422-launch-kernel-cost-multi-kind-s1 python3 -m expectation.pass.tuning.launch_kernel_cost_func` -> `[OK] launch-kernel-cost-func expectation passed`
- `git diff --check` -> 通过
Diff 反推审查：
- 已按实际 diff 逐项核对 `launch-kernel-cost-func` 的实现、dialect verifier、spec、registry 与测试文件，确认四 kind 合同统一收口，没有发现旧 helper / 旧路径残留回流到当前公开合同。
- `expectation` 仅作为合同验收资产单列，不计入本轮 diff 反推测试，也没有被当作 pytest 替代项。
- 未发现与 `[immutable-file] expectation/pass/tuning/launch_kernel_cost_func/basic_all.py`、[`invalid_kind.py`](../../../../expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py) 的合同/immutable 约束冲突；这些文件保持只读，未在本轮改动范围内。
合同验收（如适用）：
- `python3 -m expectation.pass.tuning.launch_kernel_cost_func` -> `[OK] launch-kernel-cost-func expectation passed`
- 仅作为合同验收资产单列，不计入本轮 Diff 反推审查的测试集合。
自检：
- 已读完整阶段、全局完成态 / 验收设计与前序记录；未越权改文件；闭环已完成；测试与审查均按实际 diff 反推；原问题已解决；要求已满足；无已知 bug / 逻辑问题 / 未覆盖边界 / 潜在漏洞。
- API 收口已统一：`LaunchKernelCostFuncPass`、registry 选项透传、`tuner.cost` verifier 和 spec 文案都围绕同一四值集合运行。
- 边界已机械可判：非法 / 空段 / 重复 kind、callee 缺失、重名 cost function、metadata 冲突与不支持 op 都能稳定失败。
- 可改进点：未发现额外改进点。
结论：通过；已执行 `Diff 反推审查`，review 结果与 build 阶段产物一致，未发现合同或 immutable 约束冲突；请管理员继续推进后续链路。

## 归并收口

- 时间：`2026-04-23 10:14:12 +0800`
- 经办人：`李白`
- 任务：`T-20260423-9c23217c（merge）`
- 已重新核对 `TODO.md`、`ARCHITECTURE/plan/launch_kernel_cost_func_multi_kind_green_plan.md` 的 S1 正文、全局完成态 / 验收设计，以及前序 build / review 记录。
- 本轮合并范围覆盖 `kernel_gen/passes/tuning/launch_kernel_cost_func.py`、`kernel_gen/dialect/tuner.py`、`spec/pass/tuning/launch_kernel_cost_func.md`、`spec/dialect/tuner.md`、`spec/pass/registry.md`、`test/dialect/test_tuner_dialect.py`、`test/pass/test_launch_kernel_cost_func.py`、`test/pass/test_pass_registry.py`。
- `expectation` 仍只作为合同验收资产单列，未纳入 diff-driven 测试。
- 结论：当前收口结果可以随本次 merge 进入主线。
