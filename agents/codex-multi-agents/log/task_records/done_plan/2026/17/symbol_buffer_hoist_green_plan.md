# symbol_buffer_hoist_green_plan.md

> 说明：该文件为 `symbol_buffer_hoist` 主题在 latest main 对齐后的 surviving 归档承接快照。`origin/main@315bd81e7b660c809e82900ca94ca64bd38bc4e2` 的干净现场已不再包含 `ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md`、`TODO.md` 与 `expectation` 包；因此正文里提到的 `expectation/pass/symbol_buffer_hoist/**` 与 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist` 只用于说明历史 / 本地归因来源，不构成 latest main 可直接运行入口。当前 latest main tracked direct asset 已收为本归档文件与 [`20260427-symbol-buffer-hoist-plan-align-s2.md`](../../../2026/17/20260427-symbol-buffer-hoist-plan-align-s2.md)；[`20260427-symbol-buffer-hoist-plan-fix-s2.md`](../../../2026/17/20260427-symbol-buffer-hoist-plan-fix-s2.md) 仅保留为第一轮修复记录，不再作为当前 direct asset 概括。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`睡觉小分队`
- 目标 `spec`：
  - [`spec/pass/symbol_buffer_hoist.md`](../../../../../../../spec/pass/symbol_buffer_hoist.md)
  - [`spec/pass/registry.md`](../../../../../../../spec/pass/registry.md)
- 目标 `API`：
  - [`kernel_gen/passes/symbol_buffer_hoist.py`](../../../../../../../kernel_gen/passes/symbol_buffer_hoist.py)
  - [`kernel_gen/passes/__init__.py`](../../../../../../../kernel_gen/passes/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../../../../../../kernel_gen/passes/registry.py)
- 目标 `test`：
  - [`test/pass/test_symbol_buffer_hoist.py`](../../../../../../../test/pass/test_symbol_buffer_hoist.py)
  - [`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py)
