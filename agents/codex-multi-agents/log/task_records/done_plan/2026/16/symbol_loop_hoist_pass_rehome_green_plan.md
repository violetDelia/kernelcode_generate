# symbol_loop_hoist_pass_rehome_green_plan.md

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`小李飞刀`
- 目标 `spec`：
  - [`spec/pass/symbol_loop_hoist.md`](../../spec/pass/symbol_loop_hoist.md)
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- 目标 `API`：
  - [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)
  - [`kernel_gen/passes/__init__.py`](../../kernel_gen/passes/__init__.py)
  - [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
- 目标 `test`：
  - [`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py)
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
- 目标 `验收资产`：
  - 正式合入资产：
    - [`spec/pass/symbol_loop_hoist.md`](../../spec/pass/symbol_loop_hoist.md)
    - [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)
    - [`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py)
    - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
  - 架构侧合同参考：
    - [`expectation/pass/symbol_loop_hoist/__main__.py`](../../expectation/pass/symbol_loop_hoist/__main__.py)
    - `cd /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_loop_hoist`
- 目标 `功能实现`：
  - [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)
  - [`kernel_gen/passes/__init__.py`](../../kernel_gen/passes/__init__.py)
  - [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1` | `无` | `wt-20260419-symbol-loop-hoist-pass-s1` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-symbol-loop-hoist-pass-s1.md` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`
- 结论摘要：`同意本轮只收迁移 + expectation 全通过，且不拆单独 spec 任务；单任务 S1 足以一次性收口。review pattern 口径明确为“单次只向上提一层，但 pass 反复运行直到 IR 稳定”；当前支持范围先锁 symbol.const 与 symbol.add/sub/mul/div/floordiv，与现有 expectation 覆盖一致；未纳入支持集合的 op 保持原位不动，不作为失败处理。补充该边界后已复评通过，可按当前版本直接建任务推进。`

## 最终验收结论（2026-04-20 00:21:40 +0800）

- 验收人：`守护最好的爱莉希雅`
- 验收结论：`不通过`
- 验证基线：
  - 当前主仓执行目录：`/home/lfr/kernelcode_generate`
  - 当前 `HEAD`：`c44ef67b55cd5675c595094a0ffa6dc4e03bafce`
- 实际复跑结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_loop_hoist` -> `exit 1`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_symbol_loop_hoist.py` -> `7 passed`
- 最小阻断项：
  - [`expectation/pass/symbol_loop_hoist/__main__.py`](../../expectation/pass/symbol_loop_hoist/__main__.py) 的 `CASE-1` 当前仍失败；`symbol.const` 外提后的 IR 未匹配 expectation 锁定文本，报错为 `expected ok=True, got ok=False`，并指向 `const-hoist` 片段中的 `symbol.const 2` 未按预期出现在下一行。
- 结论说明：
  - 当前 `TODO.md` 中该计划状态虽为 `完成待检查`，但主仓终验命令未全绿，因此不满足归档前置条件。
  - 本段为本轮按规则补回的正文终验结论与验证基线。

## 复核结论（2026-04-20 00:23:25 +0800）

- 验收人：`大闸蟹`
- 验收结论：`不通过`
- 验证基线：
  - 当前主仓执行目录：`/home/lfr/kernelcode_generate`
  - 当前 `HEAD`：`c44ef67b55cd5675c595094a0ffa6dc4e03bafce`
- 实际复跑结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_loop_hoist` -> `exit 1`
  - `python3 -m pytest -q test/pass/symbol_loop_hoist/test_symbol_elewise.py` -> `exit 4`（`file or directory not found`）
  - `python3 -m pytest -q test/pass/test_pass_manager.py -k symbol_loop_hoist` -> `3 passed`
- 最小阻断项：
  - [`expectation/pass/symbol_loop_hoist/__main__.py`](../../expectation/pass/symbol_loop_hoist/__main__.py) 的 `CASE-1` 仍失败；`symbol.const` 外提后的 IR 未匹配 expectation 锁定文本，错误为 `CHECK-NEXT not found on next line`。
  - 计划正文与验收设计仍点名不存在的 [`test/pass/symbol_loop_hoist/test_symbol_elewise.py`](../../test/pass/symbol_loop_hoist/test_symbol_elewise.py)；当前专属 pytest 路径尚未与正文验收项同步收口。
- 结论说明：
  - 当前仍不满足归档前置条件。
  - 本段为本轮按规则补回的正文复核结论与验证基线。

## 当前唯一修复任务（2026-04-20 03:57:32 +0800）

- 任务号：`T-20260420-caaeb711`
- `worktree`：`/home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s3`
- 记录文件：`/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/16/20260420-symbol-loop-hoist-pass-s3.md`
- 最小修复目标：
  - 修复 [`expectation/pass/symbol_loop_hoist/__main__.py`](../../expectation/pass/symbol_loop_hoist/__main__.py) `CASE-1` 对应的 `symbol.const` 外提文本差异，使目录入口恢复通过。
  - 同步收口计划正文中的正式验收口径，去掉对不存在测试路径的旧点名，保证终验命令与当前仓库布局一致。
- 说明：
  - 该任务承接上一轮已完成的合并任务 [`T-20260420-3f9d2b03`](../../DONE.md)，作为当前唯一保留的修复入口。

## 复验结论（2026-04-20 04:34:41 +0800）

- 复验人：`大闸蟹`
- 复验结论：`不通过`
- 验证基线：
  - 当前主线验收基线：`main@e29116f888df3097f0b057edcf73bb05da2d647e`
  - 实际复验现场：`/tmp/kernelcode_generate-symbol-loop-hoist-archive-check`（由 `e29116f888df3097f0b057edcf73bb05da2d647e` 创建的临时只读 `worktree`）
- 实际复跑结果：
  - `cd /tmp/kernelcode_generate-symbol-loop-hoist-archive-check && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/kernelcode_generate-symbol-loop-hoist-archive-check:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_loop_hoist` -> `6` 个 `CASE` 全部通过
  - `cd /tmp/kernelcode_generate-symbol-loop-hoist-archive-check && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_symbol_loop_hoist.py` -> `8 passed`
  - `cd /tmp/kernelcode_generate-symbol-loop-hoist-archive-check && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_manager.py -k symbol_loop_hoist` -> `3 passed, 15 deselected`
  - `cd /tmp/kernelcode_generate-symbol-loop-hoist-archive-check && rg -n "kernel_gen\\.passes\\.lowering\\.symbol_loop_hoist|spec/pass/lowering/symbol_loop_hoist|test/pass/test_symbol_loop_hoist" kernel_gen spec test` -> `exit 0`
- 最小阻断项：
  - 按当前计划正文的验收必过项，旧路径残留扫描仍命中：[`kernel_gen/passes/lowering/symbol_loop_hoist.py`](../../kernel_gen/passes/lowering/symbol_loop_hoist.py)、[`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)、[`spec/pass/lowering/symbol_loop_hoist.md`](../../spec/pass/lowering/symbol_loop_hoist.md)、[`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py) 仍保留 `lowering` 专题源头与导入口径；当前主线尚未满足计划中“迁移/rehome”这一验收条件。
- 必要摘要：
  - `CASE-1` 的 `symbol.const` 外提文本、目录级 expectation runner 与专属 pytest 已在 `e29116f` 上恢复通过。
  - 当前真正剩余的阻断不在行为正确性，而在计划正文明确要求的旧 `lowering` 路径残留尚未清空，因此我不能给出归档“通过”结论。

## 当前唯一修复任务（2026-04-20 04:11:27 +0800）

- 任务号：`T-20260420-5b710e81`
- `worktree`：`/home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4`
- 记录文件：`/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/16/20260420-symbol-loop-hoist-pass-s4.md`
- 最小修复目标：
  - 清理旧路径残留扫描仍命中的 [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)、[`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)、[`spec/pass/symbol_loop_hoist.md`](../../spec/pass/symbol_loop_hoist.md)、[`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py) 中旧专题源头与导入口径。
  - 维持 `symbol.const` / `symbol.add/sub/mul/div/floordiv` 外提行为、目录级 expectation runner 与专属 pytest 继续通过。
- 说明：
  - 该任务承接上一轮已完成的合并任务 [`T-20260420-caaeb711`](../../DONE.md)，作为当前唯一保留的修复入口。

## 复验结论（2026-04-20 05:19:46 +0800）

- 复验人：`守护最好的爱莉希雅`
- 复验结论：`通过`
- 验证基线：
  - 当前主线验收基线：`main@f4b894eb02aef35e7c563449406d3968985e5a14`
  - 当前主仓执行目录：`/home/lfr/kernelcode_generate`
- 实际复跑结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_loop_hoist` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_symbol_loop_hoist.py` -> `9 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_manager.py -k symbol_loop_hoist` -> `3 passed`
  - `rg -n "kernel_gen/passes/lowering/symbol_loop_hoist\\.py|spec/pass/lowering/symbol_loop_hoist\\.md|kernel_gen\\.passes\\.lowering\\.symbol_loop_hoist|spec/pass/lowering/symbol_loop_hoist" kernel_gen spec test` -> `exit 1`
- 必要摘要：
  - `symbol.const` 与 `symbol.add/sub/mul/div/floordiv` 的目录级 expectation 已恢复全绿，专属 pytest 与 pass_manager 顺序回归同步通过。
  - 旧 `lowering` 专题源文件与公开导入口径残留已清空；当前剩余 `test/pass/test_symbol_loop_hoist.py` 属于现行专题正式测试入口，不再构成迁移阻断。
  - 该计划当前已满足归档前置条件。

## 复验结论（2026-04-20 05:24:54 +0800）

- 复验人：`大闸蟹`
- 复验结论：`通过`
- 验证基线：
  - 当前主线验收基线：`main@f4b894eb02aef35e7c563449406d3968985e5a14`
  - 当前主仓执行目录：`/home/lfr/kernelcode_generate`
- 实际复跑结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_loop_hoist` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_symbol_loop_hoist.py` -> `9 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_manager.py -k symbol_loop_hoist` -> `3 passed, 15 deselected`
  - `rg -n "kernel_gen/passes/lowering/symbol_loop_hoist\\.py|spec/pass/lowering/symbol_loop_hoist\\.md|kernel_gen\\.passes\\.lowering\\.symbol_loop_hoist|spec/pass/lowering/symbol_loop_hoist" kernel_gen spec test` -> `exit 1`
- 必要摘要：
  - `symbol.const` 与 `symbol.add/sub/mul/div/floordiv` 的目录级 expectation、专属 pytest 与 pass_manager 顺序回归在最新主线已全部通过。
  - 旧 `lowering` 专题源文件与公开导入口径残留未再命中；`test/pass/test_symbol_loop_hoist.py` 当前作为正式专题测试入口保留，不构成迁移阻断。
  - 当前已满足归档前置条件，可进入唯一归档任务链。

## 输入摘要

- 目标：新建 `symbol_loop_hoist` 的重构计划，范围只收两件事：目录迁移与 expectation 全通过。
- 不做什么：不再拆单独 `spec` 任务，不把无关 `dma` / `tile` / 其他 pass 家族一起迁移，不在本轮引入 `memref`、`arith` 或统一 effect 体系。
- 当前痛点：expectation 已经上移到 [`expectation/pass/symbol_loop_hoist`](../../expectation/pass/symbol_loop_hoist)，但实现 / spec / pytest 仍在 `lowering` 归属；同时 expectation 当前只剩 `symbol.const` 外提这一条缺口未通过。
- 完成后最想看到的例子：`SymbolLoopHoistPass` 统一从 `kernel_gen.passes.symbol_loop_hoist` 导入，专题 `spec / 实现 / 专属 pytest / expectation` 都落在同主题目录；`python3 -m expectation.pass.symbol_loop_hoist` 全部通过。

## 计划目标

- 把 `symbol_loop_hoist` 的公开归属从 `lowing/lowering` 调整为独立的 `pass/symbol_loop_hoist` 主题目录。
- 把 pass 语义收口为“单次只向上提一层，但 pass 会重复运行直到 IR 不再变化”的 review pattern 形态。
- 把当前支持范围收口为 `symbol.const` 与首批标量 `symbol` 算术 `elewise`：`symbol.add/sub/mul/div/floordiv`。
- 把可外提条件收口为：`op` 属于支持集合，且所有 operands 都来自当前 `symbol.for` 之外的 SSA。
- 对未纳入支持集合的 op，保持原位不动，不作为失败处理。
- 让架构侧维护的 `expectation/pass/symbol_loop_hoist` 成为合同真源，并要求 black-box expectation 在当前任务现场可复现。
- 按用户要求，本计划不拆单独 `spec` 任务；普通 build/review/merge 只改 spec、实现与测试，不把本地 expectation 副本或 `.gitignore` 放行规则纳入正常合并内容。

## 当前基线

- 当前公开合同：
  - [`spec/pass/symbol_loop_hoist.md`](../../spec/pass/symbol_loop_hoist.md) 作为当前专题 `spec`，收口 pass 的公开语义与验收边界。
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md) 已记录 `symbol-loop-hoist` 与 `tile`、`lower-dma-memory-hierarchy` 的顺序关系。
- 当前公开 API：
  - [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py) 作为当前实现入口。
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py) 现从 `kernel_gen.passes.symbol_loop_hoist` 导入。
- 当前实现入口：
  - 唯一实现文件已迁移到 [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)。
  - 当前实现使用“循环内扫描 + 反复推进”的结构，并已把“单层上提 + 反复运行到稳定”收口为公开合同。
  - 当前实现已支持 `symbol.const` 与 `symbol.add/sub/mul/div/floordiv` 这组标量 `symbol` 外提。
