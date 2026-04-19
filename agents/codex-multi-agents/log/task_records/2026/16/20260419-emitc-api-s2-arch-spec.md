时间：2026-04-19 21:09 +0800
经办人：咯咯咯
任务：T-20260419-a928693d
任务目标：冻结 Arch 公共接口与 include/api vs include/npu_demo 分层
改动：更新 [`spec/include/api/Arch.md`](../../../../../../spec/include/api/Arch.md)，补齐 `KernelContext::thread_id()`、`KernelContext::thread_num()`、`KernelContext::barrier(visibility, scope)`、`KernelContext::get_dynamic_memory<Space, T>()` 的公开接口说明，并把“include/api 只定义接口与最小语义、include/npu_demo 承接 runtime 行为”的职责拆分写成明确边界；未修改实现、测试或 `expectation` 文件。
验证：`rg -n "launch<|KernelContext::thread_id|KernelContext::thread_num|KernelContext::barrier|get_dynamic_memory<|include/api 只定义接口与最小语义|include/npu_demo 承接 runtime 行为" spec/include/api/Arch.md` -> 命中计划书 S2 验收要求的关键字与分层短语；`git diff -- spec/include/api/Arch.md` -> 确认本轮只改 `spec/include/api/Arch.md`。未执行测试命令，原因：当前阶段仅收口 spec 文档。
结论：当前 S2 spec 已完成；下游 build 可按最新 Arch 公共接口和 include/api vs include/npu_demo 分层口径继续实现与补齐验收资产。

时间：2026-04-19 21:14
经办人：金铲铲大作战
任务：T-20260419-a928693d
任务目标：对齐 include/api/Arch.h 与公开分层
改动：更新 [`include/api/Arch.h`](../../../../../../include/api/Arch.h)，新增公开 `KernelContext` 接口声明，只暴露 `thread_id()`、`thread_num()`、`barrier(visibility, scope)` 与 `get_dynamic_memory<Space, T>()` 的最小接口面，并补上 `initializer_list` 依赖与对应中文说明；更新 [`test/include/api/test_arch.py`](../../../../../../test/include/api/test_arch.py)，新增 `_compile_only(...)` 辅助函数与 `test_include_api_arch_declares_public_kernel_context_surface`，同时把头文件文本校验扩展到 `KernelContext` 的公开声明。未修改 `include/npu_demo/Arch.h` 与当前 worktree 中已存在的 `spec/include/api/Arch.md` 改动。
验证：`python3 -m pytest -q test/include/api/test_arch.py` -> `5 passed`；`python3 -m pytest -q test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py` -> `14 passed`；`git diff --check -- include/api/Arch.h test/include/api/test_arch.py` -> 通过。
结论：当前 build 已完成；`include/api/Arch.h` 已与最新 Arch 公共接口 spec 对齐，并保持 include/api 只暴露接口面、include/npu_demo 继续承接 runtime 实现的分层。下一步可进入 review 复核公开分层与接口声明。

时间：2026-04-19 21:16 +0800
经办人：提莫炖蘑菇
任务：T-20260419-a928693d
任务目标：复核 include/api/Arch.h 的公开接口声明与分层是否对齐最新 Arch spec
改动：本轮仅做审查。复核 [`spec/include/api/Arch.md`](../../../../../../spec/include/api/Arch.md) 与 [`include/api/Arch.h`](../../../../../../include/api/Arch.h) 的公开 Arch 合同，确认 `BarrierVisibility`、`BarrierScope`、抽象 `KernelContext`、`thread_id()`、`thread_num()`、`barrier(visibility, scope)`、`get_dynamic_memory<Space, T>()` 与 `launch<block, thread, subthread>(callee, args...)` 的公开口径、职责拆分和中文说明已经一致；同时复核 [`test/include/api/test_arch.py`](../../../../../../test/include/api/test_arch.py) 新增的 compile-only 用例与头文件文本校验，确认其已覆盖 “include/api 仅暴露接口面、不引入后端实现细节” 的回归点。
验证：`python3 -m pytest -q test/include/api/test_arch.py` -> `5 passed`；`python3 -m pytest -q test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py` -> `14 passed`；`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s2-arch-spec diff --check -- include/api/Arch.h spec/include/api/Arch.md test/include/api/test_arch.py` -> 通过；行号核对：[`include/api/Arch.h`](../../../../../../include/api/Arch.h) 第 22-25 行已补 `initializer_list` 与公开依赖，第 91-162 行已声明抽象 `KernelContext` 与四个最小接口面；[`spec/include/api/Arch.md`](../../../../../../spec/include/api/Arch.md) 第 31-46 行已写明 include/api 与 include/npu_demo 的职责拆分，第 146-260 行已完整写实 `KernelContext` 及其成员合同；[`test/include/api/test_arch.py`](../../../../../../test/include/api/test_arch.py) 第 138-181 行新增 `_compile_only(...)`，第 277-359 行已补头文件文本校验与 compile-only 公开接口用例。
结论：审查通过。当前 `include/api/Arch.h` 的公开接口声明与分层已对齐最新 Arch spec，未发现新的阻断项，可进入 `merge`。

时间：2026-04-19 22:38 +0800
经办人：李白
任务：T-20260419-a928693d
任务目标：在 `wt-20260419-emitc-api-s2-arch-spec` 内按当前 merge 边界合并已通过审查的 Arch 公共接口声明与分层收口改动
改动：已完成合并前核对。当前待合入文件为 [`include/api/Arch.h`](../../../../../../include/api/Arch.h)、[`spec/include/api/Arch.md`](../../../../../../spec/include/api/Arch.md)、[`test/include/api/test_arch.py`](../../../../../../test/include/api/test_arch.py) 与当前记录文件；未发现 `expectation/` 路径改动，也未混入额外无关现场文件。
验证：`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s2-arch-spec status --short --branch` -> 仅命中上述 include、spec、测试与记录文件；`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s2-arch-spec rev-parse --short HEAD` -> `39dd69f`；`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s2-arch-spec rev-parse --short origin/main` -> `2d346c5`
结论：已完成合并前核对；下一步在当前 `worktree` 内先对齐最新主线，再提交上述允许范围内的改动，向远端主分支发起一次推送，并执行 `-done` 后回报管理员。
