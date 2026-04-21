时间：2026-04-22 02:48
经办人：金铲铲大作战
任务：T-20260422-2185fc33
任务目标：补齐 npu_demo target 文件化加载、registry 1/1/1 查询结果与 i64 DSL/MLIR 前置链路
改动：
- 新增 [kernel_gen/target/targets/npu_demo.txt](kernel_gen/target/targets/npu_demo.txt)，把 npu_demo 的能力矩阵与硬件值收口到文件化目标源，当前 `block_num/thread_num/subthread_num = 1/1/1`。
- 更新 [kernel_gen/target/registry.py](kernel_gen/target/registry.py)，让 import 时直接从 `kernel_gen/target/targets/npu_demo.txt` 解析并注册 npu_demo，且支持默认目录重复加载的幂等回放。
- 更新 [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)，补齐 `NumericType.Int64 <-> i64` 的双向映射。
- 更新 [spec/target/registry.md](spec/target/registry.md)、[spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)、[spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)，同步文件化 npu_demo 数据源口径与 i64 前置链路说明。
- 更新 [test/target/test_target_registry.py](test/target/test_target_registry.py)、[test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)、[test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)，补齐 npu_demo.txt 载入、registry 1/1/1 断言与 i64 DSL/MLIR 回归测试。
验证：
- 初跑 `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1:/home/lfr/kernelcode_generate PYTHONDONTWRITEBYTECODE=1 pytest -q /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1/test/target/test_target_registry.py /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1/test/dsl/test_emit_mlir.py /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1/test/dsl/test_mlir_gen.py` -> `245 passed, 1 failed`，失败点为 `test/dsl/test_mlir_gen.py::test_expectation_dsl_mlir_gen_root_entry_runs_in_fresh_process` 的既有 expectation 子进程 `ModuleNotFoundError`，与本轮 diff 无关。
- 按 `Diff 反推自测` 收窄后分别复跑：
- `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1:/home/lfr/kernelcode_generate PYTHONDONTWRITEBYTECODE=1 pytest -q /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1/test/target/test_target_registry.py -k 'test_target_registry_npu_demo_template or test_target_registry_npu_demo_analysis_defaults or test_target_registry_npu_demo_rejects_unsupported_ops or test_target_registry_npu_demo_supports_launch_and_barrier_caps or test_target_registry_loads_default_cpu_directory'` -> `5 passed, 14 deselected`
  - `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1:/home/lfr/kernelcode_generate PYTHONDONTWRITEBYTECODE=1 pytest -q /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1/test/dsl/test_emit_mlir.py -k 'test_emit_mlir_maps_int64_memory_dtype_to_i64'` -> `1 passed, 72 deselected`
  - `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1:/home/lfr/kernelcode_generate PYTHONDONTWRITEBYTECODE=1 pytest -q /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1/test/dsl/test_mlir_gen.py -k 'test_build_func_op_supports_int64_tensor_signature'` -> `1 passed, 153 deselected`
- `git -C /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1 diff --check` -> 通过
Diff 反推自测：
- 改动文件：`kernel_gen/target/registry.py`、`kernel_gen/target/targets/npu_demo.txt`、`kernel_gen/dsl/mlir_gen/emit/core.py`、`spec/target/registry.md`、`spec/dsl/emit_mlir.md`、`spec/dsl/mlir_gen.md`、`test/target/test_target_registry.py`、`test/dsl/test_emit_mlir.py`、`test/dsl/test_mlir_gen.py`。
- 反推测试命令：以 `pytest` 为主的三组定向回归，分别覆盖 target registry、emit_mlir i64 双向映射、build_func_op i64 tensor 签名。
- 结果：定向 diff 反推测试全部通过；`expectation` 未纳入本轮 diff 反推测试，仅保留为合同验收资产单列。
合同验收（如适用）：
- 未执行。原因：本轮为 build 阶段的 diff 反推自测收口，expectation 仅作为合同验收资产单列，不替代改动文件对应测试。
结论：当前 build 已完成，npu_demo target 已改为从 `kernel_gen/target/targets/npu_demo.txt` 加载，registry 查询值收口为 `1/1/1`，i64 DSL/MLIR 前置链路已补齐；下一步按 TODO 流转 review。

时间：2026-04-22 02:50
经办人：提莫炖蘑菇
任务：T-20260422-2185fc33
任务目标：复核 npu_demo target 文件化加载、registry 1/1/1 查询结果与 i64 DSL/MLIR 前置链路
Diff 反推审查：已按实际 diff 复核 `kernel_gen/target/registry.py`、`kernel_gen/target/targets/npu_demo.txt`、`kernel_gen/dsl/mlir_gen/emit/core.py`、`spec/target/registry.md`、`spec/dsl/emit_mlir.md`、`spec/dsl/mlir_gen.md`、`test/target/test_target_registry.py`、`test/dsl/test_emit_mlir.py` 与 `test/dsl/test_mlir_gen.py`；build 记录已包含 `Diff 反推自测`，本轮 review 仅在此基础上做合同与回归复核，expectation 仅作为合同验收资产单列，不替代对应 pytest。
验证：`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1:/home/lfr/kernelcode_generate PYTHONDONTWRITEBYTECODE=1 pytest -q /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1/test/target/test_target_registry.py -k 'test_target_registry_npu_demo_template or test_target_registry_npu_demo_analysis_defaults or test_target_registry_npu_demo_rejects_unsupported_ops or test_target_registry_npu_demo_supports_launch_and_barrier_caps or test_target_registry_loads_default_cpu_directory'` -> `5 passed, 14 deselected`；`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1:/home/lfr/kernelcode_generate PYTHONDONTWRITEBYTECODE=1 pytest -q /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1/test/dsl/test_emit_mlir.py -k 'test_emit_mlir_maps_int64_memory_dtype_to_i64'` -> `1 passed, 72 deselected`；`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1:/home/lfr/kernelcode_generate PYTHONDONTWRITEBYTECODE=1 pytest -q /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1/test/dsl/test_mlir_gen.py -k 'test_build_func_op_supports_int64_tensor_signature'` -> `1 passed, 153 deselected`；`git -C /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1 diff --check` -> 通过。
说明：曾对三文件做过一轮更宽的 `pytest -q test/target/test_target_registry.py test/dsl/test_emit_mlir.py test/dsl/test_mlir_gen.py`，唯一失败点为 `test_expectation_dsl_mlir_gen_root_entry_runs_in_fresh_process` 的既有 expectation 子进程 `ModuleNotFoundError: No module named 'expectation.dsl'`，与本轮 diff 无关，不作为本次 review 阻断。
结论：通过

时间：2026-04-22 03:01 CST
经办人：李白
任务：T-20260422-2185fc33
任务目标：完成 merge 收口与同步确认
改动：当前 worktree 仅保留本任务记录文件、`kernel_gen/target/targets/npu_demo.txt` 及已修改的 target/spec/test 文件；本轮在已通过 `Diff 反推自测` / `Diff 反推审查` 的结论基础上补写 merge 收口记录，不扩大修改面
验证：`timeout 60 git -C /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1 fetch origin` -> 通过；`git -C /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1 status --short --untracked-files=all` -> 仅当前任务相关文件待提交；`git -C /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s1 diff --check` -> 通过
Diff 反推自测 / Diff 反推审查：沿用已写入 build / review 记录中的结论；本轮 merge 不新增测试，只收口提交与同步
合同验收（如适用）：expectation 仅作为合同验收资产单列，本轮不新增 expectation 验收
结论：merge 收口已完成，待提交并推送