- 当前测试与验收资产：
  - expectation 已在主仓 [`expectation/pass/symbol_loop_hoist/__main__.py`](../../expectation/pass/symbol_loop_hoist/__main__.py)，且已改为 `ircheck` 黑盒口径。
  - 专属 pytest 当前是 [`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py)。
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py) 已覆盖顺序约束，但仍引用旧路径。
- 当前缺口或失败点：
  - 当前公开文本、实现入口与专属 pytest 已切到 root 专题目录，待在 `wt-20260420-symbol-loop-hoist-pass-s4` 复跑 expectation / pytest / pass_manager 并补回任务记录。
  - 需要确认包级兼容入口仍可通过 `kernel_gen.passes.lowering` 访问，但不再作为主入口对外书写。
  - 旧路径扫描应在 `kernel_gen spec test` 维度不再命中。

## 合同真源顺序

- `架构侧 expectation 基线 > spec/pass/symbol_loop_hoist.md > test/pass/test_symbol_loop_hoist.py > 当前实现`

## 方案比较与选型

- 不采用方案：只修 `expectation/pass/symbol_loop_hoist/__main__.py`，保留实现 / spec / pytest 都在 `lowering` 旧目录。
  - 原因：这会继续保留“合同目录”和“实现目录”两套口径，后续维护者仍需猜专题边界。
- 不采用方案：先做单独 `spec` 任务，再做实现任务。
  - 原因：用户已经明确不希望有单独 `spec` 任务；当前范围也足够清楚，可以在单个执行任务里同步更新 spec。
- 采用方案：
  - `spec` 与实现保持围绕 `symbol_loop_hoist` 专题收口；
  - 专属 pytest 以 [`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py) 为当前正式入口；
  - expectation 保持在主仓 [`expectation/pass/symbol_loop_hoist`](../../expectation/pass/symbol_loop_hoist)，由架构侧维护；
  - `registry / pass_manager / lowering.__init__` 这类文件只同步引用，不另起专题。
