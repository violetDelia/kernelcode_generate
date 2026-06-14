# T-20260614-8021d996 / multi-buffer-apply-fixed-reserved-before-auto

## 基本信息
- 任务 ID：`T-20260614-8021d996`
- 计划书：`ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md`
- 当前阶段：Pre-Execute local-only expectation 物化门禁
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260614-multi-buffer-apply-fixed-reserved-before-auto`
- 分支：`task/multi-buffer-apply-fixed-reserved-before-auto`
- 计划 staged blob：`100644 8eebfb0cc9bf3b136f9211b278d538eb6893b367 0`
- 计划 staged sha256：`cccbd3b3ccb5e18b042da57d332d1333124f1b2d46a7f9587a21950da6139d1b`

## 创建与暂停状态
- 管理员已按用户最终确认创建唯一计划级 execute。
- 当前保持未分发状态，未指派执行人。
- 本记录只覆盖架构师在目标 worktree 的 local-only expectation 物化门禁。
- 管理员、execute、review、archive_acceptance、merge 和替补仍不得修改、新建、移动、删除或重命名 `expectation/`；只能读取、运行、引用和记录。

## local-only expectation 物化
- 授权来源：用户确认 `multi_buffer_apply_fixed_reserved_before_auto` 计划可下发，计划要求创建后先由架构师在目标 worktree 物化 local-only expectation。
- 合同 manifest：以下 6 个 apply `.py` 文件是本计划当前合同 manifest。
- 运行支撑文件：`expectation/pass/multi_buffer/_path.py` 是这些 leaf 的 import-path helper，仅记录为 local-only 支撑文件，不作为本计划合同 leaf。

### sha256
- `expectation/pass/multi_buffer/_path.py`：`767b46f69b62b522e3ba1cdd2983f430ec6d08cd51cd74e25b6f54d86e5367f7`
- `expectation/pass/multi_buffer/apply/__main__.py`：`b3fe8c14b1f71ab4aa40fa40f05db8e518e02ac2e392c1bcb06ba66bd0fca32d`
- `expectation/pass/multi_buffer/apply/fixed_memory_stage.py`：`27a67b744563b6b12755319081f0239ea0f56289e3cf79a73a43b409a2e5abc6`
- `expectation/pass/multi_buffer/apply/dynamic_target_auto.py`：`9611bbf9939305c434479a2fbf4066b9ce5c768b2a627893d260e809bb39c42b`
- `expectation/pass/multi_buffer/apply/fixed_reserved_before_auto.py`：`5b125ff0d6b706b4e8414c01acd5f47be97565fcabed0e39edcaca18af38b0af`
- `expectation/pass/multi_buffer/apply/direct_use_boundary.py`：`a6f314d3042eeb2393d07ceab76c49bf17eae31b7ec29b9cdaeed7077ecc2ec4`
- `expectation/pass/multi_buffer/apply/existing_current_noop.py`：`d157ccc835028da2aa7bd68f846965558c6d4a292bb9e452f4a447cc0dcdd66d`

### ignored / tracked 状态
- `git check-ignore -v` 对上述 7 个 local-only 文件均命中 `.gitignore:21:expectation`。
- `git ls-files --stage -- expectation/pass/multi_buffer/_path.py expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade` 无输出。
- `git status --short --ignored --untracked-files=all -- expectation/pass/multi_buffer/_path.py expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade` 仅显示：
  - `!! expectation/pass/multi_buffer/_path.py`
  - `!! expectation/pass/multi_buffer/apply/__main__.py`
  - `!! expectation/pass/multi_buffer/apply/direct_use_boundary.py`
  - `!! expectation/pass/multi_buffer/apply/dynamic_target_auto.py`
  - `!! expectation/pass/multi_buffer/apply/existing_current_noop.py`
  - `!! expectation/pass/multi_buffer/apply/fixed_memory_stage.py`
  - `!! expectation/pass/multi_buffer/apply/fixed_reserved_before_auto.py`
  - 运行后新增 `!! expectation/pass/multi_buffer/apply/__pycache__/*`，按计划分类为非合同 cache。

### scope diff
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md` 无输出。
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md` 无输出。
- 当前 cached diff 仍保留计划候选，并将在本记录写入后额外包含本任务记录；`expectation/` 未进入 staged diff。

## 合同验收
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile expectation/pass/multi_buffer/apply/__main__.py expectation/pass/multi_buffer/apply/fixed_memory_stage.py expectation/pass/multi_buffer/apply/dynamic_target_auto.py expectation/pass/multi_buffer/apply/fixed_reserved_before_auto.py expectation/pass/multi_buffer/apply/direct_use_boundary.py expectation/pass/multi_buffer/apply/existing_current_noop.py`：通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.fixed_memory_stage`：通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.dynamic_target_auto`：通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.fixed_reserved_before_auto`：通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.direct_use_boundary`：通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.existing_current_noop`：通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply`：通过。

## 门禁结论
- Pre-Execute local-only expectation 物化门禁通过。
- 管理员可以按标准流程分发或恢复唯一计划级 execute `T-20260614-8021d996`。
- 分发后 execute 仍只能读取、运行、引用和记录 `expectation/`，不得修改、新建、移动、删除或重命名 `expectation/`。

## execute 主体记录

时间：2026-06-14 12:47 +0800
经办人：金铲铲大作战
任务：`T-20260614-8021d996` / `multi-buffer-apply-fixed-reserved-before-auto`
任务目标：按 `ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md` 完成 mixed fixed/auto fixed-reserved-before-auto 合同、tracked pytest、必要实现判断、Diff 反推自测、合同验收和记录闭环。

执行前阅读记录：
- 已读根 `AGENTS.md`、角色 prompt `agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/任务记录约定.md`、`agents/standard/expectation任务规则.md`。
- 已读计划书 `ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md` 全文，核对 S1/S2/S3/S4 小任务卡、公开 API 不变、禁止修改面和合同真源。
- 已读本任务记录前序 Pre-Execute local-only expectation 物化门禁、`expectation/pass/multi_buffer/apply/fixed_reserved_before_auto.py`、`expectation/pass/multi_buffer/apply/__main__.py`、`spec/pass/memory/multi_buffer.md`、`kernel_gen/passes/memory/multi_buffer.py`、`test/passes/memory/test_multi_buffer.py`、`test/passes/pipeline/test_npu_demo_lowering.py`。

计划内小任务卡核对：
- S1 已完成：`spec/pass/memory/multi_buffer.md` 在 Apply 合同中显式说明同组 mixed fixed/auto 必须先扣同 insertion scope / target loop / memory space 的 fixed reserved 和 same-scope live alloc reserved，再计算 auto group；测试矩阵新增 TC-MULTI-BUFFER-014A。
- S2 已完成：`test/passes/memory/test_multi_buffer.py` 新增 `test_multi_buffer_apply_fixed_reserved_before_auto_static_num`，通过公开 `MultiBufferApplyPass(target="npu_demo")` 构造 3 个 fixed `num="2"` 与 2 个 auto TSM candidate，断言 fixed ring `num=2`、auto ring `num=79`、不出现 `symbol.const 81`、不残留 `multi_buffer.`、不残留原 typed `dma.free`。
- S3 已判定无需实现修复：修改前后 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.fixed_reserved_before_auto` 均通过，新增 tracked pytest 也通过；`kernel_gen/passes/memory/multi_buffer.py` 已按现有 fixed reserved 汇总逻辑得到 `79`。
- S4 已完成：合同验收、pytest、private/KCE gate、diff check、敏感范围和 local-only expectation 状态核对均已记录。

最小功能闭环：
- 交付行为：补齐 spec 合同和 tracked pytest，把用户场景从 local-only expectation 落为可审查的 tracked 回归测试。
- 实现入口：`MultiBufferApplyPass.apply(ctx, module)`；本轮未改实现文件，因当前实现已满足 fixed-reserved before auto。
- 测试入口：新增 pytest 直接构造 apply-only 输入，设置当前公开三项属性 `multi_buffer.update_points/use_points/num` 和 `analysis.loop_id`，只通过公开 pass API 验证输出。
- 失败边界：若实现错误地未扣 fixed reserved，新用例会生成或保留 `81` 并无法满足两个 auto ring `num=79` 断言。

改动：
- `spec/pass/memory/multi_buffer.md`：补 mixed fixed/auto fixed-reserved-before-auto 合同说明，明确 `npu_demo` TSM 3 个 fixed 先占 `67584` bytes，auto group 应为 `79` 而不是 `81`；测试矩阵新增 TC-MULTI-BUFFER-014A。
- `test/passes/memory/test_multi_buffer.py`：新增 `test_multi_buffer_apply_fixed_reserved_before_auto_static_num`。
- 未修改 `kernel_gen/passes/memory/multi_buffer.py`；未修改、新建、移动、删除或重命名 `expectation/`。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_apply_fixed_reserved_before_auto_static_num`：exit=0，`1 passed, 25 deselected`；断言 3 个 fixed `num=2`、2 个 auto `num=79`、无 `81`、无 `multi_buffer.`、无原 typed `dma.free`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.fixed_reserved_before_auto`：exit=0，无输出；合同 leaf 通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply`：exit=0，无输出；apply 聚合合同通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/pipeline/test_npu_demo_lowering.py`：exit=0，`37 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`：exit=0，`8 passed`。
- `git diff --check && git diff --cached --check`：exit=0。

Diff 反推自测：
- 实际 diff 文件：`spec/pass/memory/multi_buffer.md`、`test/passes/memory/test_multi_buffer.py`。
- spec diff 反推：`git diff --check` / `git diff --cached --check` 均通过；文本新增 fixed-reserved before auto 合同和 TC-MULTI-BUFFER-014A。
- pytest diff 反推：新增用例定向跑通；全量 `test/passes/memory/test_multi_buffer.py test/passes/pipeline/test_npu_demo_lowering.py` 跑通。`expectation` 单列为合同验收，不计入 Diff 反推测试。

合同验收与 local-only expectation 核对：
- sha256 复查与 Pre-Execute manifest 一致：
  - `expectation/pass/multi_buffer/_path.py`：`767b46f69b62b522e3ba1cdd2983f430ec6d08cd51cd74e25b6f54d86e5367f7`
  - `expectation/pass/multi_buffer/apply/__main__.py`：`b3fe8c14b1f71ab4aa40fa40f05db8e518e02ac2e392c1bcb06ba66bd0fca32d`
  - `expectation/pass/multi_buffer/apply/fixed_memory_stage.py`：`27a67b744563b6b12755319081f0239ea0f56289e3cf79a73a43b409a2e5abc6`
  - `expectation/pass/multi_buffer/apply/dynamic_target_auto.py`：`9611bbf9939305c434479a2fbf4066b9ce5c768b2a627893d260e809bb39c42b`
  - `expectation/pass/multi_buffer/apply/fixed_reserved_before_auto.py`：`5b125ff0d6b706b4e8414c01acd5f47be97565fcabed0e39edcaca18af38b0af`
  - `expectation/pass/multi_buffer/apply/direct_use_boundary.py`：`a6f314d3042eeb2393d07ceab76c49bf17eae31b7ec29b9cdaeed7077ecc2ec4`
  - `expectation/pass/multi_buffer/apply/existing_current_noop.py`：`d157ccc835028da2aa7bd68f846965558c6d4a292bb9e452f4a447cc0dcdd66d`
- `git check-ignore -v` 对上述 7 个 local-only 文件均命中 `.gitignore:21:expectation`。
- `git ls-files --stage -- expectation/pass/multi_buffer/_path.py expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade` 无输出。
- `git status --short --ignored --untracked-files=all -- expectation/pass/multi_buffer/_path.py expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade` 仅显示本计划 apply manifest、`_path.py` 和运行生成的 `apply/__pycache__/*` 为 `!!` ignored local-only；`__pycache__` 归类为非合同 cache。

敏感范围核对：
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
- `expectation/pass/multi_buffer/apply` 未进入 staged/unstaged diff；`expectation/pass/multi_buffer/analysis` 与 `facade` 未进入本轮运行、diff 或验收范围。

减法检查：
- 新增 / 改动 private callable 清单：无。未新增下划线 helper；未改 `kernel_gen/passes/memory/multi_buffer.py`。
- 被替代旧逻辑及处理结果：实现已有 fixed reserved 汇总逻辑满足合同，本轮没有替换实现逻辑。
- 保留旧逻辑依据：合同 leaf、apply 聚合 expectation、新增 tracked pytest 和 full pytest 均证明现有实现会先扣 fixed reserved 并得到 `79`。
- 删除 / 未删除验证：`git diff --cached --name-status` 显示本轮仅计划书、任务记录、spec、test；无实现旧逻辑删除需求。

自检：
- 公开 API、registry pass name、option、默认值和公开错误文本均未改。
- 未跨文件调用非公开业务 helper；新增测试只通过公开 pass API 验证行为。
- 未修改 `.skills/`、`expectation/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`agents-list`。
- 新测试断言能区分错误实现：若未扣 fixed reserved，auto num 会落到 `81` 而非 `79`；同时断言临时属性和旧 free 生命周期被清除。
- 已检查遗漏、重复、注释准确性、复用、函数粒度、输入输出校验、资源、并发、性能和兼容性；本轮无实现变更，风险集中在测试覆盖和合同文本，已由新增用例和全量相关 pytest 覆盖。

结论：
- execute 主体完成，可进入 `review`；下一步按计划级链路执行 `execute -> review -> archive_acceptance -> merge/归档`，本轮不得进入 archive_acceptance 或 merge。

## execute -> review 标准流转补记

时间：2026-06-14 12:50 +0800
经办人：金铲铲大作战
任务：`T-20260614-8021d996` / `multi-buffer-apply-fixed-reserved-before-auto`
任务目标：记录本次 execute -> review 标准流转的实际命令、脚本输出、状态复查和敏感范围复查。

实际命令：
```bash
CODEX_MULTI_AGENTS_AGENTS_FILE=/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -next -task_id T-20260614-8021d996 -from "金铲铲大作战" -type review -message "review；任务目标：审查 T-20260614-8021d996 multi-buffer-apply fixed-reserved-before-auto 候选，核对 mixed fixed/auto 合同、spec、tracked pytest、必要实现判断、Diff 反推自测、expectation 只读合同验收、敏感范围和任务记录；计划级后续应 review -> archive_acceptance -> merge/归档，不得直接 merge；任务链记录：agents/codex-multi-agents/log/task_records/2026/24/20260614-multi-buffer-apply-fixed-reserved-before-auto.md。" -agents-list /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md -auto
```

完整脚本输出：
```text
OK: next T-20260614-8021d996
OK: replace 金铲铲大作战 状态
OK: auto-dispatch T-20260614-8021d996 -> 不要啊教练
OK: replace 不要啊教练 状态
OK: talk 金铲铲大作战 -> 不要啊教练 (不要啊教练)
OK: talk 金铲铲大作战 -> 神秘人 (神秘人)
```

TODO 复查：
- `/home/lfr/kernelcode_generate/TODO.md` 显示 `T-20260614-8021d996` 为 `review / 不要啊教练 / 进行中`。
- 同一 TODO 中另有 `T-20260613-56f5a699` 为 unrelated `review / 不要啊教练 / 暂停`，不属于本任务候选或流转范围。

agents-list 复查：
- `/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md` 显示 `不要啊教练 busy`。
- `/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md` 显示 `金铲铲大作战 free`。

talk.log 复查：
- `/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/talk.log` 尾部包含 `金铲铲大作战 -> 不要啊教练` 的任务交接消息，含 worktree、计划书、记录文件和 review 目标。
- `/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/talk.log` 尾部包含 `金铲铲大作战 -> 神秘人` 的管理员回报消息：`任务 T-20260614-8021d996 已完成当前阶段，已回到任务列表；新任务类型=review，已经指派给-> 不要啊教练。`

diff check：
- `git diff --check && git diff --cached --check`：exit=0。

敏感范围复查：
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
- `git status --short --ignored --untracked-files=all -- expectation/pass/multi_buffer/_path.py expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade` 仅显示 `expectation/pass/multi_buffer/_path.py`、apply manifest 6 个 `.py` 文件和运行生成的 `apply/__pycache__/*` 为 `!!` ignored local-only；未进入 staged/unstaged diff。
- `expectation/pass/multi_buffer/apply`、`expectation/pass/multi_buffer/analysis`、`expectation/pass/multi_buffer/facade` 未进入 tracked diff；analysis/facade 未进入本轮验收范围。

自检：
- 本补记只追加任务记录并暂存；未改实现、spec、test、计划验收结论或 `expectation/`。
- 本轮 execute 已流转到 review；未进入 `archive_acceptance` 或 `merge`。
- 当前 staged 候选为计划书、任务记录、`spec/pass/memory/multi_buffer.md`、`test/passes/memory/test_multi_buffer.py`；无敏感范围 diff。

结论：
- execute -> review 标准流转补记完成，等待 `不要啊教练` review 结论。

## review 审查记录

时间：2026-06-14 12:58 +0800
经办人：不要啊教练
任务：`T-20260614-8021d996` / `multi-buffer-apply-fixed-reserved-before-auto`
任务目标：审查 mixed fixed/auto fixed-reserved-before-auto 候选，核对 spec、tracked pytest、必要实现判断、Diff 反推自测、expectation 只读合同验收、敏感范围和任务记录；计划级后续只进入 `archive_acceptance`，不得直接 merge。

### 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260614-multi-buffer-apply-fixed-reserved-before-auto`
- 分支：`task/multi-buffer-apply-fixed-reserved-before-auto`
- `git fetch origin main --prune && git rev-parse HEAD && git rev-parse origin/main && git merge-base HEAD origin/main && git rev-list --left-right --count HEAD...origin/main`：
  - `HEAD = 031a1462c2095df98636b4605d38bd09b5f49c97`
  - `origin/main = 031a1462c2095df98636b4605d38bd09b5f49c97`
  - `merge-base = 031a1462c2095df98636b4605d38bd09b5f49c97`
  - ahead/behind = `0 0`
- 当前 staged diff：`ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md`、本任务记录、`spec/pass/memory/multi_buffer.md`、`test/passes/memory/test_multi_buffer.py`。
- unstaged tracked diff：无。
- 冲突 / 覆盖风险：未发现。

### findings

- 无阻断项。
- 无最小需改项。
- 无新增待用户确认项。

### 执行记录与流转核对

- 已核对 TODO：`T-20260614-8021d996` 为 `review / 不要啊教练 / 进行中`；另一个 `T-20260613-56f5a699` 为 unrelated `review / 不要啊教练 / 暂停`，未纳入本审查。
- 已核对 agents-list：`不要啊教练=busy`，`金铲铲大作战=free`。
- 已核对任务记录尾部 execute -> review 标准流转补记：包含实际 `-next -type review -auto` 命令、完整脚本输出、TODO / agents-list / talk 复查、`git diff --check` / `git diff --cached --check`、敏感范围空 diff、`expectation/pass/multi_buffer/apply` ignored local-only 未入 staged / unstaged diff、自检和未进入 `archive_acceptance` / `merge` 说明。
- 已核对 execute 主体记录：包含执行前阅读、计划内小任务卡、最小功能闭环、验证、Diff 反推自测、合同验收、敏感范围、减法检查和自检。

### 被审 diff 与结论

- `spec/pass/memory/multi_buffer.md`：Apply 合同新增 mixed fixed / auto fixed-reserved-before-auto 规则，明确同一 insertion scope / target loop / memory space 下先汇总 fixed backing 与 same-scope live alloc reserved，再计算 auto group；测试矩阵新增 `TC-MULTI-BUFFER-014A`，锁定 `npu_demo` TSM 静态场景 `79` 而非 `81`。
- `test/passes/memory/test_multi_buffer.py`：新增公开 pytest `test_multi_buffer_apply_fixed_reserved_before_auto_static_num`，用公开 `MultiBufferApplyPass(target="npu_demo")` 构造 3 个 fixed `num="2"` 与 2 个 auto 候选，断言 fixed ring `2`、auto ring `79`、无 `symbol.const 81`、无 `multi_buffer.`、无原 typed `dma.free`。
- `kernel_gen/passes/memory/multi_buffer.py` 未改；审查现有实现中 group key 覆盖 target loop / memory space / insertion block / insertion anchor，fixed 候选先累加 `fixed_reserved`，auto 分支再执行 `capacity - fixed_reserved - same_scope_reserved` 与 auto group unit 的 floordiv，和本轮合同一致；无需实现修改的判断有 tracked pytest 与 expectation 证据支撑。
- 公开 API：`MultiBufferApplyPass`、`MultiBufferPass`、registry pass name / options / 默认值 / 公开错误文本均未改。
- expectation：本轮未修改、新建、移动、删除或重命名 `expectation/`；只读运行和引用。

### Diff 反推审查

- 实际业务 diff 为 `spec/pass/memory/multi_buffer.md` 与 `test/passes/memory/test_multi_buffer.py`；反推测试覆盖新增合同文本和新增 pytest。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_apply_fixed_reserved_before_auto_static_num`：exit=0，`1 passed, 25 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/pipeline/test_npu_demo_lowering.py`：exit=0，`37 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`：exit=0，`8 passed`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile test/passes/memory/test_multi_buffer.py kernel_gen/passes/memory/multi_buffer.py`：exit=0。
- `git diff --check && git diff --cached --check`：exit=0。

### 合同验收

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.fixed_reserved_before_auto`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply`：exit=0。
- `sha256sum expectation/pass/multi_buffer/_path.py expectation/pass/multi_buffer/apply/__main__.py expectation/pass/multi_buffer/apply/fixed_memory_stage.py expectation/pass/multi_buffer/apply/dynamic_target_auto.py expectation/pass/multi_buffer/apply/fixed_reserved_before_auto.py expectation/pass/multi_buffer/apply/direct_use_boundary.py expectation/pass/multi_buffer/apply/existing_current_noop.py` 与 Pre-Execute manifest 一致：
  - `_path.py` = `767b46f69b62b522e3ba1cdd2983f430ec6d08cd51cd74e25b6f54d86e5367f7`
  - `__main__.py` = `b3fe8c14b1f71ab4aa40fa40f05db8e518e02ac2e392c1bcb06ba66bd0fca32d`
  - `fixed_memory_stage.py` = `27a67b744563b6b12755319081f0239ea0f56289e3cf79a73a43b409a2e5abc6`
  - `dynamic_target_auto.py` = `9611bbf9939305c434479a2fbf4066b9ce5c768b2a627893d260e809bb39c42b`
  - `fixed_reserved_before_auto.py` = `5b125ff0d6b706b4e8414c01acd5f47be97565fcabed0e39edcaca18af38b0af`
  - `direct_use_boundary.py` = `a6f314d3042eeb2393d07ceab76c49bf17eae31b7ec29b9cdaeed7077ecc2ec4`
  - `existing_current_noop.py` = `d157ccc835028da2aa7bd68f846965558c6d4a292bb9e452f4a447cc0dcdd66d`
- `git check-ignore -v` 对上述 7 个 local-only 文件均命中 `.gitignore:21:expectation`。
- `git ls-files --stage -- expectation/pass/multi_buffer/_path.py expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade`：无输出。
- `git status --short --ignored --untracked-files=all -- expectation/pass/multi_buffer/_path.py expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade`：仅显示 `_path.py`、apply manifest 6 个 `.py` 文件和 `apply/__pycache__/*` 为 `!!` ignored local-only；`__pycache__` 为非合同 cache。

### 敏感范围

- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md kernel/dump`：无输出。
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md kernel/dump`：无输出。
- `expectation/pass/multi_buffer/apply`、`analysis`、`facade` 未进入 staged / unstaged diff；`.skills`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md`、`agents-list` 和 `kernel/dump` 均无本任务 diff。

### 减法审查

- 本轮没有实现 diff；没有被替代的生产 helper 或旧入口需要删除。
- execute 记录中“无需实现修复”的保留依据充分：定向 pytest、相关全量 pytest、`fixed_reserved_before_auto` leaf 与 apply 聚合 expectation 均通过，证明现有实现已先扣 fixed reserved 并得到 `79`。
- 新增 / 改动 private callable：无。`git diff --cached -U0 -- test/passes/memory/test_multi_buffer.py spec/pass/memory/multi_buffer.md` 未新增 `def _...`、`hasattr/getattr/callable(getattr(...))`、跨文件 private import 或 `object` 掩盖签名。
- 新测试调用同文件既有测试辅助与公开 `MultiBufferApplyPass`，未直连生产非公开 API。

### 自检

- 已逐项读取实际 diff、计划书、execute 记录、execute -> review 标准流转补记、相关 spec / test / 实现和 local-only expectation 状态。
- 已核对 latest main 基线、公开 API、expectation 权限、敏感范围、Diff 反推审查、测试有效性、减法审查和 private/KCE gate。
- 新 pytest 会在错误实现未扣 fixed reserved 时落到 `81` 并失败；同时断言临时属性和原 `dma.free` 清理，测试有效。
- 未修改实现、spec、测试、计划书或 `expectation/`；本段仅追加 review 记录。
- 未进入 merge；计划级 review 通过后仅允许流转 `archive_acceptance`。

### 结论

通过。`T-20260614-8021d996` execute 候选满足 review 目标，无可执行返工项；下一步按计划级链路流转 `archive_acceptance`，不得直接 merge。

## review -> archive_acceptance 标准流转记录

时间：2026-06-14 13:00 +0800
经办人：不要啊教练
任务：`T-20260614-8021d996` / `review -> archive_acceptance`
任务目标：记录本次 review 通过后实际 `-next -type archive_acceptance -auto` 流转、完整脚本输出、TODO / agents-list / talk 复查、diff check、敏感范围空 diff和自检；计划级链路进入 `archive_acceptance`，不进入 merge。

实际命令：

```bash
bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file /home/lfr/kernelcode_generate/TODO.md \
  -next \
  -task_id T-20260614-8021d996 \
  -from "不要啊教练" \
  -type archive_acceptance \
  -message "archive_acceptance；任务目标：核对 T-20260614-8021d996 / multi-buffer-apply-fixed-reserved-before-auto review 通过后的计划书入档验收与可归档性；重点复核 latest main 同步、计划书回写、mixed fixed/auto fixed-reserved-before-auto 合同、tracked pytest、必要实现判断、expectation 只读合同验收、Diff 反推审查、减法审查、private/KCE gate、敏感范围和任务记录完整性。任务链记录：agents/codex-multi-agents/log/task_records/2026/24/20260614-multi-buffer-apply-fixed-reserved-before-auto.md。计划级链路 execute -> review -> archive_acceptance -> merge/归档；archive_acceptance 完成前不得进入 merge。" \
  -agents-list /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
  -auto
```

完整脚本输出：

```text
OK: next T-20260614-8021d996
OK: replace 不要啊教练 状态
OK: auto-dispatch T-20260614-8021d996 -> 提莫炖蘑菇
OK: replace 提莫炖蘑菇 状态
OK: talk 不要啊教练 -> 提莫炖蘑菇 (提莫炖蘑菇)
OK: talk 不要啊教练 -> 神秘人 (神秘人)
```

### 流转后复查

- TODO 复查：`/home/lfr/kernelcode_generate/TODO.md` 显示 `T-20260614-8021d996` 为 `archive_acceptance / 提莫炖蘑菇 / 进行中`；unrelated `T-20260613-56f5a699` 仍为 `review / 不要啊教练 / 暂停`。
- agents-list 复查：`/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md` 显示 `提莫炖蘑菇=busy`，`不要啊教练=free`，`金铲铲大作战=free`。
- talk.log 复查：尾部包含 `@不要啊教练向@提莫炖蘑菇发起会话` 的 archive_acceptance 交接消息，写明 worktree、计划书、记录文件和计划级链路；尾部也包含 `@不要啊教练向@神秘人发起会话`，说明任务已完成当前阶段、已进入计划书入档验收并指派给 `提莫炖蘑菇`。

### diff check 与敏感范围

- `git diff --check && git diff --cached --check`：exit=0。
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md kernel/dump`：无输出。
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md kernel/dump`：无输出。
- `git status --short --ignored --untracked-files=all -- expectation/pass/multi_buffer/_path.py expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade`：仅显示 `_path.py`、apply manifest 6 个 `.py` 文件和 `apply/__pycache__/*` 为 `!!` ignored local-only；`expectation/pass/multi_buffer/apply` 未进入 staged / unstaged diff。
- 当前 staged 候选：`ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md`、本任务记录、`spec/pass/memory/multi_buffer.md`、`test/passes/memory/test_multi_buffer.py`。

### 自检

- review 正文已写明通过结论、验证、Diff 反推审查、合同验收、减法审查、敏感范围和自检。
- 本段只补 review -> archive_acceptance 标准流转记录；`TODO.md` 与 agents-list 状态变化来自标准脚本，未手工修改状态文件。
- 未修改实现、spec、test、计划书或 `expectation/`；未执行 merge、提交、推送或归档。
- 当前任务已为 `archive_acceptance / 提莫炖蘑菇 / 进行中`；下一阶段应先完成计划书入档验收，不得提前进入 merge。

结论：T-20260614-8021d996 已按计划级标准链路从 review 流转到 archive_acceptance，责任人为 `提莫炖蘑菇`；不要啊教练已释放为 free。

## archive_acceptance / 计划书入档验收

时间：2026-06-14 13:10 +0800
经办人：提莫炖蘑菇
任务：`T-20260614-8021d996` / `multi-buffer-apply-fixed-reserved-before-auto`
任务目标：核对 review 通过后的计划书入档验收与可归档性，复核 latest main 同步、计划书回写、mixed fixed / auto fixed-reserved-before-auto 合同、tracked pytest、必要实现判断、expectation 只读合同验收、Diff 反推审查、减法审查、private / KCE gate、敏感范围和任务记录完整性。

### 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260614-multi-buffer-apply-fixed-reserved-before-auto`
- 分支：`task/multi-buffer-apply-fixed-reserved-before-auto`
- `git fetch origin main --prune && git rev-parse HEAD && git rev-parse origin/main && git merge-base HEAD origin/main && git rev-list --left-right --count HEAD...origin/main`：
  - `HEAD = 031a1462c2095df98636b4605d38bd09b5f49c97`
  - `origin/main = 031a1462c2095df98636b4605d38bd09b5f49c97`
  - `merge-base = 031a1462c2095df98636b4605d38bd09b5f49c97`
  - ahead/behind = `0 0`
- 当前 staged 候选：`ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md`、本任务记录、`spec/pass/memory/multi_buffer.md`、`test/passes/memory/test_multi_buffer.py`。
- unstaged tracked diff：无。
- 冲突 / 覆盖风险：未发现。

### 计划书回写

- 已在 `ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md` 的 `计划书入档验收 / 复验 / 修复复核记录` 章节回写本次 archive_acceptance 结论。
- 回写内容：当前状态改为已完成 archive_acceptance 且结论通过；补齐结论人、验证基线、执行目录、latest main 同步结果、合入候选、合同验收摘要、expectation 权限核对摘要和通过摘要。
- 本轮计划书回写仅限入档验收章节；未修改计划任务目标、公开 API 设计、执行规则、小任务卡或 expectation 授权 scope。

### 任务记录与流转完整性

- 已核对 Pre-Execute local-only expectation 物化门禁记录：包含架构师物化 scope、manifest hash、ignored / ls-files / scope diff 核对和合同验收。
- 已核对 execute 主体记录：包含执行前阅读、最小功能闭环、Diff 反推自测、合同验收、减法检查、自检和结论。
- 已核对 execute -> review 标准流转补记：管理员已确认通过，记录尾部包含实际 `-next -type review -auto` 命令、完整输出、TODO / agents-list / talk 复查、diff check、敏感范围空 diff、expectation ignored local-only 未入 diff、自检和未进入 archive_acceptance / merge 说明。
- 已核对 review 正文：结论通过，已复核 mixed fixed / auto 合同、spec、tracked pytest、必要实现判断、Diff 反推自测、expectation 只读合同验收、敏感范围和任务记录。
- 已核对 review -> archive_acceptance 标准流转补记：管理员已确认通过，记录尾部包含实际 `-next -type archive_acceptance -auto` 命令、完整输出、TODO 复查 `archive_acceptance / 提莫炖蘑菇 / 进行中`、agents-list 复查 `提莫炖蘑菇 busy / 不要啊教练 free`、talk 交接与回报、diff check、敏感范围空 diff、expectation ignored local-only 未入 staged / unstaged diff、自检和未进入 merge 说明。

### 被验 diff 与可归档性

- `spec/pass/memory/multi_buffer.md`：补齐 Apply 合同中的 mixed fixed / auto fixed-reserved-before-auto 规则，明确同一 insertion scope / target loop / memory space 下先汇总 fixed backing 与 same-scope live alloc reserved，再计算 auto group；测试矩阵新增 `TC-MULTI-BUFFER-014A`，锁定 `npu_demo` TSM 静态场景 `79` 而非 `81`。
- `test/passes/memory/test_multi_buffer.py`：新增公开 pytest `test_multi_buffer_apply_fixed_reserved_before_auto_static_num`，用公开 `MultiBufferApplyPass(target="npu_demo")` 构造 3 个 fixed `num="2"` 与 2 个 auto 候选，断言 fixed ring `2`、auto ring `79`、5 个 current / advance、无原 typed `dma.free`、无 `multi_buffer.`、无 `symbol.const 81`，并 `module.verify()`。
- `kernel_gen/passes/memory/multi_buffer.py`：无 diff。核对现有实现中 old pair 路径 `fixed_reserved_by_space` 后扣 reserved 再算 auto group，loop staging group 路径先汇总 `fixed_reserved` / same-scope reserved，再执行 `capacity - reserved` 与 group unit floordiv；无需实现修改的判断由 tracked pytest 与 expectation 支撑。
- 公开 API：`MultiBufferApplyPass`、`MultiBufferPass`、`from_options`、`apply`、registry pass name / option、公开错误语义均未改。
- 可归档性：计划书、任务记录、spec、pytest 为当前 staged 候选；expectation 为 ignored local-only，不进入提交候选；未发现需回 execute 的阻断项。

### Diff 反推审查

- 实际业务 diff：`spec/pass/memory/multi_buffer.md` 与 `test/passes/memory/test_multi_buffer.py`；计划书与任务记录为流程 / 验收记录。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_apply_fixed_reserved_before_auto_static_num`：exit=0，`1 passed, 25 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/pipeline/test_npu_demo_lowering.py`：exit=0，`37 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`：exit=0，`8 passed`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile test/passes/memory/test_multi_buffer.py kernel_gen/passes/memory/multi_buffer.py`：exit=0。
- `git diff --check && git diff --cached --check`：exit=0。
- 测试有效性：新增 pytest 在未扣 fixed reserved 时会产生 `81` 并触发 `assert "symbol.const 81" not in module_text` / ring num 断言失败；同时检查临时属性和 typed free 清理。

### 合同验收

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.fixed_reserved_before_auto`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply`：exit=0。
- expectation 仅作为合同验收资产单列，不替代 Diff 反推 pytest。

### expectation 权限与敏感范围

- `sha256sum expectation/pass/multi_buffer/_path.py expectation/pass/multi_buffer/apply/__main__.py expectation/pass/multi_buffer/apply/fixed_memory_stage.py expectation/pass/multi_buffer/apply/dynamic_target_auto.py expectation/pass/multi_buffer/apply/fixed_reserved_before_auto.py expectation/pass/multi_buffer/apply/direct_use_boundary.py expectation/pass/multi_buffer/apply/existing_current_noop.py`：
  - `_path.py` = `767b46f69b62b522e3ba1cdd2983f430ec6d08cd51cd74e25b6f54d86e5367f7`
  - `__main__.py` = `b3fe8c14b1f71ab4aa40fa40f05db8e518e02ac2e392c1bcb06ba66bd0fca32d`
  - `fixed_memory_stage.py` = `27a67b744563b6b12755319081f0239ea0f56289e3cf79a73a43b409a2e5abc6`
  - `dynamic_target_auto.py` = `9611bbf9939305c434479a2fbf4066b9ce5c768b2a627893d260e809bb39c42b`
  - `fixed_reserved_before_auto.py` = `5b125ff0d6b706b4e8414c01acd5f47be97565fcabed0e39edcaca18af38b0af`
  - `direct_use_boundary.py` = `a6f314d3042eeb2393d07ceab76c49bf17eae31b7ec29b9cdaeed7077ecc2ec4`
  - `existing_current_noop.py` = `d157ccc835028da2aa7bd68f846965558c6d4a292bb9e452f4a447cc0dcdd66d`
- `git check-ignore -v` 对上述 7 个文件均命中 `.gitignore:21:expectation`。
- `git ls-files --stage -- expectation/pass/multi_buffer/_path.py expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade`：无输出。
- `git status --short --ignored --untracked-files=all -- expectation/pass/multi_buffer/_path.py expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade`：仅显示 `_path.py`、apply manifest 6 个 `.py` 文件和 `apply/__pycache__/*` 为 `!!` ignored local-only；`__pycache__` 为非合同 cache。
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md kernel/dump`：无输出。
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md kernel/dump`：无输出。

### 减法审查

- 本轮 archive_acceptance 仅回写计划书入档验收章节并追加任务记录；没有实现 / spec / test 代码改动。
- execute 候选没有实现 diff；没有被替代的生产 helper、旧入口或旧文案需要删除。
- 现有实现保留依据充分：old pair 与 loop staging group 路径已有 fixed reserved 汇总和 reserved 扣减逻辑，新增 pytest、全量 memory/pipeline pytest 与 local-only expectation 均通过。
- 本轮新增 / 改动 private callable：无。`git diff --cached -U0 -- spec/pass/memory/multi_buffer.md test/passes/memory/test_multi_buffer.py` 未新增 `def _...`、跨文件 private import、`hasattr/getattr/callable(getattr(...))` 或 `object` 掩盖签名。
- 新增测试仅调用同测试文件内既有 test helper 与公开 `MultiBufferApplyPass`，未直连生产非公开 API。

### 自检

- 已按 archive_acceptance 职责核对 latest main 同步现场、计划书回写、mixed fixed / auto fixed-reserved-before-auto 合同、tracked pytest、必要实现判断、expectation 只读合同验收、Diff 反推审查、减法审查、private / KCE gate、敏感范围和任务记录完整性。
- 本轮只修改计划书入档验收章节与任务记录；未修改实现、spec、测试、`expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md`、`TODO.md`、`DONE.md`、agents-list 或 `kernel/dump`。
- 未执行 merge、提交、推送、归档或清理；archive_acceptance 通过后只按标准脚本续接 `merge/归档`。

### 结论

通过。`T-20260614-8021d996` 已满足计划书入档验收与可归档性要求，无阻断项、无最小需改项、无新增待确认项；下一步按计划级链路流转 `merge/归档`，不得由 review / archive_acceptance 角色直接执行合并。

## archive_acceptance -> merge 标准流转记录

时间：2026-06-14 13:15 +0800
经办人：提莫炖蘑菇
任务：`T-20260614-8021d996` / `archive_acceptance -> merge`
任务目标：记录本次计划书入档验收通过后实际 `-next -type merge -auto` 流转、完整脚本输出、TODO / agents-list / talk 复查、diff check、敏感范围空 diff、expectation ignored local-only 状态和自检；只交接给 merge 角色，不执行 merge、提交、推送、归档或清理。

实际命令：

```bash
bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file /home/lfr/kernelcode_generate/TODO.md \
  -next \
  -task_id T-20260614-8021d996 \
  -from "提莫炖蘑菇" \
  -type merge \
  -message "merge；任务目标：合入已通过 execute、review 与 archive_acceptance 的 T-20260614-8021d996 / multi-buffer-apply-fixed-reserved-before-auto staged 改动、计划书入档验收记录和任务记录；合入前复核 latest main、计划书回写、mixed fixed/auto fixed-reserved-before-auto 合同、tracked pytest、必要实现判断、expectation 只读合同验收、Diff 反推审查、减法审查、private/KCE gate、敏感范围空 diff和任务记录完整性；不得修改 expectation 本体，不得顺手改实现；按合并规范同批提交/推送计划书、任务记录、spec 与测试，完成后执行 -done 与 done_plan 归档并清理对应 worktree/branch。任务链记录：agents/codex-multi-agents/log/task_records/2026/24/20260614-multi-buffer-apply-fixed-reserved-before-auto.md。" \
  -agents-list /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
  -auto
```

完整脚本输出：

```text
OK: next T-20260614-8021d996
OK: replace 提莫炖蘑菇 状态
OK: auto-dispatch T-20260614-8021d996 -> 李白
OK: replace 李白 状态
OK: talk 提莫炖蘑菇 -> 李白 (李白)
OK: talk 提莫炖蘑菇 -> 神秘人 (神秘人)
```

### 流转后复查

- TODO 复查：`/home/lfr/kernelcode_generate/TODO.md` 显示 `T-20260614-8021d996` 为 `merge / 李白 / 进行中`，任务目标为合入已通过 execute、review 与 archive_acceptance 的 staged 改动、计划书入档验收记录和任务记录。
- agents-list 复查：`/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md` 显示 `李白=busy`、`提莫炖蘑菇=free`、`不要啊教练=free`。
- talk.log 复查：尾部包含 `@提莫炖蘑菇向@李白发起会话` 的 merge 交接消息，写明 worktree、计划书、记录文件、合并前复核重点和不得修改 expectation / 不得顺手改实现；尾部也包含 `@提莫炖蘑菇向@神秘人发起会话`，说明任务已完成当前阶段、已回到任务列表并指派给 `李白`。

### diff check 与敏感范围

- `git diff --check && git diff --cached --check`：exit=0。
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md kernel/dump`：无输出。
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md kernel/dump`：无输出。
- `git status --short --ignored --untracked-files=all -- expectation/pass/multi_buffer/_path.py expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade`：仅显示 `_path.py`、apply manifest 6 个 `.py` 文件和 `apply/__pycache__/*` 为 `!!` ignored local-only；`expectation/pass/multi_buffer/apply` 未进入 staged / unstaged diff。
- 当前 staged 候选：`ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md`、本任务记录、`spec/pass/memory/multi_buffer.md`、`test/passes/memory/test_multi_buffer.py`。

### 自检

- archive_acceptance 正文已写明通过结论、latest main 同步、计划书回写、合同验收、Diff 反推审查、减法审查、private / KCE gate、敏感范围和任务记录完整性。
- 本段只记录实际 archive_acceptance -> merge 标准流转；任务状态由标准脚本完成，未手工修改 `TODO.md` 或 agents-list。
- 本次补记仅追加任务记录；未改实现、spec、测试或计划验收结论，未修改 `expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md`、`DONE.md`、agents-list 或 `kernel/dump`。
- 未执行 merge、提交、推送、归档或清理。

结论：T-20260614-8021d996 已按计划级链路从 archive_acceptance 流转到 `merge / 李白 / 进行中`；提莫炖蘑菇已释放为 free。

## merge / 归档记录

时间：2026-06-14 13:20 +0800
经办人：李白
任务：`T-20260614-8021d996` / `multi-buffer-apply-fixed-reserved-before-auto`
任务目标：合入已通过 execute、review 与 archive_acceptance 的 spec / 测试 / 任务记录，并将计划书同批归档到 `done_plan/2026`。

### latest main 与合入来源

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260614-multi-buffer-apply-fixed-reserved-before-auto`
- 来源分支：`task/multi-buffer-apply-fixed-reserved-before-auto`
- `git fetch origin main --prune && git rev-parse HEAD && git rev-parse origin/main && git merge-base HEAD origin/main && git rev-list --left-right --count HEAD...origin/main`：
  - `HEAD = 031a1462c2095df98636b4605d38bd09b5f49c97`
  - `origin/main = 031a1462c2095df98636b4605d38bd09b5f49c97`
  - `merge-base = 031a1462c2095df98636b4605d38bd09b5f49c97`
  - ahead / behind = `0 0`
- latest main 同步结论：无待合并提交，无冲突或覆盖风险。

### 同批合入范围

- 计划书原路径：`ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md`
- 计划书归档目标：`agents/codex-multi-agents/log/task_records/done_plan/2026/multi_buffer_apply_fixed_reserved_before_auto.md`
- 归档动作：本次 merge 阶段执行 `git mv`，最终 staged 候选不再包含 `ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md`，计划正文将以 done_plan 路径同批合入。
- 最终待提交范围：
  - `A agents/codex-multi-agents/log/task_records/2026/24/20260614-multi-buffer-apply-fixed-reserved-before-auto.md`
  - `A agents/codex-multi-agents/log/task_records/done_plan/2026/multi_buffer_apply_fixed_reserved_before_auto.md`
  - `M spec/pass/memory/multi_buffer.md`
  - `M test/passes/memory/test_multi_buffer.py`
- 未纳入范围：`expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md`、`TODO.md`、`DONE.md`、`agents/codex-multi-agents/agents-lists.md`、`kernel/dump`。

### 验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_apply_fixed_reserved_before_auto_static_num`：exit=0，`1 passed, 25 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/pipeline/test_npu_demo_lowering.py`：exit=0，`37 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`：exit=0，`8 passed`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile test/passes/memory/test_multi_buffer.py kernel_gen/passes/memory/multi_buffer.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.fixed_reserved_before_auto`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply`：exit=0。
- `git diff --check && git diff --cached --check`：exit=0。
- 敏感范围核对：
  - `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md kernel/dump`：无输出。
  - `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md kernel/dump`：无输出。
- `expectation/pass/multi_buffer/_path.py` 与 `expectation/pass/multi_buffer/apply/*.py` 仍为 ignored local-only；`expectation/pass/multi_buffer/apply/__pycache__/*` 为 ignored cache，均未进入 staged / unstaged diff。

### 冲突处理与剩余风险

- 冲突处理：无冲突；merge 阶段未修改实现、spec、测试内容，未触碰 `expectation/` 本体。
- 公开 API：本次合入未新增、删除、重命名公开 API，未改变 pass name / option、公开错误语义或工具入口。
- 剩余风险：本轮按计划级验收复跑任务相关 pytest、合同 expectation、private / KCE 和 diff check，未运行全仓 pytest；pytest 中的 xdsl `DeprecationWarning` 为既有环境告警，不影响本次断言通过。

结论：T-20260614-8021d996 满足计划级 merge / 归档条件；合并记录、任务记录、计划书 done_plan 归档、spec 与测试将同批提交并推送，随后执行 `-done` 与 `-done-plan`。
