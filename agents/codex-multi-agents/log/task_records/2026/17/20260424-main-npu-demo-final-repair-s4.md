# 20260424-main-npu-demo-final-repair-s4

## 任务信息

- 任务：`T-20260424-4781572d`
- 发起人：`神秘人`
- 计划书：[`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md)
- worktree：`/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4`

时间：2026-04-24 21:24
经办人：jcc你莫辜负
任务：T-20260424-4781572d
任务目标：核对 `expectation.pass.tuning.launch_kernel_cost_func` 目录入口当前失败与其直接关联的实现 / spec / test，确认当前 `build` 是否可在指定 worktree 内直接收口。
执行前阅读记录：已读 [`TODO.md`](../../../../../../TODO.md) 本任务行，确认当前类型为 `build`、目标为“只收 `expectation.pass.tuning.launch_kernel_cost_func` 目录入口失败及其直接关联的实现/spec/test”；已读计划书 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 最新复验 / 修复任务口径、全局完成态与合同真源顺序；已回读前序记录 [`wt-20260424-launch-kernel-cost-multi-kind-repair-s3/agents/codex-multi-agents/log/task_records/2026/17/20260424-launch-kernel-cost-multi-kind-repair-s3.md`](../../../../../../wt-20260424-launch-kernel-cost-multi-kind-repair-s3/agents/codex-multi-agents/log/task_records/2026/17/20260424-launch-kernel-cost-multi-kind-repair-s3.md)，确认这组 expectation 入口曾因旧 `multi_kind` / 前置状态不一致长期阻塞；已核对当前角色提示词与 [`agents/standard/expectation任务规则.md`](../../../../../../agents/standard/expectation任务规则.md)，当前角色默认不得修改仓库中的 `expectation` 文件，若任务确实需要改 `expectation` 必须先询问架构师。
最小功能闭环：先在新建 worktree 上确认“当前 Git 现场”里是否真的存在 `expectation.pass.tuning.launch_kernel_cost_func` 目录入口，以及失败是否仍是 `multi_kind.py`；若现场与任务文案不一致，则先记录 blocker，不直接越权新增或改写 `expectation` 资产。
改动：本轮尚未修改任何实现、spec、test 或 `expectation` 文件。已完成的动作只有：1）创建指定 worktree；2）核对 tracked 文件集合、目录入口实际加载来源与公开 pytest 基线；3）定位当前 blocker。
验证：
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 status --short` -> 当前 worktree 干净。
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 ls-files expectation/pass/tuning 'expectation/pass/tuning/launch_kernel_cost_func*'` -> 当前 tracked 现场只有 [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py) 与 [`basic_all.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py)，不存在 `expectation/pass/tuning/launch_kernel_cost_func/` package。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 python3 -m expectation.pass.tuning.launch_kernel_cost_func`（`cwd=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4`） -> `No module named expectation.pass.tuning.launch_kernel_cost_func`，说明纯 worktree 现场连目录入口 package 都不存在。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4:/home/lfr/kernelcode_generate python3 -m expectation.pass.tuning.launch_kernel_cost_func`（`cwd=/home/lfr/kernelcode_generate`） -> 失败于主仓额外状态中的 [`expectation/pass/tuning/launch_kernel_cost_func/__main__.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func/__main__.py) 裸 `import invalid_kind`，不是当前 tracked worktree 的真实文件。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4/test/pass/test_launch_kernel_cost_func.py /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4/test/dialect/test_tuner_dialect.py -ra` -> `56 passed, 1 warning`，直接关联的公开 pytest 当前通过。
Diff 反推自测：本轮尚未进入可执行的代码 diff。已按 blocker 定位只复核直接关联的公开 pytest 与目录入口现场，不把 `expectation` 合同入口当成 diff 反推测试的替代证据。
自检：已按任务要求先读 `TODO`、计划书最新修复口径、全局完成态和前序记录；已确认当前 blocker 来自 tracked worktree 与任务文案的现场不一致，而不是只看任务标题得出的猜测；未越权修改 `expectation`；当前若继续修复，至少需要在 tracked worktree 中新增 `expectation.pass.tuning.launch_kernel_cost_func` 相关资产，这一步按角色规则需先询问架构师。
结论：当前任务阻塞。具体 blocker 是：指定 worktree 的 tracked 现场并不存在 `expectation.pass.tuning.launch_kernel_cost_func` package，当前目录入口失败不是单纯的 `multi_kind.py` 断言问题，而是“当前现场缺 package，混入主仓额外状态后又失败于裸 `import invalid_kind`”。下一步先用 `-talk` 向 `守护最好的爱莉希雅` 和 `神秘人` 回报这一差异，请他们明确：1）是否允许在当前 worktree 内新增 `expectation/pass/tuning/launch_kernel_cost_func/{__main__.py,_shared.py}` 等 expectation 资产；2）若允许，是否需要同步改写直接关联 spec/test 说明。

---
时间：2026-04-24 21:34 +0800
经办人：守护最好的爱莉希雅
任务：T-20260424-4781572d
架构补充口径：
- 允许在当前任务内直接新增缺失的 `expectation/pass/tuning/launch_kernel_cost_func/` package 及其直接承接文件，用当前 tracked worktree 作为真实现场，不以主仓额外状态中的旧 package 为准。
- 新增范围只限本条目录入口恢复所必需的非只读 expectation 资产，例如 `__main__.py`、`_shared.py`、以及当前目录入口实际需要的 companion case / helper；不得顺手扩到无关 expectation family。
- `spec/test` 不要求默认一起改；只有在本任务为让新 package 成为当前写实合同时，发现直接关联的 spec/test 仍写旧路径、旧入口或旧错误短语，才一并最小同步，且同步范围只限与这条目录入口直接相关的说明与测试。
- 执行记录继续要求真实自检与 `Diff 反推自测`；`expectation` 仍只单列为合同验收资产，不替代对应测试。

---
时间：2026-04-24 21:28 +0800
经办人：jcc你莫辜负
任务：T-20260424-4781572d
任务目标：补齐当前 tracked worktree 内 `expectation.pass.tuning.launch_kernel_cost_func` 目录入口，并只承接与该入口直接相关的 helper / spec 同步，不引回旧四 kind expectation。
执行前阅读记录：已回读 [`TODO.md`](../../../../../../TODO.md) 当前任务行、计划书 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 最新修复口径与全局完成态；已结合本记录前半段 blocker 结论和 `守护最好的爱莉希雅` 的最新口径，确认本轮允许在当前 worktree 内新增 `expectation/pass/tuning/launch_kernel_cost_func/` 的非只读入口资产，但范围只限目录入口恢复所需文件。
最小功能闭环：1）给 [`expectation/pass/tuning/launch_kernel_cost_func`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func) 新增当前目录入口与 family 内共享 helper；2）把 [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py) 改成直接依赖新 helper，而不是缺失的 `expectation.utils.case_runner`；3）最小同步 [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../../../spec/pass/tuning/launch_kernel_cost_func.md) 中与当前目录入口现场不一致的表述；4）按实际 diff 跑公开 pytest 与本地脚本，再单列跑目录入口验收。
改动：
- 更新 [`.gitignore`](../../../../../../.gitignore)，只对白名单放开 [`expectation/pass/tuning/launch_kernel_cost_func/__main__.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func/__main__.py) 与 [`_shared.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func/_shared.py)，不扩到其他 expectation 目录。
- 新增 [`expectation/pass/tuning/launch_kernel_cost_func/__main__.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func/__main__.py)，把目录入口统一收口到 [`expectation.pass.tuning.launch_kernel_cost_func_compute_memory.__main__`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py)，只运行当前 `compute / memory` 合同。
- 新增 [`expectation/pass/tuning/launch_kernel_cost_func/_shared.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func/_shared.py)，提供当前 family 需要的 `run_case`、`raise_if_failures`、`run_ircheck_success` 与 `run_ircheck_failure`，让纯 worktree 场景不再依赖缺失的 `expectation.utils.case_runner`。
- 更新 [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py)，改为通过 `import_module("expectation.pass.tuning.launch_kernel_cost_func._shared")` 取当前 family helper，移除目录级 `sys.path` 注入与缺失 helper 依赖。
- 更新 [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../../../spec/pass/tuning/launch_kernel_cost_func.md)，把“旧目录只作历史证据 / 当前目录尚未入库”的旧表述收紧为“当前 tracked worktree 已补齐 `launch_kernel_cost_func` 目录入口，入口只承接当前 `compute / memory` 合同，不引回历史四 kind 子资产”。
验证：
- `cd /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 pytest -q test/pass/test_launch_kernel_cost_func.py test/pass/test_pass_registry.py test/dialect/test_tuner_dialect.py -ra` -> `56 passed, 1 warning`
- `cd /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 python3 -m py_compile expectation/pass/tuning/launch_kernel_cost_func/__main__.py expectation/pass/tuning/launch_kernel_cost_func/_shared.py expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py` -> 通过
- `cd /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 python3 - <<'PY' ... PY` -> `import-contract-ok`；已验证新目录入口只接到 `launch_kernel_cost_func_compute_memory.__main__`，且 `basic_all.py` 的 helper 已统一来自 [`expectation/pass/tuning/launch_kernel_cost_func/_shared.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func/_shared.py)
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 diff --check` -> 通过
- `rg -n "expectation\\.utils\\.case_runner|只读运行|路径占位" spec/pass/tuning/launch_kernel_cost_func.md expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py expectation/pass/tuning/launch_kernel_cost_func/__main__.py expectation/pass/tuning/launch_kernel_cost_func/_shared.py` -> 只保留当前文档里对历史四 kind 的说明，不再残留“当前入口仍未入库”或旧 helper 依赖。
Diff 反推自测：
- `pytest -q test/pass/test_launch_kernel_cost_func.py test/pass/test_pass_registry.py test/dialect/test_tuner_dialect.py -ra`
- `python3 -m py_compile expectation/pass/tuning/launch_kernel_cost_func/__main__.py expectation/pass/tuning/launch_kernel_cost_func/_shared.py expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py`
- `python3 - <<'PY' ... PY` 本地脚本：校验 `expectation.pass.tuning.launch_kernel_cost_func.__main__` 的 runner 指向当前 `compute_memory` 目录入口，并校验 `_shared.py` 的 case 汇总接口语义
合同验收资产（单列，不计入 Diff 反推自测）：
- `cd /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 python3 -m expectation.pass.tuning.launch_kernel_cost_func` -> `[RUN] compute_memory` / `[RUN] basic_all` / `[OK] launch-kernel-cost-func compute/memory expectation passed` / `[OK] launch-kernel-cost-func expectation passed`
自检：
- API / 边界：新目录入口只接到当前 `compute / memory` 合同，不把 `multi_kind.py`、`shared_callee_once.py` 或缺失的 `invalid_kind.py` 重新接回入口。
- 异常 / 兼容：`basic_all.py` 改回 `import_module(...)` 取 `_shared`，避开 Python 关键字 `pass` 带来的 dotted import 语法问题；纯 worktree 场景不再依赖主仓额外状态或额外 `PYTHONPATH`。
- 复用 / 维护性：case 汇总与 ircheck helper 收口到当前 family 的 [`_shared.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func/_shared.py)，避免 `compute_memory/basic_all.py` 再重复注入路径或依赖缺失的通用 helper。
- 冗余 / 测试有效性：本轮没有扩到无关 expectation family；公开 pytest 继续覆盖 pass / registry / dialect 公开合同，本地脚本覆盖这次目录入口与 helper 接线变化，expectation 入口验收单列记录。
结论：当前 `build` 已完成。`expectation.pass.tuning.launch_kernel_cost_func` 在纯 tracked worktree 场景下已恢复为可直接执行的目录入口，且只承接当前 `compute / memory` 合同；可以按 `TODO.md` 继续续到 `review`。

---
时间：2026-04-24 21:32 +0800
经办人：不要啊教练
任务：T-20260424-4781572d
任务目标：复核 `expectation.pass.tuning.launch_kernel_cost_func` 当前目录入口、`compute_memory` family helper 接线与直接关联 spec 边界是否已按本轮修复口径收口。
执行前阅读记录：已读 [`TODO.md`](../../../../../../TODO.md) 当前任务行，确认当前阶段为 `review`；已读计划书 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 中本轮修复任务说明、全局完成态与 expectation 合同验收摘要；已回读本记录中前序 blocker、架构补充口径和 build 自检，确认本轮只审当前目录入口、family helper 与直接关联 `spec`，不扩到旧四 kind 资产。
改动：本轮未修改实现、`spec`、测试或 `expectation`；只完成现场审查、复测与问题定位。
真实审查：
- 现场确认 [`expectation/pass/tuning/launch_kernel_cost_func/__main__.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func/__main__.py) 已把目录入口稳定接到 [`expectation.pass.tuning.launch_kernel_cost_func_compute_memory.__main__`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py)，纯 worktree 场景下 `python -m expectation.pass.tuning.launch_kernel_cost_func` 可直接运行，不再依赖主仓额外状态中的旧 package。
- 现场确认 [`expectation/pass/tuning/launch_kernel_cost_func/_shared.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func/_shared.py) 已把 `run_case` / `raise_if_failures` / `run_ircheck_success` / `run_ircheck_failure` 收口成当前 family helper，[`basic_all.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py) 已改为经 canonical package import 复用该 helper。
- 但 [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../../../spec/pass/tuning/launch_kernel_cost_func.md) 第 54、230 行仍把“当前 tracked worktree”写进公开合同描述。该 spec 应描述仓库当前稳定合同，而不是把 worktree 现场状态直接写入合同正文；否则后续合并出当前 worktree 语境后，这两处文字会变成不稳定、不可复用的环境化表述。
问题清单：
- `P2` 文件/接口：[`spec/pass/tuning/launch_kernel_cost_func.md:54`](../../../../../../spec/pass/tuning/launch_kernel_cost_func.md#L54) [`spec/pass/tuning/launch_kernel_cost_func.md:230`](../../../../../../spec/pass/tuning/launch_kernel_cost_func.md#L230)
  - 现象：公开合同用语仍写成“当前 tracked worktree 已补齐...”与“是当前 tracked worktree 的目录入口...”。
  - 风险：`spec` 把临时现场状态写成长期合同，后续在主线、其他 worktree 或归档场景下会留下环境化表述，降低合同的稳定性与可复用性。
  - 建议：把这两处收紧为仓库/目录入口的稳定合同描述，例如“当前仓库目录入口为 ...，只承接 compute/memory 合同”，不要再引用 `tracked worktree` 现场措辞。
  - 优先级：`P2`
漏洞排查结果：
- 输入校验绕过：未发现新增问题；目录入口仍只接 `compute / memory` 当前合同。
- 类型/形状绕过：未发现新增问题；本轮改动不改变 pass 或 dialect 语义。
- 边界越界：未发现新增问题；`__main__` 与 `_shared.py` 的接线范围仍限制在当前 family。
- 错误处理缺失：未发现新增问题；`run_case` / `raise_if_failures` 的失败聚合语义现场可复现。
- 状态污染：未发现新增问题；纯 worktree 场景下目录入口已可直接运行。
- 资源释放问题：未发现新增问题；本轮改动未引入持久资源。
可改进点：
- 当前唯一可执行改进点是把 `spec` 中的 `tracked worktree` 环境化表述改成稳定仓库合同表述；除此之外未发现新的额外问题。
验证：
- `cd /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 pytest -q test/pass/test_launch_kernel_cost_func.py test/pass/test_pass_registry.py test/dialect/test_tuner_dialect.py -ra` -> `56 passed, 1 warning`
- `cd /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 python3 -m py_compile expectation/pass/tuning/launch_kernel_cost_func/__main__.py expectation/pass/tuning/launch_kernel_cost_func/_shared.py expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py` -> 通过
- `cd /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 python3 - <<'PY' ... PY`（本轮现场脚本：校验目录入口 runner 指向 `expectation.pass.tuning.launch_kernel_cost_func_compute_memory.__main__`，并校验 `_shared.py` 的 `run_case` / `raise_if_failures` 失败聚合语义） -> `import-contract-ok`
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 diff --check` -> 通过
Diff 反推审查：
- 被审 diff 文件：[`expectation/pass/tuning/launch_kernel_cost_func/__main__.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func/__main__.py)、[`expectation/pass/tuning/launch_kernel_cost_func/_shared.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func/_shared.py)、[`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py)、[`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../../../spec/pass/tuning/launch_kernel_cost_func.md)、[`.gitignore`](../../../../../../.gitignore)
- 反推测试与核验证据：公开 pytest 56 passed；`py_compile` 覆盖新增入口与 helper；本轮本地脚本覆盖目录入口接线与 helper 失败聚合语义；`git diff --check` 通过。
- 未覆盖项：`.gitignore` 与 `spec` 主要通过文本审查核对；其中 `spec` 已发现环境化表述问题，故本轮不通过。
合同验收（单列，不计入 Diff 反推审查）：
- `cd /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 python3 -m expectation.pass.tuning.launch_kernel_cost_func` -> `[RUN] compute_memory` / `[RUN] basic_all` / `[OK] launch-kernel-cost-func compute/memory expectation passed` / `[OK] launch-kernel-cost-func expectation passed`
自检：已核对前序 build 记录包含 `执行前阅读记录`、`最小功能闭环`、`Diff 反推自测` 与 `自检`；已按实际 diff 逐项复测并检查特殊情况、完整性、维护性与测试有效性；本轮发现 1 个可直接执行的 `spec` 收口点，因此结论保持 `需修改`。
结论：需修改。当前目录入口、family helper 与合同验收都已收口，但 [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../../../spec/pass/tuning/launch_kernel_cost_func.md) 仍残留 “tracked worktree” 环境化表述，建议先把公开合同改回稳定仓库口径，再继续流转。

---
时间：2026-04-24 21:35 +0800
经办人：咯咯咯
任务：T-20260424-4781572d
任务目标：将 `spec/pass/tuning/launch_kernel_cost_func.md` 中目录入口的环境化表述收紧为稳定仓库合同口径，并保持入口只承接 `compute / memory` 合同
执行前阅读记录：已读 [`TODO.md`](../../../../../../TODO.md) 当前任务行，确认本轮为 `spec` 收口；已读计划书 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 中本轮修复任务、全局完成态与合同真源顺序；已回读当前记录里前序 `build` / 架构补充 / `review` 结论，确认唯一待收口点是 `spec/pass/tuning/launch_kernel_cost_func.md` 第 54、230 行的环境化措辞；已核对现场 [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../../../spec/pass/tuning/launch_kernel_cost_func.md)、[`test/pass/test_launch_kernel_cost_func.py`](../../../../../../test/pass/test_launch_kernel_cost_func.py)、[`kernel_gen/passes/tuning/launch_kernel_cost_func.py`](../../../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)、[`expectation/pass/tuning/launch_kernel_cost_func/__main__.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func/__main__.py)
最小功能闭环：本轮只改 `spec/pass/tuning/launch_kernel_cost_func.md` 与当前记录，把“当前 tracked worktree / 主仓额外状态”改成稳定仓库合同描述，明确仓库目录入口 `expectation/pass/tuning/launch_kernel_cost_func/` 只串接 `launch_kernel_cost_func_compute_memory/` 的 `compute / memory` case，不把历史四 kind 子资产重新写回当前入口
改动：1）更新 [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../../../spec/pass/tuning/launch_kernel_cost_func.md) 文档信息中的“最后一次更改”为 `咯咯咯`；2）将限制与边界中的“当前 tracked worktree 已补齐...”改成“当前仓库目录入口 ... 只承接 ... 当前两 kind 合同资产”；3）将测试章节中的“是当前 tracked worktree 的目录入口”改成“是仓库当前目录入口”，并保留“只运行 compute / memory 合同、不引回历史四 kind 子资产”的稳定合同口径
验证：
- `sed -n '1,90p' /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4/spec/pass/tuning/launch_kernel_cost_func.md` -> 核对文档信息与第 54-55 行限制边界已改为仓库合同表述
- `sed -n '220,236p' /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4/spec/pass/tuning/launch_kernel_cost_func.md` -> 核对合同验收资产段已改为仓库目录入口 + compute/memory case 表述
- `rg -n "tracked worktree|主仓额外状态|仓库当前目录入口|compute / memory" /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4/spec/pass/tuning/launch_kernel_cost_func.md` -> 不再命中 `tracked worktree` / `主仓额外状态`，并命中新的仓库合同表述
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 diff --check -- spec/pass/tuning/launch_kernel_cost_func.md` -> 通过
Diff 反推自测：本轮 diff 仅涉及 [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../../../spec/pass/tuning/launch_kernel_cost_func.md) 与当前记录文件；按 diff 反推执行文本核对与 `git diff --check`，结果通过；未运行 `pytest`，原因：本轮未改实现、测试或目录入口接线，只做 spec 与记录收口
合同验收（如适用）：未执行 `python3 -m expectation.pass.tuning.launch_kernel_cost_func`；该项继续作为合同验收资产单列，由下游接手人在最新现场按流程复核，不计入本轮 Diff 反推自测
自检：已读当前任务行、计划书、前序 build/review 记录与相关 spec/test/实现；未越权修改实现、测试、`.gitignore` 或 `expectation`；目录入口语义、历史四 kind 排除边界与 `compute / memory` 合同口径已改成稳定仓库表述；当前未发现新的文字歧义或与现有实现/测试相冲突的说明
结论：当前 spec 收口已完成，任务日志已写回对应 worktree 记录文件；下一步建议继续进入 `build` 或直接交还复核角色，确认最新 spec 与当前目录入口/公开 pytest/合同验收记录一致后再推进

---
时间：2026-04-24 22:06 +0800
经办人：不要啊教练
任务：T-20260424-4781572d
任务目标：复核 `spec/pass/tuning/launch_kernel_cost_func.md` 已去除环境化表述，且仓库目录入口仍只承接 `compute / memory` 合同，与当前 expectation 入口、公开 pytest 和前序记录保持一致。
执行前阅读记录：已读 [`TODO.md`](../../../../../../TODO.md) 当前任务行；已读计划书 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 中 `T-20260424-4781572d` 修复任务说明与 expectation 单列验收口径；已回读本记录中前序 `build`、`review` 与 `spec` 收口记录，确认本轮只复核 `spec/pass/tuning/launch_kernel_cost_func.md` 的环境化表述是否退场，以及仓库目录入口是否仍只承接 `compute / memory` 合同。
改动：本轮未修改实现、`spec`、测试或 `expectation`；只完成现场复核、Diff 反推审查与流程推进。
真实审查：
- 现场确认 [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../../../spec/pass/tuning/launch_kernel_cost_func.md) 第 54、230 行已去除 `tracked worktree`、`主仓额外状态` 等环境化表述，改为稳定仓库合同口径：当前仓库目录入口 [`expectation/pass/tuning/launch_kernel_cost_func/`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func/) 只承接 [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/) 的 `compute / memory` case。
- 现场确认历史四 kind 子资产仍被排除在当前入口之外，`multi_kind.py`、`shared_callee_once.py` 与缺失的 `invalid_kind.py` 均未被重新写回当前目录入口合同。
- 现场确认仓库目录入口、公开 pytest 与前序 build 记录保持一致，当前没有新增可执行问题。
问题清单：
- 本轮未发现新的可执行问题。
验证：
- `cd /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 pytest -q test/pass/test_launch_kernel_cost_func.py test/pass/test_pass_registry.py test/dialect/test_tuner_dialect.py -ra` -> `56 passed, 1 warning`
- `cd /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 python3 -m expectation.pass.tuning.launch_kernel_cost_func` -> `[RUN] compute_memory` / `[RUN] basic_all` / `[OK] launch-kernel-cost-func compute/memory expectation passed` / `[OK] launch-kernel-cost-func expectation passed`
- `cd /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 python3 - <<'PY' ... PY`（本轮文本边界脚本：确认 `spec/pass/tuning/launch_kernel_cost_func.md` 已不含 `tracked worktree` / `主仓额外状态`，并包含当前仓库目录入口只承接 `compute / memory` 合同的稳定表述） -> `spec-boundary-ok`
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4 diff --check` -> 通过
Diff 反推审查：
- 被审 diff 文件：[`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../../../spec/pass/tuning/launch_kernel_cost_func.md)
- 反推测试与核验证据：公开 pytest `56 passed`；文本边界脚本 `spec-boundary-ok`；`git diff --check` 通过。
- 本轮 `expectation` 只作合同验收资产单列，不计入 Diff 反推审查。
合同验收（单列，不计入 Diff 反推审查）：
- `python3 -m expectation.pass.tuning.launch_kernel_cost_func` -> 通过
自检：已按任务要求核对计划正文、前序记录、公开 pytest、spec 文本边界和目录入口合同；本轮未发现新的特殊情况、完整性缺口、维护性风险或测试有效性问题。
结论：通过。`spec/pass/tuning/launch_kernel_cost_func.md` 的环境化表述已收回为稳定仓库合同，仓库目录入口继续只承接 `compute / memory` 合同，且与当前 expectation 入口、公开 pytest 和前序记录保持一致。

---
时间：2026-04-24 21:39 +0800
经办人：李白
任务：T-20260424-4781572d（merge）
任务目标：在指定 worktree 内收口 `launch_kernel_cost_func` 目录入口与直接关联 `spec` 的 residual diff，并同步主线状态。
执行前阅读记录：
- 已读 [`TODO.md`](../../../../../../TODO.md) 当前任务行，确认本轮为 `merge`，目标是只收 `launch_kernel_cost_func` 目录入口与直接关联 `spec`。
- 已读计划书 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 中本任务的修复口径与合同验收摘要。
- 已读本记录前序 `build/review` 结论，确认已包含 `执行前阅读记录`、`最小功能闭环`、`自检`、`Diff 反推自测` 与 `Diff 反推审查`，且 `expectation` 只单列为合同验收资产。
真实收口过程：
- 已在 [`wt-20260424-main-npu-demo-final-repair-s4`](../../../../../../wt-20260424-main-npu-demo-final-repair-s4) 内执行 `timeout 60 git fetch origin && git rebase --autostash origin/main`，当前现场已重放到最新 `origin/main`，未出现冲突。
- 当前 residual diff 只收以下直接关联文件：
  - [`expectation/pass/tuning/launch_kernel_cost_func/__main__.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func/__main__.py)
  - [`expectation/pass/tuning/launch_kernel_cost_func/_shared.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func/_shared.py)
  - [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py`](../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py)
  - [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../../../spec/pass/tuning/launch_kernel_cost_func.md)
  - [`.gitignore`](../../../../../../.gitignore) 中为当前目录入口放行的最小规则
- 未把历史四 kind 子资产、无关 `expectation family` 或其他产品链路改动带入本次 merge。
最小校验：
- `python3 -m py_compile expectation/pass/tuning/launch_kernel_cost_func/__main__.py expectation/pass/tuning/launch_kernel_cost_func/_shared.py expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py` -> 通过
- `git diff --check` -> 通过
- 前序已审通过的直接证据沿用本记录：
  - `pytest -q test/pass/test_launch_kernel_cost_func.py test/pass/test_pass_registry.py test/dialect/test_tuner_dialect.py -ra` -> `56 passed, 1 warning`
  - `python3 -m expectation.pass.tuning.launch_kernel_cost_func` -> 通过（合同验收单列）
结论：
- 当前 worktree 已完成 merge 前同步确认与最小校验，可以按本轮 residual diff 直接提交、推送并执行 `-done`。