- 最小公开接口：
  - `from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass`
  - `from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistError`

## 公开 API 设计

- 公开入口：
  - `kernel_gen.passes.symbol_loop_hoist.SymbolLoopHoistPass`
  - `kernel_gen.passes.symbol_loop_hoist.SymbolLoopHoistError`
- 参数顺序：
  - `SymbolLoopHoistPass.run(module)`
- 参数类型：
  - `module: ModuleOp`
- 返回值：
  - `run(module) -> module`
- 公开行为：
- 单次命中只把 candidate 向上提一层到最近父 block。
- pass 只要本轮改了 IR，就继续运行；直到不再变化。
- 当前支持集合仅包含 `symbol.const` 与首批标量 `symbol` 算术 `elewise`：`symbol.add/sub/mul/div/floordiv`。
- 只有当候选 op 的所有 operands 都来自当前 `symbol.for` 之外的 SSA 时，才允许外提。
- 未纳入支持集合的 op 保持原位不动，不作为失败处理。

```python
from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass

module = SymbolLoopHoistPass().run(module)
```

## 完成态定义

- [`spec/pass/symbol_loop_hoist.md`](../../spec/pass/symbol_loop_hoist.md) 作为当前专题 `spec`，收口 pass 的公开语义与验收边界。
- [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py) 作为当前实现入口。
- [`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py) 作为当前专属 pytest 入口。
- 主仓 [`expectation/pass/symbol_loop_hoist`](../../expectation/pass/symbol_loop_hoist) 继续作为架构侧合同入口；当前任务现场若出现同名本地副本，只能用于复现，不属于正常合并内容，也不得通过修改 `.gitignore` 放行。
- `symbol.const` 与 `symbol.add/sub/mul/div/floordiv` 的外提语义统一收口为“单层上提 + 反复运行到稳定 + operands 全部来自 loop 外 SSA”。
- 未纳入支持集合的 op 统一保持原位，不作为失败处理。

## 验收设计

- 验收资产：
  - 正式合入资产：
    - [`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py)
    - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
  - 架构侧合同参考：
    - [`expectation/pass/symbol_loop_hoist/__main__.py`](../../expectation/pass/symbol_loop_hoist/__main__.py)
