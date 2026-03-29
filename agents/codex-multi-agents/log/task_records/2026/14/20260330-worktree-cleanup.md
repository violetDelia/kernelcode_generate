时间：2026-03-30 02:01:40 +0800
任务：T-20260330-9fe11d51
任务目标：清理遗留 worktree（wt-20260328-operation-dialect-mapping、wt-20260328-operation-invariants、wt-20260328-pass-acceptance-points），核对残余变更并执行合并/清理。

处置过程：
- 目录核对：3 个目标 worktree 均存在。
- 远程同步检查：执行 `timeout 120 git fetch origin --prune` 超时（exit 124），基于本地 `origin/main` 继续处置。
- `wt-20260328-operation-dialect-mapping`：仅残留未跟踪记录文件，且链路记录显示提交已进入主线（`e587c85`、`809420d`），无需再合并代码。
- `wt-20260328-operation-invariants`：仅残留未跟踪记录文件，链路记录显示提交 `b693e9d` 已推送主线，无需再合并代码。
- `wt-20260328-pass-acceptance-points`：存在未提交残余；核对后识别出未入主线且具业务价值改动：
  - 新增 `kernel_gen/passes/analysis/{__init__.py,func_cost.py}`（补齐 `func_cost` 实现入口与实现文件）；
  - 更新 `kernel_gen/passes/lowering/nn_to_kernel.py`（补充 module 可遍历性校验与异常归因包装）；
  - 更新 `spec/pass/pass_manager.md`、`spec/pass/analysis/func_cost.md`、`spec/pass/lowering/nn_to_kernel.md`（前后置条件/失败归因与用例映射收敛）；
  - 更新 `test/pass/test_lowering_nn_to_kernel.py`（补充 COV-N2K-024/025）；
  - 其余历史噪音（旧路径删除、仅元信息变更、`__pycache__`）不合并。

结论：
- 已在临时 merge worktree 吸收有效残余并准备提交；提交后执行一次 push。
- 3 个遗留 worktree 均进入可清理状态，待提交与推送结果确认后统一清理。
