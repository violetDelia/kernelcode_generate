## 正在执行的任务
| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 状态 | 用户指导 | 记录文件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T-20260325-99e9da4b | 神秘人 | 2026-03-25 23:21:11 +0800 | /home/lfr/kernelcode_generate/wt-20260325-rename-pass-to-passes | 合并任务：pass→passes 链路已复审通过，按合并规范将变更合入 main。范围限定 kernel_gen/passes/**、spec/pass/**、test/pass/** 与记录文件 agents/codex-multi-agents/log/task_records/2026/13/20260325-rename-pass-to-passes.md；禁止合入 agents/（除 task_records）、TODO.md、DONE.md、AGENTS.md、skills/ 或 expectation 改动；禁止 git stash；提交信息格式 T-<task_id>-<desc>；合并前确认 worktree 无其他进行中任务。必要时运行 pytest -q test/pass/test_pass_manager.py test/pass/test_lowing_nn_to_kernel.py 并记录结果。 | 我不是牛马 | 进行中 |  | agents/codex-multi-agents/log/task_records/2026/13/20260325-rename-pass-to-passes.md |
| T-20260325-1151cc27 | 神秘人 | 2026-03-25 23:28:48 +0800 | /home/lfr/kernelcode_generate/wt-20260325-expectation-dsl-emit-c-nn | 合并任务：emit_c 类型提示补齐已复审通过，按合并规范合入 main。范围限定 test/dsl/test_emit_c.py 与记录文件 agents/codex-multi-agents/log/task_records/2026/13/20260325-expectation-dsl-emit-c-nn.md；禁止合入 agents/（除 task_records）、TODO.md、DONE.md、AGENTS.md、skills/ 或 expectation 改动；禁止 git stash；提交信息格式 T-<task_id>-<desc>；合并前确认 worktree 无其他进行中任务。必要时运行 pytest -q test/dsl/test_emit_c.py 并记录结果。 | 我不是牛马 | 进行中 |  | agents/codex-multi-agents/log/task_records/2026/13/20260325-expectation-dsl-emit-c-nn.md |
| T-20260325-c1539555 | 神秘人 | 2026-03-25 23:35:50 +0800 | /home/lfr/kernelcode_generate/wt-20260325-expectation-temp-arch-get-block-id | cleanup 任务：确认 main 已包含提交 5014418 且 worktree 无未合入差异后，删除 /home/lfr/kernelcode_generate/wt-20260325-expectation-temp-arch-get-block-id 及本地分支；同步更新记录文件。禁止使用 git stash。 | 李白 | 进行中 |  | agents/codex-multi-agents/log/task_records/2026/13/20260325-expectation-temp-arch-get-block-id.md |

## 任务列表
| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 记录文件 |
| --- | --- | --- | --- | --- | --- | --- |
| T-20260325-bfeba81f | 榕 | 2026-03-25 23:35:08 +0800 |  | expectation任务：维护并完善 expectation/dsl/mlir_gen/dialect/dma/alloc.py（覆盖静态/动态/stride/错误参数与返回类型一致性） | 神秘人 |  |

## 需要用户确认的事项
| 任务 ID | 创建时间 | worktree | 描述 | 用户确认状态 | 记录文件 |
| --- | --- | --- | --- | --- | --- |