- 输入样例：
  - loop 内单个 `symbol.const`
  - loop 内 `symbol.add/sub/mul/div/floordiv`
  - 带 `tile` / `lower-dma-memory-hierarchy` 的 pass 顺序组合
- 锁定输出：
- `symbol.const` 与标量 `symbol` 算术 `elewise` 被向上提到最近父 block
- 同一条链可在多轮运行中逐层继续上提，直到稳定
- 不在当前支持集合内的 op 保持原位，不触发 pass 失败
- pass 顺序关系继续保持原有要求
- 必过命令：
  - `cd /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_loop_hoist`
  - `pytest -q test/pass/test_symbol_loop_hoist.py`
  - `pytest -q test/pass/test_pass_manager.py -k symbol_loop_hoist`
- 验证基线：
  - 在最新同步任务现场的 `worktree` 中执行；若根目录旧现场与任务 `worktree` 不一致，只记为现场差异，不单独作为阻断依据。
  - `expectation` 目录按 [`agents/standard/expectation任务规则.md`](../../agents/standard/expectation任务规则.md) 由架构侧保管；普通 build/review/merge 不得通过本地副本或 `.gitignore` 放行把 expectation 改动带入交付。

## 阶段拆分

### S1：symbol_loop_hoist 迁移、重构与 expectation 收口

