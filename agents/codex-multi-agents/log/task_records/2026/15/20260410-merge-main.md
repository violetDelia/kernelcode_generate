时间：2026-04-10 02:28:46 +0800
经办人：李白
任务：T-20260410-2c9a1fc6
任务目标：合并主仓工作区当前全部改动并推送到 `main`（以 `agents/codex-multi-agents/config/config.txt` 的 `BRANCH` 为准）。
改动：
- 提示词同步：更新多名角色的 `agents/codex-multi-agents/agents/*/*.prompt.md`。
- ircheck 链路：更新 `kernel_gen/tools/ircheck.py`、`spec/tools/ircheck.md`，并新增/更新 `test/tools/test_ircheck_{cli,parser,runner}.py`。
- 任务脚本：更新 `skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`。
- 变更范围以 `git diff --name-only` 输出为准（本次为上述文件集合）。
结论：已合并。
