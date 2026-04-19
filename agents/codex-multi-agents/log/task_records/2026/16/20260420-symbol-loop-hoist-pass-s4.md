时间：2026-04-20 04:23 +0800
经办人：小李飞刀
任务：T-20260420-5b710e81
任务目标：修复 symbol_loop_hoist 归档阻断，清理 lowering 残留路径与旧导入口径，收口 spec/test/registry 到当前专题归属。
改动：
- 将主实现迁移到 [`kernel_gen/passes/symbol_loop_hoist.py`](../../../../../../kernel_gen/passes/symbol_loop_hoist.py)，并把旧 `lowering` submodule 交给 [`kernel_gen/passes/lowering/__init__.py`](../../../../../../kernel_gen/passes/lowering/__init__.py) 做兼容导出。
- 将专题 spec 迁移到 [`spec/pass/symbol_loop_hoist.md`](../../../../../../spec/pass/symbol_loop_hoist.md)，同步把文档中的功能实现 / 使用示例 / 关联文件改成根级专题路径。
- 更新 [`kernel_gen/passes/__init__.py`](../../../../../../kernel_gen/passes/__init__.py) 公开导出 `SymbolLoopHoistPass` / `SymbolLoopHoistError`，更新 [`kernel_gen/passes/registry.py`](../../../../../../kernel_gen/passes/registry.py) 的 builtin 导入口径到根级模块。
- 更新 [`test/pass/test_symbol_loop_hoist.py`](../../../../../../test/pass/test_symbol_loop_hoist.py) 的根级导入、覆盖率描述与路径注释，并补了一条包级兼容导出断言。
- 同步更新 [`ARCHITECTURE/plan/symbol_loop_hoist_pass_rehome_green_plan.md`](../../../../../../ARCHITECTURE/plan/symbol_loop_hoist_pass_rehome_green_plan.md) 的当前任务段、正式合入资产与 s4 复现命令。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_loop_hoist` -> `6` 个 `CASE` 全部通过。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q test/pass/test_symbol_loop_hoist.py test/pass/test_pass_manager.py test/pass/test_pass_registry.py` -> `45 passed, 21 warnings`。
- `rg -n "kernel_gen\\.passes\\.lowering\\.symbol_loop_hoist|spec/pass/lowering/symbol_loop_hoist|kernel_gen/passes/lowering/symbol_loop_hoist" /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4/kernel_gen /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4/spec /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4/test` -> 未命中。
- `git -C /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4 status --short --branch --untracked-files=all` -> 仅当前任务改动与新增/删除文件。
结论：通过。当前 build 已完成，根级专题归属与旧 lowering 路径清理已同步收口；下一步按流程执行 `-next -auto -type review` 并回报管理员。

时间：2026-04-20 04:34 +0800
经办人：提莫炖蘑菇
任务：T-20260420-5b710e81
任务目标：复核 symbol_loop_hoist 根级专题归属收口结果、root spec/registry/test 对齐与旧 lowering 路径清理。
改动：
- 复核 [`kernel_gen/passes/symbol_loop_hoist.py`](../../../../../../kernel_gen/passes/symbol_loop_hoist.py) 的根级实现与 [`spec/pass/symbol_loop_hoist.md`](../../../../../../spec/pass/symbol_loop_hoist.md) 的专题归属是否一致。
- 复核 [`kernel_gen/passes/__init__.py`](../../../../../../kernel_gen/passes/__init__.py)、[`kernel_gen/passes/registry.py`](../../../../../../kernel_gen/passes/registry.py) 与 [`kernel_gen/passes/lowering/__init__.py`](../../../../../../kernel_gen/passes/lowering/__init__.py) 的导出/兼容口径。
- 复核 [`test/pass/test_symbol_loop_hoist.py`](../../../../../../test/pass/test_symbol_loop_hoist.py) 的专属断言与路径引用，以及旧 lowering 路径是否已从 `kernel_gen/spec/test` 中清理。
验证：
- `rg -n "kernel_gen\\.passes\\.lowering\\.symbol_loop_hoist|spec/pass/lowering/symbol_loop_hoist|kernel_gen/passes/lowering/symbol_loop_hoist" /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4/kernel_gen /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4/spec /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4/test` -> 未命中。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_loop_hoist` -> `6` 个 `CASE` 全部通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4 pytest -q /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4/test/pass/test_symbol_loop_hoist.py` -> `8 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4 pytest -q /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4/test/pass/test_pass_manager.py -k symbol_loop_hoist` -> `3 passed, 15 deselected`。
结论：通过。旧路径残留已清理，root spec/registry/test 与当前实现一致，symbol.const 外提和专属 pytest / expectation runner 仍通过。

时间：2026-04-20 05:17 +0800
经办人：李白
任务：T-20260420-5b710e81
任务目标：合并本轮已通过复审的 symbol_loop_hoist 根级专题归属收口结果、root spec/registry/test 对齐与旧 lowering 路径清理
改动：在指定 worktree 完成 merge 收口，带入 root 归属结果与旧路径清理：新增 `kernel_gen/passes/symbol_loop_hoist.py`、`spec/pass/symbol_loop_hoist.md`；删除 `kernel_gen/passes/lowering/symbol_loop_hoist.py`、`spec/pass/lowering/symbol_loop_hoist.md`；同步更新 `kernel_gen/passes/__init__.py`、`kernel_gen/passes/lowering/__init__.py`、`kernel_gen/passes/registry.py` 与 `test/pass/test_symbol_loop_hoist.py`；并在同次提交纳入当前任务记录文件。
验证：`git -C /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4 diff --name-status` -> 命中上述文件清单；`git -C /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4 diff --name-only --cached`（提交前）-> 空；`git -C /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4 status --short --branch --untracked-files=all` -> 仅本任务改动范围与记录文件；`git -C /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4 rev-parse --short HEAD` -> `e29116f`，`git -C /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4 rev-parse --short origin/main` -> `d71da6c`（提交后将前移并推送）。
结论：当前 merge 收口输入已确认，下一步执行单次提交、同步到最新主线后推送，完成 `-done` 并回报管理员。
