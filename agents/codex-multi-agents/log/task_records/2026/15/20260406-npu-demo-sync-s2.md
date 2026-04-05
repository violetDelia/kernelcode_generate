时间：2026-04-06 05:10 +0800
经办人：睡觉小分队
任务：T-20260406-41139920（npu_demo_parallel_add_sync_green_plan-S2-spec）
任务目标：按计划书 S2 冻结 include/api/Arch 与 include/npu_demo/Arch 的职责边界、KernelContext 运行时视图、barrier(visibility, scope)、thread_num()/block_num() 返回本次 launch 值，以及 target.registry 对 arch.launch/arch.barrier 与 thread_num=8 能力上限的公开合同；仅修改 spec。
改动：
- 新增 `spec/include/api/Arch.md`，冻结 include/api 层公共源码接口：`launch<block, thread, subthread>(callee, args...)`、`BarrierScope::{BLOCK, THREAD}`、`barrier(visibility, scope)`；明确 `callee` 是函数对象，禁止字符串 callee，且 include/api 只声明公共接口，不承接后端 runtime/barrier 实现。
- 更新 `spec/include/npu_demo/npu_demo.md`，冻结 `npu_demo::launch<block, thread, subthread>(callee, args...)` 与 `KernelContext` 运行时视图：`block_num()/thread_num()/subthread_num()` 返回当前 launch extent，`block_id()/thread_id()/subthread_id()` 为当前执行索引；P0 子集固定为 `block=1`、`subthread=1`、`2 <= thread <= 8`。
- 更新 `spec/include/npu_demo/npu_demo.md` 中 `KernelContext::barrier(visibility, scope)`：P0 仅支持 `visibility={MemorySpace::TSM, MemorySpace::TLM}` 且 `scope=BarrierScope::BLOCK`；空 visibility、重复项、混入 `SM/LM/GM`、`scope=THREAD` 等均需显式失败，禁止 silent fallback。
- 更新 `spec/target/registry.md`，将 `npu_demo` 固定模板中的 arch 能力矩阵收口为支持 `arch.launch` 与 `arch.barrier`，并明确 `thread_num=8`、`block_num=1`、`subthread_num=1` 是 capability upper bound，不等于 launched body 中当前运行时值；旧名 `arch.launch_kernel` 不再属于已启用矩阵。
- 反证点：1) 不允许 `include/api/Arch.h` 混入 `npu_demo` 私有线程/barrier 实现；2) 不允许 `KernelContext` 继续返回与 launch 无关的固定常量（如 `thread_num=8`、`thread_id=3`）；3) 不允许无参 `barrier()` 或字符串 callee；4) registry 不允许把未带 `arch.` 前缀的 `launch`/`barrier` 当作稳定输入域。
- gate 证据：
  - `cd /home/lfr/kernelcode_generate/wt-20260406-npu-demo-sync-s2 && pytest -q test/include/api/test_arch.py` -> exit=4，`ERROR: file or directory not found: test/include/api/test_arch.py`。
  - `cd /home/lfr/kernelcode_generate/wt-20260406-npu-demo-sync-s2 && pytest -q test/include/npu_demo/test_kernel_context.py -k "runtime or barrier"` -> exit=5，`10 deselected in 0.01s`，说明当前测试尚未补到 runtime/barrier 命名与场景。
  - `cd /home/lfr/kernelcode_generate/wt-20260406-npu-demo-sync-s2 && pytest -q test/target/test_target_registry.py -k "npu_demo and launch"` -> exit=5，`18 deselected in 0.39s`，说明当前 target registry 测试尚未覆盖 `arch.launch/arch.barrier` 的新口径。
结论：S2 spec 收口已完成，当前 spec 已给出 include/api、npu_demo runtime、target.registry 的唯一稳定合同；gate 未绿的原因是实现/补测尚未跟进（缺 `test/include/api/test_arch.py`，其余两条命令无匹配用例），不属于本次 spec-only 改动范围。建议后续唯一任务进入“实现+补测”，允许同步 `include/api/Arch.h`、`include/npu_demo/Arch.h`、`include/npu_demo/npu_demo.h`、`kernel_gen/target/registry.py` 及三处测试文件，并以本记录中的反证点为验收基线。

时间：2026-04-06 06:22 +0800
经办人：小李飞刀
任务：T-20260406-d234a944（npu_demo_parallel_add_sync_green_plan-S2-实现+补测）
任务目标：基于已冻结的 S2 spec 落地 `include/api/Arch.h`、`include/npu_demo/Arch.h`、`include/npu_demo/npu_demo.h`、`kernel_gen/target/registry.py` 与对应测试，使 `KernelContext` 运行时视图、`barrier(visibility, scope)`、`arch.launch/arch.barrier` registry 合同与 `thread_num=8` 能力上限全部可验证，并让三条 gate 均 `exit=0`。
改动：
- 新增 `include/api/Arch.h`，仅声明公共 `BarrierScope` 与 `launch<block, thread, subthread>(callee, args...)` 接口，保持 include/api 层不混入后端 runtime 实现，并用静态断言拒绝字符串 callee。
- 新增 `include/npu_demo/Arch.h`，实现 `npu_demo::KernelContext` 运行时视图、`barrier(visibility, scope)` 校验与 `launch<1, thread, 1>` 的 P0 子集执行路径；`block_num()/thread_num()/subthread_num()` 返回本次 launch extent，`thread` 仅接受 `2..8` 且不做 silent fallback。
- 更新 `include/npu_demo/npu_demo.h`，改为聚合 `include/api/Arch.h` 与 `include/npu_demo/Arch.h` 的统一入口，保留既有 Core/Memory/Dma/Nn 聚合关系。
- 更新 `kernel_gen/target/registry.py`，放开 `arch.launch` / `arch.barrier`，保持 `arch.launch_kernel` 未启用，并把 `npu_demo` 模板能力上限收口为 `block_num=1`、`thread_num=8`、`subthread_num=1`。
- 新增 `test/include/api/test_arch.py`，验证 include/api 头只暴露公共声明、拒绝字符串 callee、且不泄漏后端实现。
- 更新 `test/include/npu_demo/test_kernel_context.py`，补齐 launched body 的 runtime view、显式 `barrier(visibility, scope)`、以及不支持 extent 时显式失败的用例。
- 更新 `test/target/test_target_registry.py`，补齐 `npu_demo` 对 `arch.launch` / `arch.barrier` 支持与能力上限的断言。
- 改动文件：`include/api/Arch.h`、`include/npu_demo/Arch.h`、`include/npu_demo/npu_demo.h`、`kernel_gen/target/registry.py`、`test/include/api/test_arch.py`、`test/include/npu_demo/test_kernel_context.py`、`test/target/test_target_registry.py`。
- 验证命令 1：`pytest -q test/include/api/test_arch.py`
  - 退出码：`0`
  - 关键输出：`3 passed in 0.55s`
