时间：2026-04-22 14:42
经办人：jcc你莫辜负
任务：T-20260422-bd36a572
任务目标：修复 npu_demo lowering outline 后 wrapper 先于 body 导致的 gen_kernel 编译失败，并补齐回归测试
改动：kernel_gen/dsl/gen_kernel.py 为 npu_demo launch module 增加 body 前置声明，并把 body 签名拼接收敛到统一 helper；test/dsl/test_gen_kernel.py 新增 outline -> gen_kernel -> compile 回归测试，覆盖 wrapper 先于 body 的真实顺序
验证：`pytest -q test/dsl/test_gen_kernel.py -k 'outlined_npu_demo_launch_module or compiles_npu_demo_launch_wrapper_and_barrier_body'` -> 2 passed, 63 deselected；`pytest -q test/tools/test_dsl_run.py -k 'npu_demo and (sub or mul or matmul)'` -> 3 passed, 16 deselected；`git diff --check` -> 通过
Diff 反推自测：改动文件为 `kernel_gen/dsl/gen_kernel.py`、`test/dsl/test_gen_kernel.py`；反推出的测试命令为 `pytest -q test/dsl/test_gen_kernel.py -k 'outlined_npu_demo_launch_module or compiles_npu_demo_launch_wrapper_and_barrier_body'`、`pytest -q test/tools/test_dsl_run.py -k 'npu_demo and (sub or mul or matmul)'`，并补跑 `git diff --check`；执行结果均通过；未执行项为 `expectation`，原因：`expectation` 只作为合同验收资产单列，不替代对应测试，本轮 build 按 Diff 反推自测收口
合同验收（如适用）：未执行；本轮未单列 expectation 合同验收
结论：通过，当前 build 已完成，可按 TODO.md 继续后续 review

时间：2026-04-22 14:43 +0800
经办人：提莫炖蘑菇
任务：T-20260422-bd36a572
任务目标：复核本轮 npu_demo lowering outline 修复与回归测试
改动：按实际 diff 复核 kernel_gen/dsl/gen_kernel.py 与 test/dsl/test_gen_kernel.py 的 npu_demo wrapper/body 顺序修复；确认新增 body 前置声明与统一签名 helper 仅解决 wrapper 先于 body 的可见性问题，没有改变公开调用合同
验证：`pytest -q test/dsl/test_gen_kernel.py -k 'outlined_npu_demo_launch_module or compiles_npu_demo_launch_wrapper_and_barrier_body'` -> 2 passed, 63 deselected；`pytest -q test/tools/test_dsl_run.py -k 'npu_demo and (sub or mul or matmul)'` -> 3 passed, 16 deselected；`git diff --check` -> 通过
Diff 反推审查：被审 diff 为 `kernel_gen/dsl/gen_kernel.py`、`test/dsl/test_gen_kernel.py`；复跑的实际命令为 `pytest -q test/dsl/test_gen_kernel.py -k 'outlined_npu_demo_launch_module or compiles_npu_demo_launch_wrapper_and_barrier_body'`、`pytest -q test/tools/test_dsl_run.py -k 'npu_demo and (sub or mul or matmul)'`，并补跑 `git diff --check`；三项结果均通过。`expectation` 仅作为合同验收资产单列，本轮未将其计入 diff 反推测试
合同验收（如适用）：未执行；本轮审查仅按 diff 反推测试与代码合同检查，不额外纳入 expectation 合同验收
结论：通过，body 前置声明已消除 outline 后 wrapper 先于 body 的编译失败风险，回归测试与源码顺序均已收口

时间：2026-04-22 14:44 +0800
经办人：李白
任务：T-20260422-bd36a572
任务目标：将 npu_demo lowering outline 修复与回归测试收口并合并到主线
改动：将 `kernel_gen/dsl/gen_kernel.py` 的 body 前置声明与统一签名 helper、`test/dsl/test_gen_kernel.py` 的 outline 回归测试一并纳入主线；确认 wrapper 先于 body 的编译失败风险已被 body 声明覆盖，公开调用合同保持不变
验证：`cd /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-final-repair && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m pytest -q test/dsl/test_gen_kernel.py -k 'outlined_npu_demo_launch_module or compiles_npu_demo_launch_wrapper_and_barrier_body'` -> 2 passed, 63 deselected；`cd /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-final-repair && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m pytest -q test/tools/test_dsl_run.py -k 'npu_demo and (sub or mul or matmul)'` -> 3 passed, 16 deselected；`git diff --check` -> 通过
Diff 反推自测：按当前 diff 反推覆盖 `kernel_gen/dsl/gen_kernel.py` 与 `test/dsl/test_gen_kernel.py`；复跑的最小验证为 outline 回归测试与 `test/tools/test_dsl_run.py` 子集，均通过；`expectation` 仍只作为合同验收资产单列，不纳入 diff 反推测试
Diff 反推审查：按实际 diff 复核 `kernel_gen/dsl/gen_kernel.py`、`test/dsl/test_gen_kernel.py` 的 outline 后 wrapper/body 顺序修复，确认 body 前置声明与统一签名 helper 已消除可见性问题，未改变公开调用合同
合同验收（如适用）：未额外执行；本轮 merge 以 diff 反推测试和代码合同检查为准，`expectation` 仅作为合同验收资产单列
结论：merge 已完成，记录已更新，可执行 `-done`
