时间：
2026-04-06 11:35 +0800

经办人：
朽木露琪亚

任务：
T-20260406-857c057b
npu_demo_parallel_add_sync_green_plan-S5-实现/测试（计划书：ARCHITECTURE/plan/npu_demo_parallel_add_sync_green_plan.md#S5）

任务目标：
- 让 `launch<1, 4, 1>(..., ...)` 真实启动 4 线程并共享 barrier（禁止串行模拟）。
- `thread_id/thread_num/ctx.barrier` 校验按计划书收口：
  - `thread_id()` 每线程不同；
  - `thread_num()` 等于 launch thread 参数；
  - `ctx.barrier(visibility, scope)` 仅接受 `scope=BLOCK` 且 visibility 为 `{TSM, TLM}`。
- gate（最少）均 `exit=0`：
  - `pytest -q test/include/api/test_arch.py`
  - `pytest -q test/include/npu_demo/test_runtime_launch.py`
  - `pytest -q test/dsl/test_gen_kernel.py -k 'npu_demo and barrier'`

改动：
- 新增测试 `test/include/npu_demo/test_runtime_launch.py`：
  - 通过编译+运行 C++ 片段锁定 `npu_demo::launch<1, 4, 1>` 必须真实启动 4 个线程；
  - 在 body 内使用 `KernelContext::barrier(...)` 验证 barrier 为同一次 launch 共享对象且能真实汇合（避免串行模拟或每线程私有 barrier）。
  - 为规避环境偶发 `ld` SIGSEGV（链接器崩溃）导致用例不稳定，`g++` 编译步骤增加最多 3 次重试（仅对 `ld terminated with signal` / `SIGSEGV` / `Segmentation fault` 触发重试）。

结论：
- 新增 runtime launch gate 证据后，可复现证明 `launch<1,4,1>` 为真实并行线程启动，且 barrier 在同一 launch 范围内共享并生效。

证据：
- 变更文件（git diff --name-only）：
  - （空；本任务变更包含新增文件/未纳入 diff 输出）
- 文件存在性：
  - `ls -l test/include/npu_demo/test_runtime_launch.py agents/codex-multi-agents/log/task_records/2026/15/20260406-npu-demo-sync-s5.md`
  - 输出：
    - `-rw-r--r-- 1 lfr lfr 1327 Apr  6 11:36 agents/codex-multi-agents/log/task_records/2026/15/20260406-npu-demo-sync-s5.md`
    - `-rw-r--r-- 1 lfr lfr 6900 Apr  6 11:38 test/include/npu_demo/test_runtime_launch.py`
- gate（均 exit=0）：
  - `pytest -q test/include/api/test_arch.py`
    - `3 passed`
  - `pytest -q test/include/npu_demo/test_runtime_launch.py`
    - `1 passed`
  - `pytest -q test/dsl/test_gen_kernel.py -k 'npu_demo and barrier'`
    - `12 passed, 41 deselected`

