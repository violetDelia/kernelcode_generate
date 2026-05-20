# T-20260520 runtime_trance_block_logs

## 2026-05-20 管理员下发前置记录

- 经办人：神秘人
- 计划书：`ARCHITECTURE/plan/runtime_trance_block_logs_green_plan.md`
- 任务目标：把 runtime `TRANCE` 函数调用日志从旧单文件改为 `dump_dir/<kernel_name>/trance/block_0000.log`、`block_0001.log` 等 block 级落盘；`dsl_cost_run` 固定 stdout-only。
- latest main：`HEAD=origin/main=merge-base=8a73d06b37ab9417d5b41b397f70b752395c8787`，`ahead/behind=0/0`。
- worktree：`/home/lfr/kernelcode_generate/wt-20260520-runtime-trance-block-logs`
- branch：`task/runtime-trance-block-logs`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/20/20260520-runtime-trance-block-logs.md`

### 并行 / 依赖判断

- 当前 TODO 无进行中任务、无任务列表残留。
- 本计划可独立下发唯一 execute，不设置硬依赖。
- 与其它任务不存在当前 TODO 级重叠；后合入者仍需按计划重跑并确认 latest main。

### 禁止修改面与合同口径

- `expectation/`、`.skills/`、`agents/standard/**` 必须空 diff。
- execute / review / admin / merge 不得复制、新建、同步、修改或删除 `expectation/`。
- 任务记录必须与 spec / include / compiler / test 同批进入 review、终验和 merge。

## 2026-05-20 execute 记录

时间：2026-05-20 15:40
经办人：睡觉小分队
任务：T-20260520-e0fbce33 / runtime_trance_block_logs
任务目标：将 runtime TRANCE 函数调用日志改为 `dump_dir/<kernel_name>/trance/block_0000.log`、`block_0001.log` 等 block 级落盘，并让 `dsl_cost_run` 固定 stdout-only。

改动：
- `kernel_gen/execute_engine/compiler.py`
  - runtime trance 编译宏改为注入 `KG_TRANCE_DIR_PATH`，`KG_TRANCE_FILE_PATH` 固定空字符串。
  - `TRANCE` 启用且存在 block trace 目录时，entry shim 不再输出顶层 stdout trace，block 文件模式由后端 launch 承接。
- `kernel_gen/tools/dsl_run.py`
  - `dsl_run(...)` 在写完 kernel 级 IR/source 后，将 runtime trance 编译目录切回 root，用于生成 `dump_dir/<kernel_name>/trance`。
  - `dsl_cost_run(...)` 在编译 cost wrapper 前显式清空 dump_dir，确保 runtime trance 只保留 stdout，不生成 block 文件。
- `include/api/Trance.h` / `include/npu_demo/Trance.h`
  - 新增并实现 `prepare_block_trace_dir(...)`、`ScopedBlockTranceSink(...)`，block trace 目录清理、文件命名、header 写入和线程局部 sink 安装全部收口在 trace 模块。
- `include/npu_demo/Arch.h`
  - `launch(...)` 在 `TRANCE` block 目录模式下只调用 trace 公开入口，按 block worker 写入 `block_XXXX.log`，stdout 模式保持原有行为。
- `spec/core/config.md`、`spec/tools/dsl_run.md`、`spec/execute_engine/execute_engine_target.md`、`spec/include/api/Trance.md`、`spec/include/api/Arch.md`、`spec/include/npu_demo/npu_demo.md`
  - 同步 block trace 目录口径、`dsl_cost_run` stdout-only 口径、公开宏 `KG_TRANCE_DIR_PATH`、block 文件清理与验收条目。
- 测试：
  - `test/execute_engine/test_compile.py`
  - `test/tools/test_dsl_run.py`
  - `test/tools/test_dsl_cost_run.py`
  - `test/include/api/test_trance.py`
  - `test/include/npu_demo/test_runtime_launch.py`

执行前阅读：
- 已读任务记录前置记录、`ARCHITECTURE/plan/runtime_trance_block_logs_green_plan.md`、根目录 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`。
- 已核对最新 TODO 中本任务处于 `execute`，worktree 为 `/home/lfr/kernelcode_generate/wt-20260520-runtime-trance-block-logs`，敏感目录门禁要求 `expectation/.skills/agents/standard` 候选 diff 为空。

最小功能闭环：
- `dsl_run(...)` 在 `set_trance_enabled(True)` 且 `set_dump_dir(tmp_path)` 时，落盘到 `tmp_path/<kernel_name>/trance/block_0000.log` 等 block 文件。
- `npu_demo::launch<2, 1, 1, 0>(...)` 在 block 目录模式下为每个 block 写独立日志，并清理旧 `block_*.log`。
- `dsl_cost_run(...)` 无论是否设置 `dump_dir` 都只输出 stdout runtime trance 诊断，不生成 block 文件或旧单文件 trace。

验证：
- `python3 -m py_compile kernel_gen/execute_engine/compiler.py kernel_gen/tools/dsl_run.py test/execute_engine/test_compile.py test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/include/api/test_trance.py test/include/npu_demo/test_runtime_launch.py`
  - 结果：通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_trance.py -ra`
  - 结果：`6 passed in 2.65s`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile.py -k trance -ra`
  - 结果：`2 passed, 26 deselected in 0.87s`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_arch.py test/include/npu_demo/test_runtime_launch.py -k "trance or launch" -ra`
  - 结果：`3 passed, 4 deselected in 1.76s`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k trance -ra`
  - 结果：`2 passed, 38 deselected, 2 warnings in 6.07s`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_cost_run.py -k trance -ra`
  - 结果：`2 passed, 9 deselected, 1 warning in 5.58s`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_config.py -ra`
  - 结果：`6 passed in 0.02s`
- `git diff --check`
  - 结果：通过。
- `git diff --name-only -- expectation .skills agents/standard`
  - 结果：空。
- `git diff --cached --name-only -- expectation .skills agents/standard`
  - 结果：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`
  - 结果：空。
- 静态边界扫描：
  - `git diff -U0 -- kernel_gen include test | rg -n "^\\+.*(kernelcode::trance::detail|hasattr\\(|getattr\\([^\\n]*emit_|callable\\(getattr|def .*\\):\\s*$)"`
  - 结果：未发现本轮新增违规。

Diff 反推自测：
- 反推范围：`compiler.py`、`dsl_run.py`、`include/api/Trance.h`、`include/npu_demo/Trance.h`、`include/npu_demo/Arch.h`、相关 spec 与测试。
- 反推命令：
  - `pytest -q test/include/api/test_trance.py -ra`
  - `pytest -q test/include/api/test_arch.py test/include/npu_demo/test_runtime_launch.py -k "trance or launch" -ra`
  - `pytest -q test/execute_engine/test_compile.py -k trance -ra`
  - `pytest -q test/tools/test_dsl_run.py -k trance -ra`
  - `pytest -q test/tools/test_dsl_cost_run.py -k trance -ra`
- 断言锁定：
  - `launch` 在 block 目录模式下生成 `block_0000.log` / `block_0001.log`，header 中 block id 正确，stdout 无 launch 杂音。
  - 重跑会覆盖旧 block 文件，block 数减少时旧额外 block 文件被清理。
  - `dsl_run(...)` 不再生成旧 `<entry>_trace.txt` / `<kernel_name>_trace.txt`。
  - `dsl_cost_run(...)` 只 stdout，不创建 `trance/` 或 `block_*.log`。

自检：
- 已检查新增公开 API 仅限用户/架构已确认的 `KG_TRANCE_DIR_PATH`、`prepare_block_trace_dir(...)` 与 `ScopedBlockTranceSink(...)`，未新增其它公开入口。
- 已检查未跨文件调用非公开 helper；`Arch.h` 仅调用 trace 公开入口。
- 已检查 `expectation/.skills/agents/standard` 候选 diff 为空。
- 已检查修改范围覆盖 spec、include、compiler、tests 与任务记录，未修改 expectation。
- 已检查 block 目录模式与 stdout 模式分流明确，`dsl_cost_run` 不再落盘。

结论：已完成 execute，待 review。

## 2026-05-20 review 记录

时间：2026-05-20 03:31 +0800
经办人：提莫炖蘑菇
任务：T-20260520-e0fbce33 / runtime_trance_block_logs review
任务目标：审查 runtime_trance_block_logs 的 spec/include/compiler/test、Diff 反推自测、主仓只读 expectation/.skills/agents/standard 空 diff，以及 block 级日志与 stdout-only 口径。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260520-runtime-trance-block-logs`
- `git fetch origin`：通过。
- `HEAD=8a73d06b37ab9417d5b41b397f70b752395c8787`
- `origin/main=8a73d06b37ab9417d5b41b397f70b752395c8787`
- `merge-base=8a73d06b37ab9417d5b41b397f70b752395c8787`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`
- 判断：待审 worktree 已处在最新主线基线上；当前候选 diff 为任务改动 + 本任务记录，未发现主线同步覆盖风险。

审查范围：
- 计划书：`ARCHITECTURE/plan/runtime_trance_block_logs_green_plan.md`
- 任务记录：`agents/codex-multi-agents/log/task_records/2026/20/20260520-runtime-trance-block-logs.md`
- 被审 diff：
  - `kernel_gen/execute_engine/compiler.py`
  - `kernel_gen/tools/dsl_run.py`
  - `include/api/Trance.h`
  - `include/npu_demo/Trance.h`
  - `include/npu_demo/Arch.h`
  - `spec/core/config.md`
  - `spec/execute_engine/execute_engine_target.md`
  - `spec/include/api/Arch.md`
  - `spec/include/api/Trance.md`
  - `spec/include/npu_demo/npu_demo.md`
  - `spec/tools/dsl_run.md`
  - `test/execute_engine/test_compile.py`
  - `test/include/api/test_trance.py`
  - `test/include/npu_demo/test_runtime_launch.py`
  - `test/tools/test_dsl_cost_run.py`
  - `test/tools/test_dsl_run.py`
  - 本任务记录文件

发现：
- 最小需改项：`spec/include/api/Trance.md:423` 与 `spec/include/api/Trance.md:424` 同时使用 `TC-INCLUDE-API-TRANCE-004`。问题 -> 新增 block trace 用例插入后未重排后续用例 ID；影响 -> spec 测试矩阵出现重复编号，后续按用例编号追踪公开合同与测试覆盖时会歧义，且与当前“spec/test 定义一致”要求不符；最小返工动作 -> 将 block trace 用例或后续 include/api 公开头组合/no-op/并发用例重新编号，保持整张表用例 ID 唯一，并同步任何引用该 ID 的文档或注释；验收方式 -> `python3` 或 `rg` 检查 `spec/include/api/Trance.md` 中 `TC-INCLUDE-API-TRANCE-*` 无重复，复跑本轮 spec 关联 pytest 与 `git diff --check`。

Diff 反推审查：
- `compiler.py`：核对 `_trance_compiler_flags(...)` 已由旧 `KG_TRANCE_FILE_PATH=<trace>` 改为 `KG_TRANCE_DIR_PATH=<dump>/<kernel>/trance` + 空 `KG_TRANCE_FILE_PATH`；entry shim 在目录模式下不打印顶层 stdout/旧单文件日志。
- `dsl_run.py`：核对 `dsl_run(...)` 在 source 选择后把 dump_dir 切回 root 以生成 `<dump>/<kernel>/trance`，`dsl_cost_run(...)` 编译 cost wrapper 前清空 dump_dir，符合 stdout-only 口径。
- `include/api/Trance.h` / `include/npu_demo/Trance.h` / `include/npu_demo/Arch.h`：核对新增 `prepare_block_trace_dir(...)` 与 `ScopedBlockTranceSink(...)` 公开入口，文件创建/清理/命名集中在 trace 模块；`Arch.h` 只调用公开入口，未拼接路径、遍历目录或调用 `kernelcode::trance::detail::*`。
- `test`：核对公开测试覆盖 include block 文件、execute_engine 编译宏、dsl_run block trace、dsl_cost_run stdout-only；测试未直接调用 trace detail helper。
- `spec`：发现 `spec/include/api/Trance.md` 用例 ID 重复，需返工后再审。

验证：
- `python3 -m py_compile kernel_gen/execute_engine/compiler.py kernel_gen/tools/dsl_run.py test/execute_engine/test_compile.py test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/include/api/test_trance.py test/include/npu_demo/test_runtime_launch.py` -> 通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_trance.py -ra` -> `6 passed in 2.45s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile.py -k trance -ra` -> `2 passed, 26 deselected in 0.82s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_arch.py test/include/npu_demo/test_runtime_launch.py -k "trance or launch" -ra` -> `3 passed, 4 deselected in 1.53s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k trance -ra` -> `2 passed, 38 deselected, 2 warnings in 5.71s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_cost_run.py -k trance -ra` -> `2 passed, 9 deselected, 1 warning in 5.01s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_config.py -ra` -> `6 passed in 0.03s`。
- `git diff --check` -> 通过。
- `git diff --name-only -- expectation .skills agents/standard` -> 空。
- `git diff --cached --name-only -- expectation .skills agents/standard` -> 空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` -> 空。
- 静态扫描：`git diff -U0 -- kernel_gen include test | rg -n "^\\+.*(kernelcode::trance::detail|hasattr\\(|getattr\\([^\\n]*emit_|callable\\(getattr|def .*\\):\\s*$|__all__|object\\b)" || true` -> 空。
- 重复 ID 核验：本地脚本扫描 `spec/include/api/Trance.md` -> `TC-INCLUDE-API-TRANCE-004 [423, 424]`。

合同验收：
- 本计划正文未列当前必过 `expectation`；本轮仅核对主仓只读 `expectation/` 候选 diff 为空。

执行记录核对：
- execute 已记录执行前阅读、最小功能闭环、Diff 反推自测、自检、敏感目录门禁和静态扫描。
- execute 验证命令与实际 diff 基本匹配；但 spec 用例矩阵重复编号属于 review 反推发现的新收口项。

自检：
- 已按实际 diff 阅读实现、spec、测试和任务记录。
- 已先 `fetch` 并确认最新主线基线一致。
- 已核对公开 API 扩展来源、include 调用边界、测试是否直连非公开 helper、敏感目录空 diff。
- 已复跑 diff 反推 pytest、py_compile 与 `git diff --check`。
- 因仍存在可执行 spec 矩阵返工项，不能给出通过结论。

结论：需修改。请退回 execute，最小收口 `spec/include/api/Trance.md` 用例 ID 唯一性后，复跑相关 pytest、重复 ID 扫描、`git diff --check` 与敏感目录门禁，再回 review。

## 2026-05-20 execute 返工记录

时间：2026-05-20 04:31 +0800
经办人：小李飞刀
任务：T-20260520-e0fbce33 / runtime_trance_block_logs execute 返工
任务目标：修复 `spec/include/api/Trance.md` 中 `TC-INCLUDE-API-TRANCE-004` 用例 ID 重复，并复跑重复 ID 扫描、相关 pytest、`git diff --check`、敏感目录空 diff。

执行前阅读记录：
- 已重读根目录 `AGENTS.md`、`agents/standard/协作执行通用规则.md`、`agents/standard/任务记录约定.md`、`agents/standard/spec文件规范.md`、`agents/standard/测试文件约定.md`。
- 已复查计划书 `ARCHITECTURE/plan/runtime_trance_block_logs_green_plan.md`，确认本轮阻断点仅为 `spec/include/api/Trance.md` 测试矩阵编号重复。
- 已复查前序 review 记录，确认需要保持 `expectation/.skills/agents/standard` 空 diff，并在最新主线现场上继续收口。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260520-runtime-trance-block-logs`
- `git fetch origin`：已执行。
- 基线对齐前：`HEAD=8a73d06b37ab9417d5b41b397f70b752395c8787`，`origin/main=000dbcf018074c8e3abb4ad701c02be21e2b576b`，`merge-base=8a73d06b37ab9417d5b41b397f70b752395c8787`，`git rev-list --left-right --count HEAD...origin/main=0 1`。
- 已 fast-forward 对齐到最新主线：`HEAD=000dbcf018074c8e3abb4ad701c02be21e2b576b`，`origin/main=000dbcf018074c8e3abb4ad701c02be21e2b576b`，`git rev-list --left-right --count HEAD...origin/main=0 0`。
- 判断：本轮返工在最新主线现场完成，无覆盖风险；候选 diff 仅含任务改动与任务记录。

改动：
- `spec/include/api/Trance.md`
  - 将重复编号的测试矩阵条目重新编号，保持 `TC-INCLUDE-API-TRANCE-*` 唯一。
  - 受影响条目同步顺延为 `TC-INCLUDE-API-TRANCE-005/006/007`，并保持对应建议测试名称一致。
- 未修改 `expectation/`、`.skills/`、`agents/standard/**`。

验证：
- `python3 -m py_compile kernel_gen/execute_engine/compiler.py kernel_gen/tools/dsl_run.py test/execute_engine/test_compile.py test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/include/api/test_trance.py test/include/npu_demo/test_runtime_launch.py`
  - 结果：通过。
- `python3 - <<'PY' ...` 扫描 `spec/include/api/Trance.md` 中 `TC-INCLUDE-API-TRANCE-*`
  - 结果：`unique ids: 7`，无重复。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_trance.py test/include/api/test_public_namespace.py -ra`
  - 结果：`8 passed in 2.58s`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile.py -k trance -ra`
  - 结果：`2 passed, 26 deselected in 0.68s`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_arch.py test/include/npu_demo/test_runtime_launch.py -k "trance or launch" -ra`
  - 结果：`3 passed, 4 deselected in 1.50s`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k trance -ra`
  - 结果：`2 passed, 38 deselected, 2 warnings in 6.09s`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_cost_run.py -k trance -ra`
  - 结果：`2 passed, 9 deselected, 1 warning in 5.07s`
- `git diff --check`
  - 结果：通过。
- `git diff --name-only -- expectation .skills agents/standard`
  - 结果：空。
- `git diff --cached --name-only -- expectation .skills agents/standard`
  - 结果：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`
  - 结果：空。

Diff 反推自测：
- 反推范围：`spec/include/api/Trance.md` 的测试矩阵编号、相关 include/runtime trace 公开验证入口。
- 反推命令：`python3` 重复 ID 扫描 + `pytest -q test/include/api/test_trance.py test/include/api/test_public_namespace.py -ra`
- 断言锁定：
  - `TC-INCLUDE-API-TRANCE-*` 全局唯一，无重复编号。
  - `include/api` 公开头 compile-only 与 runtime no-op 行为仍可验证。
  - `TRANCE` 开启时的 include/runtime trace 相关公开测试仍通过，未因编号重排破坏测试入口。

自检：
- 已确认本轮仅调整 spec 测试矩阵编号，没有新增或修改公开 API。
- 已确认未修改 `expectation/`、`.skills/`、`agents/standard/**`。
- 已确认敏感目录三条门禁结果为空。
- 已确认相关 pytest、py_compile 与 `git diff --check` 均通过。
- 已确认最新主线已 fast-forward 到本 worktree，复验基线与执行现场一致。

结论：返工已闭合，准备按流程 `-next` 到 review。

## 2026-05-20 review 复审记录

时间：2026-05-20 03:58 CST
经办人：提莫炖蘑菇
任务：T-20260520-e0fbce33 / runtime_trance_block_logs review 复审
任务目标：复审 `spec/include/api/Trance.md` 测试矩阵用例 ID 唯一性、相关 pytest、重复 ID 扫描、`git diff --check`、敏感目录空 diff 与任务记录

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260520-runtime-trance-block-logs`
- `git fetch origin`：已执行。
- `HEAD=000dbcf018074c8e3abb4ad701c02be21e2b576b`
- `origin/main=000dbcf018074c8e3abb4ad701c02be21e2b576b`
- `merge-base=000dbcf018074c8e3abb4ad701c02be21e2b576b`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`
- 判断：待审 worktree 已与最新主线对齐，无覆盖风险。

审查范围：
- 计划书：`ARCHITECTURE/plan/runtime_trance_block_logs_green_plan.md`
- 任务记录：`agents/codex-multi-agents/log/task_records/2026/20/20260520-runtime-trance-block-logs.md`
- 被审 diff：
  - `kernel_gen/execute_engine/compiler.py`
  - `kernel_gen/tools/dsl_run.py`
  - `include/api/Trance.h`
  - `include/npu_demo/Trance.h`
  - `include/npu_demo/Arch.h`
  - `spec/core/config.md`
  - `spec/execute_engine/execute_engine_target.md`
  - `spec/include/api/Arch.md`
  - `spec/include/api/Trance.md`
  - `spec/include/npu_demo/npu_demo.md`
  - `spec/tools/dsl_run.md`
  - `test/execute_engine/test_compile.py`
  - `test/include/api/test_trance.py`
  - `test/include/npu_demo/test_runtime_launch.py`
  - `test/tools/test_dsl_cost_run.py`
  - `test/tools/test_dsl_run.py`
  - 任务记录文件

发现：
- 无最小需改项。前序 review 唯一阻断项 `spec/include/api/Trance.md` 中 `TC-INCLUDE-API-TRANCE-004` 重复编号已在返工中修正，当前 `TC-INCLUDE-API-TRANCE-*` 扫描结果唯一。

Diff 反推审查：
- `kernel_gen/execute_engine/compiler.py`：确认 runtime trance 编译宏切换为 `KG_TRANCE_DIR_PATH` + 空 `KG_TRANCE_FILE_PATH`，与 block trace 目录合同一致。
- `kernel_gen/tools/dsl_run.py`：确认 `dsl_run(...)` / `dsl_cost_run(...)` 的落盘行为与 stdout-only 口径分流明确。
- `include/api/Trance.h` / `include/npu_demo/Trance.h` / `include/npu_demo/Arch.h`：确认新增 block trace 公开入口与 `Arch.h` 调用边界仍只落在公开 trace 接口，无跨文件非公开 helper。
- `spec/include/api/Trance.md`：确认重复用例 ID 已修正为唯一序列，测试矩阵可机械审查。
- `test`：确认相关 pytest 仍覆盖 block trace 目录、stdout-only 与并发边界。

验证：
- `python3 -m py_compile kernel_gen/execute_engine/compiler.py kernel_gen/tools/dsl_run.py test/execute_engine/test_compile.py test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/include/api/test_trance.py test/include/npu_demo/test_runtime_launch.py` -> `exit=0`
- `python3 - <<'PY' ...` 扫描 `spec/include/api/Trance.md` 中 `TC-INCLUDE-API-TRANCE-*` -> `unique ids: 7`, 无重复
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_trance.py test/include/api/test_public_namespace.py -ra` -> `8 passed in 2.58s`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile.py -k trance -ra` -> `2 passed, 26 deselected in 0.68s`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_arch.py test/include/npu_demo/test_runtime_launch.py -k "trance or launch" -ra` -> `3 passed, 4 deselected in 1.50s`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k trance -ra` -> `2 passed, 38 deselected, 2 warnings in 6.09s`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_cost_run.py -k trance -ra` -> `2 passed, 9 deselected, 1 warning in 5.07s`
- `git diff --check` -> `exit=0`
- `git diff --name-only -- expectation .skills agents/standard` -> 空
- `git diff --cached --name-only -- expectation .skills agents/standard` -> 空
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` -> 空

自检：
- 已逐项读取实际 diff、计划书、执行记录与最新主线基线，未发现覆盖风险。
- 已确认候选 diff 未引入 `expectation/`、`.skills/`、`agents/standard/**` 变更。
- 已确认本轮无新增公开 API、无上下文能力探测、无跨文件非公开 helper 调用。

## 2026-05-20 架构终验记录

时间：2026-05-20 04:44 CST
经办人：大闸蟹
任务：T-20260520-e0fbce33 / runtime_trance_block_logs
任务目标：终验 runtime `TRANCE` block 级落盘合同、`dsl_cost_run` stdout-only 口径、公开宏 `KG_TRANCE_DIR_PATH` / `KG_TRANCE_FILE_PATH` 优先级、`ScopedBlockTranceSink` / `prepare_block_trace_dir` 公开入口、`npu_demo::launch` block 文件写入与敏感目录门禁。

验证基线：
- `HEAD=origin/main=merge-base=000dbcf018074c8e3abb4ad701c02be21e2b576b`
- `ahead/behind=0/0`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260520-runtime-trance-block-logs`

合同验收摘要：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_trance.py test/include/api/test_public_namespace.py -ra` -> `8 passed`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile.py -k trance -ra` -> `2 passed, 26 deselected`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_arch.py test/include/npu_demo/test_runtime_launch.py -k "trance or launch" -ra` -> `3 passed, 4 deselected`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k trance -ra` -> `2 passed, 38 deselected`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_cost_run.py -k trance -ra` -> `2 passed, 9 deselected`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_config.py -ra` -> `6 passed`
- `python3 -m py_compile kernel_gen/execute_engine/compiler.py kernel_gen/tools/dsl_run.py test/execute_engine/test_compile.py test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/include/api/test_trance.py test/include/npu_demo/test_runtime_launch.py` -> 通过
- `git diff --check` -> 通过
- `git diff --name-only -- expectation .skills agents/standard` -> 空
- `git diff --cached --name-only -- expectation .skills agents/standard` -> 空
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` -> 空
- `spec/include/api/Trance.md` 的 `TC-INCLUDE-API-TRANCE-*` 用例 ID 已复核为唯一，无重复

终验结论：通过。
最小阻断项：无。
补充说明：本计划已按 C1-C4 收口，`dsl_cost_run(...)` 固定 stdout-only，`dsl_run(...)` 按 block 文件落盘，旧单文件 trace 不再作为当前合同；实现、spec、include、compiler、pytest 与任务记录已同批闭环。
- 已确认复审后仅剩历史阻断项已收口，无剩余可执行返工项。

结论：通过

## 2026-05-20 第二架构终验记录

时间：2026-05-20 04:40 CST
经办人：守护最好的爱莉希雅
任务：T-20260520-e0fbce33 / runtime_trance_block_logs
任务目标：终验 runtime `TRANCE` block 级落盘合同、`dsl_cost_run` stdout-only 口径、公开宏 `KG_TRANCE_DIR_PATH` / `KG_TRANCE_FILE_PATH` 优先级、`ScopedBlockTranceSink` / `prepare_block_trace_dir` 公开入口、`npu_demo::launch` block 文件写入与敏感目录门禁。

验证基线：
- `HEAD=origin/main=merge-base=000dbcf018074c8e3abb4ad701c02be21e2b576b`
- `ahead/behind=0/0`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260520-runtime-trance-block-logs`

合同验收摘要：
- `python3 -m py_compile kernel_gen/execute_engine/compiler.py kernel_gen/tools/dsl_run.py test/execute_engine/test_compile.py test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/include/api/test_trance.py test/include/npu_demo/test_runtime_launch.py` -> 通过
- `python3 - <<'PY' ...` 扫描 `spec/include/api/Trance.md` 的 `TC-INCLUDE-API-TRANCE-*` -> `unique ids: 7`，无重复
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_trance.py test/include/api/test_public_namespace.py -ra` -> `8 passed`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile.py -k trance -ra` -> `2 passed, 26 deselected`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_arch.py test/include/npu_demo/test_runtime_launch.py -k "trance or launch" -ra` -> `3 passed, 4 deselected`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k trance -ra` -> `2 passed, 38 deselected`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_cost_run.py -k trance -ra` -> `2 passed, 9 deselected`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_config.py -ra` -> `6 passed`
- `git diff --check` -> 通过
- `git diff --name-only -- expectation .skills agents/standard` -> 空
- `git diff --cached --name-only -- expectation .skills agents/standard` -> 空
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` -> 空

自检：
- 已确认候选 diff 仅覆盖计划目标内的 runtime trace / spec / test / include / compiler / tools 文件。
- 已确认 `expectation/`、`.skills/`、`agents/standard/**` 仍为零改动。
- 已确认无公开 API 额外扩展、无跨文件非公开 helper 依赖、无静态边界扫描命中。

终验结论：通过。
最小阻断项：无。
补充说明：本计划按合同切换到 block 级 trace 落盘后，`dsl_run(...)` 与 `dsl_cost_run(...)` 的行为边界已分流清楚；当前候选 diff、pytest、重复 ID 扫描与敏感目录门禁均已闭环，可进入双架构收口后流转 merge。

---

时间：2026-05-20 04:45 CST
经办人：李白
阶段：merge 收口

合并前同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260520-runtime-trance-block-logs`
- 任务分支：`task/runtime-trance-block-logs`
- 已执行 `git fetch --prune origin`。
- `HEAD=000dbcf018074c8e3abb4ad701c02be21e2b576b`
- `origin/main=000dbcf018074c8e3abb4ad701c02be21e2b576b`
- `ahead/behind=0/0`
- 主仓 `/home/lfr/kernelcode_generate` 当前为 clean，本次合并不存在覆盖主仓本地改动风险。

本次候选同批范围：
- `include/api/Trance.h`
- `include/npu_demo/Arch.h`
- `include/npu_demo/Trance.h`
- `kernel_gen/execute_engine/compiler.py`
- `kernel_gen/tools/dsl_run.py`
- `spec/core/config.md`
- `spec/execute_engine/execute_engine_target.md`
- `spec/include/api/Arch.md`
- `spec/include/api/Trance.md`
- `spec/include/npu_demo/npu_demo.md`
- `spec/tools/dsl_run.md`
- `test/execute_engine/test_compile.py`
- `test/include/api/test_trance.py`
- `test/include/npu_demo/test_runtime_launch.py`
- `test/tools/test_dsl_cost_run.py`
- `test/tools/test_dsl_run.py`
- `agents/codex-multi-agents/log/task_records/2026/20/20260520-runtime-trance-block-logs.md`

merge 前真实复核：
- 候选 diff 与 review、返工复审、双架构终验记录一致；任务记录当前为未跟踪文件，已确认必须与代码 / spec / test 同批纳入提交，不得先合代码后补记录。
- 本计划无 `expectation/` 必过资产；merge 记录不把 expectation 写作通过依据。
- `expectation/`、`.skills/`、`agents/standard/` 无普通 diff、staged diff、未跟踪或 ignored 输出。

merge 前复跑命令：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/execute_engine/compiler.py kernel_gen/tools/dsl_run.py test/execute_engine/test_compile.py test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/include/api/test_trance.py test/include/npu_demo/test_runtime_launch.py`：exit `0`。
- `python3 - <<'PY' ...` 扫描 `spec/include/api/Trance.md` 中 `TC-INCLUDE-API-TRANCE-*`：`unique ids: 7`，无重复。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_trance.py test/include/api/test_public_namespace.py -ra`：`8 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile.py -k trance -ra`：`2 passed, 26 deselected`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_arch.py test/include/npu_demo/test_runtime_launch.py -k "trance or launch" -ra`：`3 passed, 4 deselected`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k trance -ra`：`2 passed, 38 deselected, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_cost_run.py -k trance -ra`：`2 passed, 9 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_config.py -ra`：`6 passed`。
- `git diff --check`：exit `0`。
- `git diff --name-only -- expectation .skills agents/standard`：空。
- `git diff --cached --name-only -- expectation .skills agents/standard`：空。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：空。

Diff 反推自测 / 审查继承：
- include/API 与 npu_demo runtime trace 相关 pytest 锁定 block trace 目录、公开头 compile-only、public namespace 与 runtime no-op 行为。
- execute_engine 与 tools 相关 pytest 锁定 `KG_TRANCE_DIR_PATH` / `KG_TRANCE_FILE_PATH` 优先级、`dsl_run` block 文件落盘、`dsl_cost_run` stdout-only 边界。
- 重复 ID 扫描锁定 `spec/include/api/Trance.md` 的 `TC-INCLUDE-API-TRANCE-*` 全局唯一。
- 本轮 merge 前重新复跑上述直接相关 gate，未发现 latest main 下的失效。

merge 结论：
- 可合并。
- 记录文件已与业务 / spec / test 候选同批纳入提交范围。
- 最小阻断项：无。
