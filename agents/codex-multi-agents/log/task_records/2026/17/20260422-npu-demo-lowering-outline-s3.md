时间：2026-04-22 11:41 +0800
经办人：朽木露琪亚
任务：T-20260422-2d1fa768
任务目标：在最新远端现场收口 npu_demo_lowering_outline_device_kernel_green_plan 的 S3，删除 npu_demo add/barrier 特化并让 gen_kernel 按通用 arch.launch module 生成 npu_demo launch wrapper，同时保留 helper func.func 的模块顺序输出
改动：更新 `kernel_gen/dsl/gen_kernel.py`，使 `npu_demo` module 发射改为按顶层出现顺序输出 body/wrapper/helper；将 launch body 从冻结 add+barrier 特化改为通用 lowered IR 发射，并补齐 `test.fake_symbol_value` 的 npu_demo 侧转译与 memory 结果绑定；同步更新 `spec/dsl/gen_kernel.md` 的 `npu_demo` 受控 module / helper 合同；同步更新 `test/dsl/test_gen_kernel.py` 的 helper fixture、wrapper/body 断言与当前源码形态
验证：`python3 -m pytest -q test/dsl/test_gen_kernel.py -k 'npu_demo and barrier'` -> `15 passed, 49 deselected, 1 warning`；`python3 -m pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_compiles_npu_demo_tiled_matmul_source` -> `1 passed, 63 deselected, 2 warnings`；`python3 -m pytest -q test/dsl/test_gen_kernel.py -k npu_demo` -> `24 passed, 40 deselected, 3 warnings`；`git diff --check` -> 通过
Diff 反推自测：改动文件为 `kernel_gen/dsl/gen_kernel.py`、`spec/dsl/gen_kernel.md`、`test/dsl/test_gen_kernel.py`；按实际 diff 反推执行的测试为 `test/dsl/test_gen_kernel.py -k 'npu_demo and barrier'`、`test_gen_kernel_compiles_npu_demo_tiled_matmul_source`、`-k npu_demo` 与 `git diff --check`，结果均通过；未执行 expectation，原因：expectation 仅作为合同验收资产单列，不替代对应测试
合同验收（如适用）：未执行；expectation 仅作为合同验收资产单列，本轮 build 不以 expectation 替代 pytest
结论：build 已完成，当前已进入 review 续接前状态

时间：2026-04-22 11:42 +0800
经办人：朽木露琪亚
任务：T-20260422-2d1fa768
任务目标：按流程推进 review 并回写记录
改动：已按 `TODO.md` 将本任务从 `build` 续接到 `review`，审查角色自动指派为 `提莫炖蘑菇`；当前 worktree 仅保留本次代码差异与任务记录文件，后续 review 需继续沿用同一 worktree 与同一记录链
验证：`rg -n "T-20260422-2d1fa768" /home/lfr/kernelcode_generate/TODO.md` -> 命中任务条目，类型已变更为 `review`、指派已更新为 `提莫炖蘑菇`、状态仍为 `进行中`；`git diff --check` -> 通过
Diff 反推自测：本轮仅补写任务流转记录并同步 `TODO.md`，未新增代码改动；由于属于状态推进动作，前序 build 记录已包含实际 diff 反推自测与对应 pytest 结果，本条不重复计入测试
合同验收（如适用）：未执行；expectation 仅作为合同验收资产单列，当前流转仅更新 build→review 记录
结论：build 阶段已完成并完成 review 流转，当前等待审查结果回填

时间：2026-04-22 12:15 +0800
经办人：提莫炖蘑菇
任务：T-20260422-2d1fa768
任务目标：按实际 diff 复审 npu_demo_lowering_outline_device_kernel_green_plan 的 S3 收口结果
改动：复核 `kernel_gen/dsl/gen_kernel.py`、`spec/dsl/gen_kernel.md`、`test/dsl/test_gen_kernel.py` 的本轮收口差异；确认 `npu_demo` launch body 不再依赖冻结 add+barrier 特化，允许 helper `func.func` 按 module 顶层出现顺序通过通用 `func.func` 发射路径输出，且 wrapper 仍稳定生成 `npu_demo::launch<1, 1, 1>(...)`
验证：`python3 -m pytest -q test/dsl/test_gen_kernel.py -k npu_demo` -> `24 passed, 40 deselected, 3 warnings`；`python3 -m pytest -q test/e2e/test_npu_demo_add_barrier.py` -> `1 passed, 1 warning`；`git diff --check` -> 通过
Diff 反推审查：本轮按实际 diff 反推验证的测试为 `test/dsl/test_gen_kernel.py -k npu_demo` 与 `test/e2e/test_npu_demo_add_barrier.py`，结果均通过；`expectation` 仅作为合同验收资产单列，不替代对应测试
合同验收（如适用）：未执行；`expectation` 仅作为合同验收资产单列，本轮 review 仍以 pytest 与 `git diff --check` 为准
结论：通过，审查记录已补齐 `Diff 反推审查`

时间：2026-04-22 12:16 +0800
经办人：李白
任务：T-20260422-2d1fa768
任务目标：按当前 worktree 收口 npu_demo_lowering outline S3 的 merge
改动：已将 `kernel_gen/dsl/gen_kernel.py`、`spec/dsl/gen_kernel.md`、`test/dsl/test_gen_kernel.py` 的 review 通过改动合并入当前主线；`npu_demo` launch body 已切到通用 lowered IR 发射路径，helper `func.func` 按 module 顶层出现顺序输出，测试断言与实现口径保持一致
验证：`python3 -m pytest -q /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s3/test/dsl/test_gen_kernel.py -k 'npu_demo and barrier'` -> `15 passed, 49 deselected, 1 warning`；`python3 -m pytest -q /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s3/test/dsl/test_gen_kernel.py -k test_gen_kernel_compiles_npu_demo_tiled_matmul_source` -> `1 passed, 63 deselected, 2 warnings`；`git diff --check` -> 通过
Diff 反推自测：改动文件为 `kernel_gen/dsl/gen_kernel.py`、`spec/dsl/gen_kernel.md`、`test/dsl/test_gen_kernel.py`；按实际 diff 反推执行的测试为 `test_gen_kernel.py -k 'npu_demo and barrier'`、`test_gen_kernel_compiles_npu_demo_tiled_matmul_source` 与 `git diff --check`，结果均通过；`expectation` 未参与本轮自测，仅作为合同验收资产单列
Diff 反推审查：保持 review 既有结论，确认 `npu_demo` helper `func.func` 继续通过通用函数发射路径输出且保持模块顺序，body / wrapper / helper 的源码形态与测试断言一致；`expectation` 仅作为合同验收资产单列，不替代对应测试
合同验收（如适用）：未执行；`expectation` 仅作为合同验收资产单列，本轮以 pytest 与 `git diff --check` 为准
结论：merge 已完成，记录已补齐
