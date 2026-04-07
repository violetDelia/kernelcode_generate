时间：2026-04-08 04:50:00 +0800
经办人：李白
任务：T-20260408-83e8bdc1（prompt-sync-合并）
worktree：wt-20260408-prompt-sync

## 任务目标
- 合并 `wt-20260408-prompt-sync` 的提示词同步改动到 `main` 并 `push(main)=0`。

## 范围与授权说明
- 管理员分发的验收范围原为：仅 `agents/.../神秘人.prompt.md`、`agents/.../大闸蟹.prompt.md` + 本记录文件。
- 合并前检查发现该 worktree 还包含 `expectation/**` 相关删除差异；已先按规范对任务执行 `-pause` 并回报管理员确认。
- 后续用户明确指令：“继续任务，合并 /home/lfr/kernelcode_generate/wt-20260408-prompt-sync 的所有改动”，因此本次按用户授权合入该 worktree 的全部差异（含 `expectation/**` 删除）。

## 变更摘要
- 提示词同步：
  - `agents/codex-multi-agents/agents/神秘人/神秘人.prompt.md`
  - `agents/codex-multi-agents/agents/大闸蟹/大闸蟹.prompt.md`
- expectation 删除（按用户授权合入）：
  - `expectation/dsl/emit_c/npu_demo/add.py`
  - `expectation/dsl/mlir_gen/return_type_from_body_not_signature`
  - `expectation/utils/case_runner.py`

## 合并与推送
- 合并提交（rebase/最终）：4782222
- push(main)：见 `tmux -talk` 回报（按新规 push 成功后不再回头 fixup 记录）。

## 验证
- 本任务为 prompt-sync/文件清单合并；无合并冲突，按李白提示词规则默认不运行 `pytest`。

## cleanup
- worktree remove：见 `tmux -talk` 回报
- branch delete：见 `tmux -talk` 回报