#### 阶段目标

- 一次性收口 `symbol_loop_hoist` 的实现、测试与 review pattern 形态，并把 expectation 入口归属、task-site 复现方式与正常合并边界写清；不拆单独 `spec` 阶段。

#### 目标 spec / API

- [`spec/pass/symbol_loop_hoist.md`](../../spec/pass/symbol_loop_hoist.md)
- `公开 API：kernel_gen.passes.symbol_loop_hoist.SymbolLoopHoistPass`
- `公开 API：kernel_gen.passes.symbol_loop_hoist.SymbolLoopHoistError`
- `同步引用：kernel_gen/passes/lowering/__init__.py、kernel_gen/passes/registry.py、kernel_gen/passes/pass_manager.py`

#### 禁止修改面 / 合同真源

- `禁止修改面：非架构师不得把 expectation 文件或 .gitignore 放行规则纳入正常合并内容；执行人只可修改与 symbol_loop_hoist 直接相关的 spec、实现、专属 pytest 与公开引用，不应把无关 pass 家族、无关 symbol/dma 专题一起扩进来。`
- `合同真源：架构侧 expectation 基线 > spec/pass/symbol_loop_hoist.md > test/pass/test_symbol_loop_hoist.py > 当前实现；当前任务 worktree 内若存在 expectation 副本，只作为现场复现材料，不改变正常合并边界。`