更新时间：
2026-04-06 11:41 +0800
时间：2026-04-06 12:18:30 +0800
经办人：提莫炖蘑菇
任务：T-20260406-579c4fd4（npu_demo_parallel_add_sync_green_plan#S5-审查）
任务目标：从严复核 launch<1,4,1> 真实 4 线程+共享 barrier、thread_id/thread_num/ctx.barrier 口径是否符合计划书；核对 C++ 运行证据与 ld SIGSEGV 重试不掩盖逻辑错误；检查新增文件纳入变更集风险；复跑 gate 并记录证据。
改动：未改代码；仅复跑 gate、核对 spec/实现/测试与 diff。
结论：需修改（证据缺口：无法确认是否存在未追踪新增文件；按审查规范不通过）。
问题清单：
- P1｜变更集风险：git diff --name-only/--cached 为空，但受“禁止 git status”限制，无法确认是否存在未追踪新增文件；与任务强调“新增文件纳入变更集风险”冲突，证据不足。建议由允许执行 git 的角色补充 git status/ls-files 证据并清理/纳入新增文件（如有）。
风险：
- 合并漏文件风险：若存在未追踪新增文件，将导致实现/测试不完整或运行时行为与记录不一致。
验证命令：
- PYTHONPATH=. pytest -q test/include/api/test_arch.py
- PYTHONPATH=. pytest -q test/include/npu_demo/test_runtime_launch.py
- PYTHONPATH=. pytest -q test/dsl/test_gen_kernel.py -k 'npu_demo and barrier'
- git diff --name-only
- git diff --name-only --cached
关键输出：
- test/include/api/test_arch.py：3 passed in 0.49s
- test/include/npu_demo/test_runtime_launch.py：1 passed in 0.47s
- test/dsl/test_gen_kernel.py -k 'npu_demo and barrier'：12 passed, 41 deselected in 0.54s
- git diff --name-only：空
- git diff --name-only --cached：空
读取清单与核对结论：
- include/npu_demo/Arch.h：launch 使用 std::thread 真实并发，所有线程共享 LaunchBarrierState；KernelContext 的 thread_id/thread_num 与 launch extent 一致；barrier 需 BLOCK + {TSM,TLM} 并共享状态。
- include/npu_demo/npu_demo.h：单入口 include 聚合 API 与后端实现，满足 spec 约束。
- spec/include/npu_demo/npu_demo.md：P0 子集与实现一致；launch 必须真实同步不允许串行模拟；barrier 共享对象要求与实现一致。
- test/include/npu_demo/test_runtime_launch.py：编译+运行用例验证线程/共享 barrier；ld SIGSEGV 重试仅限编译阶段，未掩盖运行时逻辑失败。
漏洞排查结果：
- 输入校验绕过：实现对 launch extent / barrier 参数做显式校验，未见绕过。
- 类型/形状绕过：KernelContext/barrier 参数类型受编译期约束，未见绕过。
- 边界越界：thread_id 范围由 launch 循环控制，未见越界。
- 错误处理缺失：非法 barrier/extent 返回 error 或抛异常，未见静默降级。
- 状态污染：barrier_state_ 仅 per-launch 共享，未见跨 launch 污染证据。
- 资源释放问题：std::thread join + shared_ptr 管理，未见泄漏证据。
改进建议：
- 必须补充“新增文件纳入变更集”的可复现证据（允许角色执行 git status/ls-files 或由管理员确认），否则存在合并漏文件风险。
下一步建议：
- 派生修复任务：由允许执行 git 的角色核对并补充“未追踪新增文件”证据，若存在则纳入变更集并回写记录；完成后再复审。

时间：2026-04-06 12:55:00 +0800
经办人：李白
任务：T-20260406-18569260（npu_demo_parallel_add_sync S5 证据补齐：新增文件追踪证明）
任务目标：补齐 git 证据以确认是否存在未追踪新增文件；若存在则纳入变更集并记录处理结果。
结论：
- 发现存在 2 个未追踪新增文件（记录文件 + 新增测试文件）。
- 已将上述新增文件纳入变更集（已 `git add`），当前 worktree 无未追踪新增文件残留。

证据（补齐）：
- 命令：`git status --porcelain`
  - 输出（add 前）：
    - `?? agents/codex-multi-agents/log/task_records/2026/15/20260406-npu-demo-sync-s5.md`
    - `?? test/include/npu_demo/test_runtime_launch.py`
- 命令：`git ls-files --others --exclude-standard`
  - 输出（add 前）：
    - `agents/codex-multi-agents/log/task_records/2026/15/20260406-npu-demo-sync-s5.md`
    - `test/include/npu_demo/test_runtime_launch.py`
- 处理：`git add agents/codex-multi-agents/log/task_records/2026/15/20260406-npu-demo-sync-s5.md test/include/npu_demo/test_runtime_launch.py`
- 命令：`git status --porcelain`
  - 输出（add 后）：
    - `A  agents/codex-multi-agents/log/task_records/2026/15/20260406-npu-demo-sync-s5.md`
    - `A  test/include/npu_demo/test_runtime_launch.py`
- 命令：`git ls-files --others --exclude-standard`
  - 输出（add 后）：（空）
- 命令：`git diff --name-only --cached`
  - 输出：
    - `agents/codex-multi-agents/log/task_records/2026/15/20260406-npu-demo-sync-s5.md`
    - `test/include/npu_demo/test_runtime_launch.py`
