时间：2026-04-09 03:26:00 +0800
经办人：李白
任务：T-20260408-ad1ff0f4（codex-multi-agents-task：-new worktree 必填且唯一）
任务目标：合并收口 `codex-multi-agents-task.sh -new` 的 `-worktree` 参数约束：禁止 `None`/空值，并在“正在执行的任务/任务列表”中要求 worktree 唯一。
改动：
- 更新 [`skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`](../../../../../skills/codex-multi-agents/scripts/codex-multi-agents-task.sh)：
  - `-new` 校验 `-worktree` 必须为非空且非 `None`。
  - 新增 worktree 唯一性校验：与“正在执行的任务/任务列表”中已有 worktree 重复时返回 `3` 并给出冲突任务 ID。
- 更新 [`spec/codex-multi-agents/scripts/codex-multi-agents-task.md`](../../../../../spec/codex-multi-agents/scripts/codex-multi-agents-task.md)：补齐 `-new worktree` 取值约束与重复返回码口径，并增补对应测试用例编号。
- 更新 [`test/codex-multi-agents/test_codex-multi-agents-task.py`](../../../../../test/codex-multi-agents/test_codex-multi-agents-task.py)：
  - 将原 `worktree=None` 的成功路径用例调整为显式路径；
  - 新增 `worktree=None` 失败用例与 worktree 重复返回 `3` 的覆盖。
结论：
- 已在 `wt-20260408-new-worktree` 完成合并提交并 push(main)=0；无合并冲突，按合并规范未额外复跑 pytest。