#### 预期示例代码

```python
from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass

module = SymbolLoopHoistPass().run(module)
```

```text
builtin.module {
  func.func @demo() {
    %c0 = symbol.const 0 : !symbol.int<"0">
    %c1 = symbol.const 1 : !symbol.int<"1">
    %c2 = symbol.const 1 : !symbol.int<"1">
    symbol.for %it = %c0 to %c1 step %c2 {iter = #symbol.iter<start = "0", end = "1", step = "1">} {
      %v = symbol.add %lhs, %rhs : !symbol.int<"4">, !symbol.int<"5"> -> !symbol.int<"9">
    }
    func.return
  }
}
```

#### 预期输出

```text
- symbol_loop_hoist 公开语义已写清为“单层上提 + 反复运行到稳定”
- test/pass/test_symbol_loop_hoist.py 与 test/pass/test_pass_manager.py 可直接作为当前正式回归入口
- 架构侧 expectation 基线可在 task-site 复现，不依赖 worktree expectation 副本或 .gitignore 放行
```

#### 目标验收资产

- 正式合入资产：
  - [`kernel_gen/passes/__init__.py`](../../kernel_gen/passes/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`spec/pass/symbol_loop_hoist.md`](../../spec/pass/symbol_loop_hoist.md)
  - [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)
  - [`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py)
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
  - [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py)
- 架构侧合同参考：
  - [`expectation/pass/symbol_loop_hoist/__main__.py`](../../expectation/pass/symbol_loop_hoist/__main__.py)
  - `cd /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_loop_hoist`

#### 验收必过项目

- `cd /home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260420-symbol-loop-hoist-pass-s4:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_loop_hoist`
- `pytest -q test/pass/test_symbol_loop_hoist.py`
- `pytest -q test/pass/test_pass_manager.py -k symbol_loop_hoist`
- `rg -n "kernel_gen\\.passes\\.lowering\\.symbol_loop_hoist|spec/pass/lowering/symbol_loop_hoist|test/pass/test_symbol_loop_hoist" kernel_gen spec test`

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：迁移并重构 symbol_loop_hoist pass，同步收口 spec / 专属 pytest / expectation，确保 expectation 全通过；不拆单独 spec 任务`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-symbol-loop-hoist-pass-s1.md`

## 待确认项

- 问题：`无`
- 可选项：`无`
- 差异：`无`
- 推荐项：`无`

## 用户确认与协同约束

- `用户确认状态：已确认`
- `未确认事项：无`
- `用户确认结论：新计划只收 symbol_loop_hoist pass 重构，两项目标是迁移与 expectation 全通过；不希望有单独 spec 任务。`
- `未确认前处理要求：无`
- `若用户要求至少询问 3 人：无`
- `询问记录 1：守护最好的爱莉希雅 / 已互评通过并在补充“未纳入支持集合的 op 保持原位不动、不作为失败处理”后复评通过 / 可按当前版本直接建任务推进`
- `询问记录 2：无`
- `询问记录 3：无`

## 参考资料

- [`expectation/pass/symbol_loop_hoist/__main__.py`](../../expectation/pass/symbol_loop_hoist/__main__.py)
- [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)
- [`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py)
- [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
- [`spec/pass/symbol_loop_hoist.md`](../../spec/pass/symbol_loop_hoist.md)