- 目标 `验收资产`：
  - [`test/pass/test_symbol_buffer_hoist.py`](../../../../../../../test/pass/test_symbol_buffer_hoist.py)
  - [`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py)
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_symbol_buffer_hoist.py test/pass/test_pass_registry.py`
- 目标 `功能实现`：
  - [`kernel_gen/passes/symbol_buffer_hoist.py`](../../../../../../../kernel_gen/passes/symbol_buffer_hoist.py)
  - [`kernel_gen/passes/__init__.py`](../../../../../../../kernel_gen/passes/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../../../../../../kernel_gen/passes/registry.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1：symbol-buffer-hoist 的 spec / build / pytest / 合同归因收口` | 无 | `wt-20260427-symbol-buffer-hoist-s1` | `agents/codex-multi-agents/log/task_records/2026/17/20260427-symbol-buffer-hoist-s1.md` |
| `S2：计划资产与 latest main 现场对齐 / 归档记录收口` | `T-20260427-51e32bf0` | `wt-20260427-symbol-buffer-hoist-plan-align-s2` | `agents/codex-multi-agents/log/task_records/2026/17/20260427-symbol-buffer-hoist-plan-align-s2.md` |

## 任务创建记录

- `S1=T-20260427-799dca63，任务类型 spec，worktree=wt-20260427-symbol-buffer-hoist-s1，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260427-symbol-buffer-hoist-s1.md`
- `R1=T-20260427-51e32bf0，任务类型 spec，任务目标：回收 python3 -m expectation.pass.symbol_buffer_hoist 的 build 必过项口径，写清 repo root unknown pass 与 immutable case 的计划层归因；记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260427-symbol-buffer-hoist-plan-fix-s2.md`
- `S2=T-20260427-b79086bb，任务类型 spec，任务目标：只收计划资产与 latest main 现场对齐，并同步 surviving done_plan / 当前记录承接位置；记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260427-symbol-buffer-hoist-plan-align-s2.md`
- `S3=T-20260428-71c1ecdf，任务类型 spec，任务目标：修复 surviving done_plan 与 20260427-symbol-buffer-hoist-plan-align-s2.md 中残留的 expectation 活动验收 / 合同真源顺序，以及旧的 not-through / plan-fix-s2 口径；记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260428-symbol-buffer-hoist-plan-align-s3.md`
- `最新 latest main 基线：origin/main@315bd81e7b660c809e82900ca94ca64bd38bc4e2`
- `当前主线 direct asset：agents/codex-multi-agents/log/task_records/done_plan/2026/17/symbol_buffer_hoist_green_plan.md + agents/codex-multi-agents/log/task_records/2026/17/20260427-symbol-buffer-hoist-plan-align-s2.md`
- `第一轮修复记录：agents/codex-multi-agents/log/task_records/2026/17/20260427-symbol-buffer-hoist-plan-fix-s2.md`

## 终验 / 复验 / 修复复核记录

- 结论人：`守护最好的爱莉希雅`
- 结论：`历史第一轮复验不通过（旧口径已由 T-20260428-71c1ecdf 继续修正）`
- 验证基线：`origin/main@315bd81e7b660c809e82900ca94ca64bd38bc4e2`
- 执行目录：`/home/lfr/kernelcode_generate-wt-20260427-symbol-buffer-hoist-recheck-1`
- 相关验收摘要：`公开 pytest 已闭合；后续修复阶段已把 latest main 中不存在 expectation 包这一事实转成历史 / 本地归因说明，不再把 python3 -m expectation.pass.symbol_buffer_hoist 写成当前活动验收入口。`
- 最小阻断项或通过摘要：`本条只保留第一轮复验背景；当前 latest main 直接承接资产上的 residual 口径，已转由 T-20260428-71c1ecdf 继续收口。`
- 是否已创建修复任务：`是；T-20260428-71c1ecdf（wt-20260428-symbol-buffer-hoist-plan-align-s3；agents/codex-multi-agents/log/task_records/2026/17/20260428-symbol-buffer-hoist-plan-align-s3.md）`

## 计划目标

- 为 `kernel_gen.passes` 新增并公开 `symbol-buffer-hoist` pass，专门收口 `symbol.for` 内 `dma.alloc` 的保守外提语义。
- 让该 pass 同时具备 `包导出 + registry 构造 + CLI --pass` 三条公开消费路径。
- 用 `pytest` 锁住公开 API/registry 合同与 hoist 语义边界；本地共享计划里保留只读 `expectation` 作为历史合同对照，但 latest main 对齐后不把已缺失的 `expectation` 包伪装成主线可直接运行入口。

## latest main 承接说明

- `origin/main@315bd81e7b660c809e82900ca94ca64bd38bc4e2` 的干净现场不再包含：
  - `ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md`
  - `TODO.md`
  - `expectation` 包
- 当前 latest main tracked direct asset 为本归档文件与 [`20260427-symbol-buffer-hoist-plan-align-s2.md`](../../../2026/17/20260427-symbol-buffer-hoist-plan-align-s2.md)。
- 因此正文中的 `expectation/pass/symbol_buffer_hoist/**` 路径与 `python3 -m expectation.pass.symbol_buffer_hoist` 只继续承担历史 / 本地只读合同来源说明：
  - repo root `unknown pass 'symbol-buffer-hoist'` 不记为 `T-20260427-799dca63` build 的最终失败归因
  - immutable `pass-symbol_buffer_hoist-output_scratch-1` 与 `pass-symbol_buffer_hoist-shape_depends_on_loop_carried-1` 的失败继续归到计划层只读合同资产说明
- 自本轮对齐任务起，后续 latest main 续接依据统一收口到本归档文件与 [`20260427-symbol-buffer-hoist-plan-align-s2.md`](../../../2026/17/20260427-symbol-buffer-hoist-plan-align-s2.md)。

## 合同真源顺序

- latest main 活动执行顺序说明：`spec -> build -> test`
- latest main 对齐后的承接关系：
  - [`spec/pass/symbol_buffer_hoist.md`](../../../../../../../spec/pass/symbol_buffer_hoist.md)
  - > [`test/pass/test_symbol_buffer_hoist.py`](../../../../../../../test/pass/test_symbol_buffer_hoist.py) + [`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py)
  - > 本归档文件与 [`20260427-symbol-buffer-hoist-plan-align-s2.md`](../../../2026/17/20260427-symbol-buffer-hoist-plan-align-s2.md)
  - > 当前实现
- 说明：latest main 已无 `expectation` 包，因此 `expectation/pass/symbol_buffer_hoist/**` 与 `python3 -m expectation.pass.symbol_buffer_hoist` 只在共享现场与历史记录中作为归因来源出现，不再写成当前 direct asset 的活动合同真源。

## 验收设计

- `pytest -q test/pass/test_symbol_buffer_hoist.py test/pass/test_pass_registry.py` 是公开接口层的唯一必过命令。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist` 只保留为历史 / 本地只读合同来源说明，不计入 latest main 的可直接运行命令集合。
- latest main 现场若继续缺失 `expectation` 包，续接说明必须写回本归档文件与对齐记录，不得把缺失资产重新写成主线入口。