- 验证命令 2：`pytest -q test/include/npu_demo/test_kernel_context.py -k 'runtime or barrier'`
  - 退出码：`0`
  - 关键输出：`2 passed, 10 deselected in 0.69s`
- 验证命令 3：`pytest -q test/target/test_target_registry.py -k 'npu_demo and launch'`
  - 退出码：`0`
  - 关键输出：`1 passed, 18 deselected in 0.38s`
结论：T-20260406-d234a944 已按 S2 冻结合同完成实现与补测，三条 gate 均 `exit=0`。当前 worktree 仍保留同链路已冻结 spec 变更（`spec/include/api/Arch.md`、`spec/include/npu_demo/npu_demo.md`、`spec/target/registry.md`），本次未额外改动 spec 内容。已知风险：`launch` 运行时当前只覆盖 P0 子集 `block=1`、`subthread=1`、`2 <= thread <= 8`，更宽能力矩阵仍需后续阶段扩展。下一步建议：派生唯一审查任务，重点核对 `KernelContext` 运行时视图、barrier 失败短语与 registry 能力矩阵是否与冻结 spec 完全一致。

时间：2026-04-06 05:41 +0800
经办人：不要啊教练
任务：T-20260406-5c8b6d34（npu_demo_parallel_add_sync_green_plan-S2-审查）
任务目标：复核 KernelContext 运行时视图与 runtime 注入、barrier(visibility, scope) 失败边界与错误短语、thread_num/block_num 返回 launch 值、target.registry 放开 arch.launch/arch.barrier 且 thread_num=8 作为能力上限的合同；核对 gate 证据。
改动：
- 审查范围：include/api/Arch.h、include/npu_demo/Arch.h、include/npu_demo/npu_demo.h、kernel_gen/target/registry.py、spec/include/api/Arch.md、spec/include/npu_demo/npu_demo.md、spec/target/registry.md、test/include/api/test_arch.py、test/include/npu_demo/test_kernel_context.py、test/target/test_target_registry.py。
结论：审查通过。
问题清单：无。
风险：未发现新增漏洞风险；P0 之外能力未覆盖与 spec 一致。
验证命令：
- pytest -q test/include/api/test_arch.py
- pytest -q test/include/npu_demo/test_kernel_context.py -k "runtime or barrier"
- pytest -q test/target/test_target_registry.py -k "npu_demo and launch"
关键输出：
- 3 passed in 0.56s
- 2 passed, 10 deselected in 0.61s
- 1 passed, 18 deselected in 0.36s
下一步建议：派生合并任务，交由李白执行合并收口。

时间：2026-04-06 05:45:55 +0800
经办人：李白
任务：T-20260406-06e60898（npu_demo_parallel_add_sync_green_plan-S2-合并收口）
任务目标：复跑 S2 gate（include/api、npu_demo KernelContext、target registry），合并审查通过的 spec/实现/测试到 main 并 push，清理 worktree/branch。
改动：
- 合入文件（业务）：`include/api/Arch.h`、`include/npu_demo/Arch.h`、`include/npu_demo/npu_demo.h`、`kernel_gen/target/registry.py`、`spec/include/api/Arch.md`、`spec/include/npu_demo/npu_demo.md`、`spec/target/registry.md`、`test/include/api/test_arch.py`、`test/include/npu_demo/test_kernel_context.py`、`test/target/test_target_registry.py`。
- 合入文件（记录）：`agents/codex-multi-agents/log/task_records/2026/15/20260406-npu-demo-sync-s2.md`。
- gate（复跑，均 exit=0）：
  - `pytest -q test/include/api/test_arch.py` -> `3 passed in 0.53s`
  - `pytest -q test/include/npu_demo/test_kernel_context.py -k "runtime or barrier"` -> `2 passed, 10 deselected in 0.67s`
  - `pytest -q test/target/test_target_registry.py -k "npu_demo and launch"` -> `1 passed, 18 deselected in 0.36s`
- merge_commit：`b8df926eb8c7091c3b33e7fac15c26d6e53d4535`。
- push(main)：`timeout 60 git push origin main`（exit=0）。
- cleanup：`git worktree remove wt-20260406-npu-demo-sync-s2 --force`；`git branch -D T-20260406-d234a944`。
结论：S2 变更已合入并推送主分支，gate 全绿，worktree/分支已清理；无后续任务。
